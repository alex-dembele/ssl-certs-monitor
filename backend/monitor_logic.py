import ssl
import socket
from datetime import datetime

# Seuil en jours pour que le statut passe à "Expire bientôt"
ALERT_THRESHOLD_DAYS = 30

def get_ssl_expiry_info(hostname: str) -> dict:
    """
    Vérifie le certificat SSL d'un domaine et retourne un dictionnaire détaillé.
    """
    try:
        # Crée un contexte SSL par défaut pour la connexion
        context = ssl.create_default_context()
        
        # Établit une connexion TCP avec le serveur sur le port 443 (HTTPS)
        # Le timeout de 5 secondes évite que le script reste bloqué indéfiniment
        with socket.create_connection((hostname, 443), timeout=5) as sock:
            # Enveloppe le socket TCP dans une couche SSL/TLS
            with context.wrap_socket(sock, server_hostname=hostname) as ssock:
                # Récupère les informations du certificat du pair (le serveur)
                cert = ssock.getpeercert()
                
                # Extrait et parse la date d'expiration
                expiry_date_str = cert['notAfter']
                expiry_date = datetime.strptime(expiry_date_str, '%b %d %H:%M:%S %Y %Z')
                
                # Calcule le nombre de jours restants
                days_left = (expiry_date - datetime.now()).days
                
                # Définit un statut clair en fonction des jours restants
                status = "OK"
                if days_left < 0:
                    status = "Expiré"
                elif days_left < ALERT_THRESHOLD_DAYS:
                    status = "Expire bientôt"

                return {
                    "domain": hostname,
                    "status": status,
                    "days_left": days_left,
                    "expiry_date": expiry_date.isoformat() # Format standard pour les dates
                }
    except Exception as e:
        # En cas d'erreur (domaine non trouvé, problème de connexion, etc.), retourne un statut d'erreur
        return {
            "domain": hostname,
            "status": "Erreur",
            "error_message": str(e)
        }