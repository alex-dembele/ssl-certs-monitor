# Fichier: backend/cron_job.py
import asyncio
import ssl
import json
from datetime import datetime
from typing import List, Dict

# Ce script sera exécuté par notre "cron" Docker.

DOMAINS_FILE = "domains.json"
STATUS_FILE = "/app/data/ssl_status.json" # Chemin dans le volume partagé
ALERT_THRESHOLD_DAYS = 30

async def get_ssl_expiry_info(hostname: str) -> Dict:
    # ... (La fonction asynchrone est identique à celle de la version précédente)
    context = ssl.create_default_context()
    try:
        _, writer = await asyncio.wait_for(asyncio.open_connection(hostname, 443, ssl=context), timeout=5.0)
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
    try:
        with open(DOMAINS_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return []

async def main():
    print(f"--- Lancement de la tâche de fond de vérification SSL ({datetime.now()}) ---")
    domains = read_domains()
    if not domains:
        print("Aucun domaine à vérifier. Tâche terminée.")
        # On écrit un fichier vide pour que le dashboard se vide aussi
        with open(STATUS_FILE, "w") as f:
            json.dump([], f)
        return

    tasks = [get_ssl_expiry_info(domain) for domain in domains]
    results = await asyncio.gather(*tasks)
    
    with open(STATUS_FILE, "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"Vérification terminée. {len(results)} domaines traités. Rapport mis à jour.")

if __name__ == "__main__":
    asyncio.run(main())