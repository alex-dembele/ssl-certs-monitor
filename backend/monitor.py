# Fichier: backend/monitor.py

import ssl
import socket
import json
import smtplib
from email.message import EmailMessage
from datetime import datetime

# Seuil général pour définir le statut "Expire bientôt"
ALERT_THRESHOLD_DAYS = 30 
# ✅ NOUVEAU : Jours spécifiques qui déclencheront l'envoi d'un email
CRITICAL_ALERT_DAYS = [5, 7] 

def get_ssl_expiry_info(hostname: str) -> dict:
    """Vérifie le certificat SSL et retourne un dictionnaire détaillé."""
    try:
        context = ssl.create_default_context()
        with socket.create_connection((hostname, 443), timeout=10) as sock:
            with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                cert = ssock.getpeercert()
                expiry_date_str = cert['notAfter']
                expiry_date = datetime.strptime(expiry_date_str, '%b %d %H:%M:%S %Y %Z')
                days_left = (expiry_date - datetime.now()).days
                
                status = "OK"
                if days_left < 0:
                    status = "Expiré"
                elif days_left < ALERT_THRESHOLD_DAYS:
                    status = "Expire bientôt"

                return {
                    "domain": hostname,
                    "status": status,
                    "days_left": days_left,
                    "expiry_date": expiry_date.isoformat()
                }
    except Exception as e:
        return {"domain": hostname, "status": "Erreur", "error_message": str(e)}

def send_summary_report(config: dict, critical_certs: list):
    """Envoie un rapport récapitulatif par email avec tous les certificats critiques."""
    # ... (cette fonction ne change pas)
    recipients = config['alert_recipients']
    smtp_config = config['smtp']
    
    msg = EmailMessage()
    msg['Subject'] = f"🚨 Rapport de Surveillance SSL : {len(critical_certs)} certificat(s) requièrent votre attention"
    msg['From'] = smtp_config['sender_email']
    msg['To'] = ", ".join(recipients)

    body_lines = ["Bonjour,", "\n", "Le rapport de surveillance a identifié les certificats suivants comme étant critiques :", "\n"]
    for cert in critical_certs:
        body_lines.append("----------------------------------------")
        body_lines.append(f"Domaine : {cert['domain']}")
        body_lines.append(f"Statut  : {cert['status']}")
        if cert['status'] != 'Erreur':
            expiry_date_str = datetime.fromisoformat(cert['expiry_date']).strftime('%d/%m/%Y')
            body_lines.append(f"Jours restants : {cert.get('days_left', 'N/A')}")
            body_lines.append(f"Date d'expiration : {expiry_date_str}")
        else:
            body_lines.append(f"Message d'erreur : {cert.get('error_message', 'Inconnue')}")
        body_lines.append("")

    msg.set_content("\n".join(body_lines))

    try:
        print(f"   -> Tentative d'envoi du rapport récapitulatif à {', '.join(recipients)}...")
        with smtplib.SMTP(smtp_config['server'], smtp_config['port']) as server:
            server.starttls()
            server.login(smtp_config['sender_email'], smtp_config['password'])
            server.send_message(msg)
        print("   -> ✅ Rapport envoyé avec succès.")
    except Exception as e:
        print(f"   -> ❌ Échec de l'envoi du rapport : {e}")


def main():
    """Fonction principale qui génère le rapport et envoie un email récapitulatif."""
    print("--- Lancement de la surveillance des certificats SSL ---")

    try:
        with open('config.json', 'r') as f:
            config = json.load(f)
        with open('domains.txt', 'r') as f:
            domains = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    except FileNotFoundError as e:
        print(f"❌ Erreur critique : Le fichier '{e.filename}' est introuvable.")
        return

    results = []
    critical_certs = []
    for domain in domains:
        print(f"Vérification de {domain}...")
        info = get_ssl_expiry_info(domain)
        results.append(info)

        # ✅ NOUVEAU : Logique de décision pour l'alerte email
        is_critical_for_email = False
        # Toujours alerter pour les erreurs et les certificats expirés
        if info['status'] in ["Expiré", "Erreur"]:
            is_critical_for_email = True
        # Alerter seulement si le nombre de jours restants est dans notre liste critique
        elif info.get('days_left') in CRITICAL_ALERT_DAYS:
            is_critical_for_email = True

        if is_critical_for_email:
            critical_certs.append(info)
    
    # Écrire le rapport JSON complet pour le dashboard
    with open('/app/data/ssl_status.json', 'w') as json_file:
        json.dump(results, json_file, indent=4)
    print("\n✅ Rapport 'ssl_status.json' généré pour le dashboard.")

    # Envoyer le rapport par email seulement si des certificats critiques ont été trouvés
    if critical_certs:
        send_summary_report(config, critical_certs)
    else:
        print("✅ Aucun certificat ne correspond aux critères d'alerte critiques. Aucun email envoyé.")
        
    print("--- Vérification terminée ---")

if __name__ == "__main__":
    main()