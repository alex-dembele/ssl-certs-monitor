# Fichier: backend/cron_job.py

import asyncio
import hashlib
import ipaddress
import ssl
import os
import smtplib
import socket
import re
from datetime import datetime
from typing import List, Dict
try:
    from .database import SessionLocal, initialize_database, list_domains, save_statuses
    from .alerts import record_notification, select_alert_events
    from .notifications import deliver_events
    from .settings import NotificationSettings
except ImportError:
    from database import SessionLocal, initialize_database, list_domains, save_statuses
    from alerts import record_notification, select_alert_events
    from notifications import deliver_events
    from settings import NotificationSettings

# Seuil en jours pour considérer qu'un certificat "Expire bientôt"
ALERT_THRESHOLD_DAYS = 30
MAX_CONCURRENCY = int(os.getenv("SSL_CHECK_MAX_CONCURRENCY", "20"))
MAX_RETRIES = int(os.getenv("SSL_CHECK_MAX_RETRIES", "2"))
DNS_TIMEOUT = float(os.getenv("SSL_CHECK_DNS_TIMEOUT", "5"))
CONNECT_TIMEOUT = float(os.getenv("SSL_CHECK_CONNECT_TIMEOUT", "5"))
TLS_TIMEOUT = float(os.getenv("SSL_CHECK_TLS_TIMEOUT", "5"))
RETRY_BACKOFF = float(os.getenv("SSL_CHECK_RETRY_BACKOFF", "0.25"))
TLS_PORT = 443
HOSTNAME_PATTERN = re.compile(r"^(?=.{1,253}$)(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,63}$")


class SSLCheckError(Exception):
    def __init__(self, error_type: str, message: str, retryable: bool = False):
        super().__init__(message)
        self.error_type = error_type
        self.retryable = retryable


def _error_result(hostname: str, error: SSLCheckError) -> Dict:
    return {
        "domain": hostname,
        "status": "Erreur",
        "error_type": error.error_type,
        "error_message": str(error),
        "checked_at": datetime.now().astimezone().isoformat(),
    }


def _certificate_value(value) -> str | None:
    if not value:
        return None
    return ", ".join("=".join(str(part) for part in item) for item in value)


def _classify_tls_error(error: BaseException) -> SSLCheckError:
    message = str(error)
    normalized = message.lower()
    if "hostname" in normalized or "doesn't match" in normalized or "match" in normalized:
        return SSLCheckError("hostname_invalide", message)
    if "issuer" in normalized or "local issuer" in normalized or "unable to get" in normalized:
        return SSLCheckError("chaine_incomplete", message)
    return SSLCheckError("certificat_invalide", message)


def _validate_hostname(hostname: str) -> None:
    try:
        ipaddress.ip_address(hostname)
    except ValueError:
        if not HOSTNAME_PATTERN.fullmatch(hostname):
            raise SSLCheckError("hostname_invalide", "Nom d'hôte invalide.")


