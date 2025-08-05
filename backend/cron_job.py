# Fichier: backend/cron_job.py

import asyncio
import ssl
import json
import os
import smtplib
from email.message import EmailMessage
from datetime import datetime
from typing import List, Dict

# Constantes pour les chemins de fichiers et le seuil d'alerte
DOMAINS_FILE = "domains.json"
# Le script écrit dans le volume `status_data`, qui est monté sur /app/public dans le conteneur
STATUS_FILE = "/app/public/ssl_status.json" 
ALERT_THRESHOLD_DAYS = 30

def send_summary_report(critical_certs: list):
    """Envoie un rapport récapitulatif par email avec tous les certificats critiques."""
    # Lire la configuration SMTP depuis les variables d'environnement
    sender_email = os.getenv("SMTP_SENDER_EMAIL")
    password = os.getenv("SMTP_PASSWORD")
    recipients_str = os.getenv("ALERT_RECIPIENTS")
    smtp_server = os.getenv("SMTP_SERVER")
    smtp_port = int(os.getenv("SMTP_PORT", 587))

    # Vérifier que toutes les variables nécessaires sont présentes
    if not all([sender_email, password, recipients_str, smtp_server]):
        print("-> AVERTISSEMENT: Variables d'environnement pour l'email non configurées. Envoi annulé.")
        return

    recipients = [email.strip() for email in recipients_str.split(',')]
    
    msg = EmailMessage()
    msg['Subject'] = f"🚨 Rapport SSL : {len(critical_certs)} certificat(s) requièrent votre attention"
    msg['From'] = sender_email
    msg['To'] = ", ".join(recipients)

    body_lines = ["Rapport de surveillance SSL du " + datetime.now().strftime('%d/%m/%Y à %H:%M'), "\n"]
    for cert in critical_certs:
        body_lines.append("----------------------------------------")
        body_lines.append(f"Domaine : {cert['domain']}")
        body_lines.append(f"Statut  : {cert['status']}")
        if cert.get('days_left') is not None:
             body_lines.append(f"Jours restants : {cert['days_left']}")
        if cert.get('error_message'):
            body_lines.append(f"Erreur : {cert['error_message']}")
        body_lines.append("\n")

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

async def get_ssl_expiry_info(hostname: str) -> Dict:
    """Vérifie le certificat SSL d'un domaine de manière asynchrone."""
    context = ssl.create_default_context()
    try:
        # Utilise asyncio pour une connexion réseau non bloquante avec un timeout
        reader, writer = await asyncio.wait_for(
            asyncio.open_connection(hostname, 443, ssl=context),
            timeout=10.0
        )
        
        cert = writer.get_extra_info('peercert')
        writer.close()
        await writer.wait_closed()

        expiry_date_str = cert['notAfter']
        expiry_date = datetime.strptime(expiry_date_str, '%b %d %H:%M:%S %Y %Z')
        days_left = (expiry_date - datetime.now()).days
        
        status = "OK"
        if days_left < 0: status = "Expiré"
        elif days_left < ALERT_THRESHOLD_DAYS: status = "Expire bientôt"

        return {"domain": hostname, "status": status, "days_left": days_left, "expiry_date": expiry_date.isoformat()}
    except Exception as e:
        return {"domain": hostname, "status": "Erreur", "error_message": f"{type(e).__name__}: {e}"}

def read_domains() -> List[str]:
    """Lit la liste des domaines depuis le fichier JSON."""
    try:
        with open(DOMAINS_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

async def main():
    """Fonction principale de la tâche de fond."""
    print(f"--- Lancement de la tâche de fond de vérification SSL ({datetime.now().strftime('%d/%m/%Y %H:%M:%S')}) ---")
    domains = read_domains()
    
    if not domains:
        print("Aucun domaine à vérifier. Tâche terminée.")
        with open(STATUS_FILE, "w") as f:
            json.dump([], f)
        return

    # Exécute toutes les vérifications en parallèle pour une performance maximale
    tasks = [get_ssl_expiry_info(domain) for domain in domains]
    results = await asyncio.gather(*tasks)
    
    # Écrit le rapport JSON qui sera lu par le dashboard
    with open(STATUS_FILE, "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"-> Vérification terminée. {len(results)} domaines traités. Rapport JSON mis à jour.")

    # Filtre les certificats critiques pour l'alerte email
    critical_certs = [cert for cert in results if cert['status'] in ['Expire bientôt', 'Expiré', 'Erreur']]
    if critical_certs:
        send_summary_report(critical_certs)
    else:
        print("-> Tous les certificats sont OK. Aucun email envoyé.")

if __name__ == "__main__":
    asyncio.run(main())