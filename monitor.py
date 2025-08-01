# Fichier: monitor.py
import ssl
import socket
import json
from datetime import datetime

# Seuil en jours pour l'alerte "Expire bientôt"
ALERT_THRESHOLD_DAYS = 30

def get_ssl_expiry_info(hostname: str) -> dict:
    """
    Vérifie le certificat SSL et retourne un dictionnaire détaillé.
    """
    status = ""
    try:
        context = ssl.create_default_context()
        with socket.create_connection((hostname, 443), timeout=10) as sock:
            with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                cert = ssock.getpeercert()

                expiry_date_str = cert['notAfter']
                expiry_date = datetime.strptime(expiry_date_str, '%b %d %H:%M:%S %Y %Z')
                days_left = (expiry_date - datetime.now()).days

                # Définir le statut en fonction des jours restants
                if days_left < 0:
                    status = "Expiré"
                elif days_left < ALERT_THRESHOLD_DAYS:
                    status = "Expire bientôt"
                else:
                    status = "OK"

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

def main():
    """
    Fonction principale qui génère le rapport ssl_status.json.
    """
    print("--- Lancement de la surveillance des certificats SSL ---")

    try:
        with open('domains.txt', 'r') as file:
            domains = [line.strip() for line in file if line.strip()]
    except FileNotFoundError:
        print("❌ Erreur : Le fichier 'domains.txt' est introuvable.")
        return

    results = []
    for domain in domains:
        print(f"Vérification de {domain}...")
        info = get_ssl_expiry_info(domain)
        results.append(info)

    # Écrire les résultats dans un fichier JSON
    with open('ssl_status.json', 'w') as json_file:
        json.dump(results, json_file, indent=4)

    print("\n✅ Rapport 'ssl_status.json' généré avec succès.")
    print("--- Vérification terminée ---")


if __name__ == "__main__":
    main()