# Fichier: backend/cron_job.py

import asyncio
import hashlib
import ipaddress
import ssl
import os
import smtplib
import socket
import re
from email.message import EmailMessage
from datetime import datetime
from typing import List, Dict
try:
    from .database import SessionLocal, initialize_database, list_domains, save_statuses
except ImportError:
    from database import SessionLocal, initialize_database, list_domains, save_statuses

# Seuil en jours pour considérer qu'un certificat "Expire bientôt"
ALERT_THRESHOLD_DAYS = 30
MAX_CONCURRENCY = int(os.getenv("SSL_CHECK_MAX_CONCURRENCY", "20"))
MAX_RETRIES = int(os.getenv("SSL_CHECK_MAX_RETRIES", "2"))
DNS_TIMEOUT = float(os.getenv("SSL_CHECK_DNS_TIMEOUT", "5"))
CONNECT_TIMEOUT = float(os.getenv("SSL_CHECK_CONNECT_TIMEOUT", "5"))
TLS_TIMEOUT = float(os.getenv("SSL_CHECK_TLS_TIMEOUT", "5"))
RETRY_BACKOFF = float(os.getenv("SSL_CHECK_RETRY_BACKOFF", "0.25"))
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
            loop.getaddrinfo(hostname, 443, type=socket.SOCK_STREAM), DNS_TIMEOUT
        )
    except asyncio.TimeoutError as error:
        raise SSLCheckError("timeout_dns", "La résolution DNS a expiré.", True) from error
    except socket.gaierror as error:
        raise SSLCheckError("erreur_dns", str(error)) from error
    except OSError as error:
        raise SSLCheckError("erreur_dns", str(error), True) from error

    if not addresses:
        raise SSLCheckError("erreur_dns", "Aucune adresse DNS retournée.")

    address = addresses[0][4][0]
    writer = None
    try:
        try:
            _, writer = await asyncio.wait_for(
                asyncio.open_connection(address, 443), CONNECT_TIMEOUT
            )
        except asyncio.TimeoutError as error:
            raise SSLCheckError("timeout_connexion", "La connexion TCP a expiré.", True) from error
        except OSError as error:
            raise SSLCheckError("erreur_connexion", str(error), True) from error

        context = ssl.create_default_context()
        try:
            await asyncio.wait_for(
                writer.start_tls(context, server_hostname=hostname), TLS_TIMEOUT
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


async def get_ssl_expiry_info(hostname: str) -> Dict:
    """Vérifie un certificat avec limites de temps et retries contrôlés."""
    for attempt in range(MAX_RETRIES + 1):
        try:
            return await _check_once(hostname)
        except SSLCheckError as error:
            if not error.retryable or attempt == MAX_RETRIES:
                return _error_result(hostname, error)
            await asyncio.sleep(RETRY_BACKOFF * (2**attempt))

# --- Logique d'envoi d'email ---
def send_summary_report(critical_certs: list):
    """Envoie un rapport récapitulatif par email avec les certificats critiques."""
    # Lit la configuration depuis les variables d'environnement chargées par Docker Compose
    sender_email = os.getenv("SMTP_SENDER_EMAIL")
    password = os.getenv("SMTP_PASSWORD")
    recipients_str = os.getenv("ALERT_RECIPIENTS")
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = int(os.getenv("SMTP_PORT", 587))

    if not all([sender_email, password, recipients_str, smtp_server]):
        print("-> AVERTISSEMENT: Variables d'environnement pour l'email non configurées. Envoi annulé.")
        return

    recipients = [email.strip() for email in recipients_str.split(',')]
    
    msg = EmailMessage()
    msg['Subject'] = f"🚨 Rapport SSL-Cert-Monitor : {len(critical_certs)} certificat(s) requièrent votre attention"
    msg['From'] = sender_email
    msg['To'] = ", ".join(recipients)

    body_lines = [
        "Bonjour,",
        "\nLe rapport de surveillance quotidien a identifié les certificats suivants comme étant critiques :",
        "\n"
    ]
    for cert in critical_certs:
        body_lines.append("----------------------------------------")
        body_lines.append(f"Domaine : {cert['domain']}")
        body_lines.append(f"Statut  : {cert['status']}")
        if cert.get('days_left') is not None:
             body_lines.append(f"Jours restants : {cert['days_left']}")
        if cert.get('error_message'):
            body_lines.append(f"Erreur : {cert['error_message']}")
        body_lines.append("")

    msg.set_content("\n".join(body_lines))

    try:
        print(f"-> Envoi du rapport à {', '.join(recipients)}...")
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(sender_email, password)
            server.send_message(msg)
        print("-> ✅ Rapport email envoyé avec succès.")
    except Exception as e:
        print(f"-> ❌ Échec de l'envoi de l'email : {e}")

# --- Logique de vérification SSL Asynchrone ---
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
    critical_certs = [cert for cert in results if cert['status'] in ['Expire bientôt', 'Expiré', 'Erreur']]
    if critical_certs:
        send_summary_report(critical_certs)
    else:
        print("-> Tous les certificats sont OK. Aucun email envoyé.")

if __name__ == "__main__":
    asyncio.run(main())
