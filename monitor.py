# Fichier: monitor.py
import ssl
import socket
from datetime import datetime

def get_ssl_expiry_info(hostname: str) -> dict:
    """
    Vérifie le certificat SSL d'un domaine et retourne les informations d'expiration.
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

                return {
                    "domain": hostname,
                    "status": "OK",
                    "days_left": days_left,
                    "expiry_date": expiry_date.strftime('%Y-%m-%d')
                }

    except Exception as e:
        return {
            "domain": hostname,
            "status": "Erreur",
            "error_message": str(e)
        }

def main():
    """
    Fonction principale pour lire les domaines et lancer les vérifications.
    """
    print("--- Lancement de la surveillance des certificats SSL ---")

    with open('domains.txt', 'r') as file:
        domains = [line.strip() for line in file if line.strip()]

    for domain in domains:
        info = get_ssl_expiry_info(domain)
        if info['status'] == "OK":
            print(f"✅ {info['domain']} - OK. Expire dans {info['days_left']} jours (le {info['expiry_date']}).")
        else:
            print(f"❌ {info['domain']} - Erreur : {info['error_message']}")

    print("\n--- Vérification terminée ---")


if __name__ == "__main__":
    main()