async def _check_once(hostname: str) -> Dict:
    _validate_hostname(hostname)
    loop = asyncio.get_running_loop()
    try:
        addresses = await asyncio.wait_for(
            loop.getaddrinfo(hostname, TLS_PORT, type=socket.SOCK_STREAM), DNS_TIMEOUT
        )
    except asyncio.TimeoutError as error:
        raise SSLCheckError("timeout_dns", "La résolution DNS a expiré.", True) from error
    except socket.gaierror as error:
        raise SSLCheckError("erreur_dns", str(error)) from error
    except OSError as error:
        raise SSLCheckError("erreur_dns", str(error), True) from error

    if not addresses:
        raise SSLCheckError("erreur_dns", "Aucune adresse DNS retournée.")

    family, _, proto, _, sockaddr = addresses[0]
    writer = None
    sock = socket.socket(family, socket.SOCK_STREAM, proto)
    sock.setblocking(False)
    try:
        try:
            await asyncio.wait_for(loop.sock_connect(sock, sockaddr), CONNECT_TIMEOUT)
        except asyncio.TimeoutError as error:
            raise SSLCheckError("timeout_connexion", "La connexion TCP a expiré.", True) from error
        except OSError as error:
            raise SSLCheckError("erreur_connexion", str(error), True) from error

        # TLS sur la socket déjà connectée : garde des délais distincts TCP/TLS
        # sans StreamWriter.start_tls, absent avant Python 3.11 (#97).
        context = ssl.create_default_context()
        try:
            _, writer = await asyncio.wait_for(
                asyncio.open_connection(sock=sock, ssl=context, server_hostname=hostname), TLS_TIMEOUT
            )
        except asyncio.TimeoutError as error:
            raise SSLCheckError("timeout_tls", "La négociation TLS a expiré.", True) from error
        except (ssl.SSLCertVerificationError, ssl.CertificateError) as error:
            raise _classify_tls_error(error) from error
        except ssl.SSLError as error:
            raise _classify_tls_error(error) from error
        except OSError as error:
            raise SSLCheckError("erreur_tls", str(error), True) from error

        certificate = writer.get_extra_info("peercert") or {}
        ssl_object = writer.get_extra_info("ssl_object")
        certificate_bytes = ssl_object.getpeercert(binary_form=True) if ssl_object else None
        not_after = certificate.get("notAfter")
        not_before = certificate.get("notBefore")
        if not_after is None or not_before is None:
            raise SSLCheckError("certificat_invalide", "Le certificat est incomplet.")
        expiry_date = datetime.strptime(not_after, "%b %d %H:%M:%S %Y %Z")
        valid_from = datetime.strptime(not_before, "%b %d %H:%M:%S %Y %Z")
        days_left = (expiry_date - datetime.now()).days
        status = "Expiré" if days_left < 0 else "Expire bientôt" if days_left < ALERT_THRESHOLD_DAYS else "OK"
        return {
            "domain": hostname,
            "status": status,
            "days_left": days_left,
            "expiry_date": expiry_date.isoformat(),
            "valid_from": valid_from.isoformat(),
            "valid_until": expiry_date.isoformat(),
            "issuer": _certificate_value(certificate.get("issuer")),
            "subject": _certificate_value(certificate.get("subject")),
            "serial_number": certificate.get("serialNumber"),
            "fingerprint": hashlib.sha256(certificate_bytes).hexdigest() if certificate_bytes else None,
            "san": [value for kind, value in certificate.get("subjectAltName", ()) if kind == "DNS"],
            "checked_at": datetime.now().astimezone().isoformat(),
        }
    finally:
        if writer is not None:
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass
        else:
            sock.close()


async def get_ssl_expiry_info(hostname: str) -> Dict:
    """Vérifie un certificat avec limites de temps et retries contrôlés."""
    for attempt in range(MAX_RETRIES + 1):
        try:
            return await _check_once(hostname)
        except SSLCheckError as error:
            if not error.retryable or attempt == MAX_RETRIES:
                return _error_result(hostname, error)
            await asyncio.sleep(RETRY_BACKOFF * (2**attempt))
        except Exception as error:
            # Une erreur imprévue ne doit pas interrompre le lot de vérifications.
            return _error_result(hostname, SSLCheckError("erreur_inattendue", f"{type(error).__name__}: {error}"))

# --- Fonction Principale du Script ---
async def main():
    """Orchestre la vérification de masse et la génération de rapports."""
    print(f"--- Lancement de la tâche de fond de vérification SSL ({datetime.now()}) ---")
    initialize_database()
    with SessionLocal() as session:
        domains = list_domains(session)
    if not domains:
        print("Aucun domaine à vérifier. Tâche terminée.")
        return

    semaphore = asyncio.Semaphore(MAX_CONCURRENCY)

    async def check_with_limit(domain: str) -> Dict:
        async with semaphore:
            return await get_ssl_expiry_info(domain)

    tasks = [check_with_limit(domain) for domain in domains]
    results = await asyncio.gather(*tasks)
    
    with SessionLocal() as session:
        save_statuses(session, results)
    
    print(f"-> Vérification terminée. {len(results)} domaines traités. Rapport mis à jour en base.")

    # Filtrage des certificats critiques et envoi de l'email
    with SessionLocal() as session:
        events = select_alert_events(session, results)
    if events:
        deliveries = deliver_events(events)
        with SessionLocal() as session:
            for delivery in deliveries:
                record_notification(
                    session, [delivery.event], delivery.success, delivery.error_message,
                    delivery_status=delivery.status, attempts=delivery.attempts,
                    idempotency_key=delivery.idempotency_key,
                )
    else:
        print("-> Aucun nouvel événement d'alerte. Aucun email envoyé.")

if __name__ == "__main__":
    asyncio.run(main())
