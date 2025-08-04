# Fichier: monitor.py
import ssl
import socket
import json
import smtplib
from email.message import EmailMessage
from datetime import datetime

# Seuil en jours pour l'alerte "Expire bientôt"
ALERT_THRESHOLD_DAYS = 30

def get_ssl_expiry_info(hostname: str) -> dict:
    """
    Vérifie le certificat SSL d'un domaine et retourne un dictionnaire détaillé.
    """
    try:
        # Créer un contexte SSL par défaut
        context = ssl.create_default_context()
        
        # Se connecter au serveur sur le port 443 (HTTPS)
        with socket.create_connection((hostname, 443), timeout=10) as sock:
            with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                cert = ssock.getpeercert()
                
                # Extraire la date d'expiration
                expiry_date_str = cert['notAfter']
                expiry_date = datetime.strptime(expiry_date_str, '%b %d %H:%M:%S %Y %Z')
                days_left = (expiry_date - datetime.now()).days
                
                # Définir le statut en fonction des jours restants
                status = "OK"
                if days_left < 0:
                    status = "Expiré"
                elif days_left < ALERT_THRESHOLD_DAYS:
                    status = "Expire bientôt"

                return {
                    "domain": hostname,
                    "status": status,
                    "days_left": days_left,
                    "expiry_date": expiry_date.isoformat() # Utiliser le format ISO 8601
                }

    except Exception as e:
        return {
            "domain": hostname,
            "status": "Erreur",
            "error_message": str(e)
        }

def send_alert_email(config: dict, cert_info: dict):
    """Envoie une alerte par email pour un certificat spécifique."""
    recipients = config['alert_recipients']
    smtp_config = config['smtp']
    
    msg = EmailMessage()
    msg['Subject'] = f"🚨 Alerte SSL : {cert_info['domain']} - Statut {cert_info['status']}"
    msg['From'] = smtp_config['sender_email']
    msg['To'] = ", ".join(recipients)

    if cert_info['status'] == 'Erreur':
        body = (f"Une erreur est survenue lors de la vérification du certificat SSL pour le domaine :\n\n"
                f"Domaine : {cert_info['domain']}\n"
                f"Erreur : {cert_info.get('error_message', 'Inconnue')}")
    else:
        # S'assurer que 'expiry_date' existe avant de l'utiliser
        expiry_date_str = "N/A"
        if 'expiry_date' in cert_info and cert_info['expiry_date']:
             expiry_date_str = datetime.fromisoformat(cert_info['expiry_date']).strftime('%d/%m/%Y')
        
        body = (f"Le certificat SSL pour le domaine suivant nécessite votre attention :\n\n"
                f"Domaine : {cert_info['domain']}\n"
                f"Statut : {cert_info['status']}\n"
                f"Jours Restants : {cert_info.get('days_left', 'N/A')}\n"
                f"Date d'expiration : {expiry_date_str}")

    msg.set_content(body)

    try:
        print(f"   -> Tentative d'envoi d'alerte email à {', '.join(recipients)}...")
        with smtplib.SMTP(smtp_config['server'], smtp_config['port']) as server:
            server.starttls()
            server.login(smtp_config['sender_email'], smtp_config['password'])
            server.send_message(msg)
        print("   -> ✅ Email envoyé avec succès.")
    except Exception as e:
        print(f"   -> ❌ Échec de l'envoi de l'email : {e}")

def main():
    """Fonction principale qui génère le rapport et envoie les alertes."""
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
    for domain in domains:
        print(f"Vérification de {domain}...")
        info = get_ssl_expiry_info(domain)
        results.append(info)

        # Si le statut est critique, on envoie une alerte
        if info['status'] in ["Expire bientôt", "Expiré", "Erreur"]:
            send_alert_email(config, info)
    
    with open('ssl_status.json', 'w') as json_file:
        json.dump(results, json_file, indent=4)

    print("\n✅ Rapport 'ssl_status.json' généré.")
    print("--- Vérification terminée ---")


if __name__ == "__main__":
    main()