# Fichier: backend/main.py
import re
import os
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List
from database import Domain, SessionLocal, add_domains, delete_domain as remove_domain, initialize_database, list_domains, list_statuses
from alerts import AlertPolicy, get_policy
# On importe la fonction de check unique
from cron_job import get_ssl_expiry_info

app = FastAPI()
backend_api_token = os.getenv("BACKEND_API_TOKEN")
if os.getenv("APP_ENV", "development") == "production" and not backend_api_token:
    raise RuntimeError("BACKEND_API_TOKEN must be configured in production")

allowed_origins = [
    origin.strip()
    for origin in os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
    if origin.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "DELETE", "OPTIONS"],
    allow_headers=["Authorization", "Content-Type"],
)

class DomainList(BaseModel): domains: List[str]
class AlertPolicyUpdate(BaseModel):
    threshold_days: int = Field(default=30, ge=1, le=3650)
    reminder_interval_hours: int = Field(default=168, ge=0, le=8760)
    enabled: bool = True
    channel: str = Field(default="email", pattern="^(email|webhook|slack|teams|discord)$")

initialize_database()

async def require_api_auth(authorization: str | None = Header(default=None)):
    if backend_api_token and authorization != f"Bearer {backend_api_token}":
        raise HTTPException(status_code=401, detail="Authentification requise.")

@app.get("/api/domains", dependencies=[Depends(require_api_auth)])
async def get_domains():
    with SessionLocal() as session:
        return {"domains": list_domains(session)}

@app.get("/api/status", dependencies=[Depends(require_api_auth)])
async def get_status():
    with SessionLocal() as session:
        return list_statuses(session)

@app.post("/api/domains/bulk", dependencies=[Depends(require_api_auth)])
async def add_bulk_domains(domain_list: DomainList):
    domain_regex = re.compile(r'^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$')
    valid_domains = {d.strip() for d in domain_list.domains if domain_regex.match(d.strip())}
    if not valid_domains:
        raise HTTPException(status_code=400, detail="Aucun nouveau domaine valide (format invalide ou doublon).")

    with SessionLocal() as session:
        added = add_domains(session, valid_domains)
    if not added:
        raise HTTPException(status_code=400, detail="Aucun nouveau domaine valide (format invalide ou doublon).")
    return {"message": f"{added} domaine(s) ajouté(s) à la liste de surveillance."}

@app.get("/api/check/{domain_name}", dependencies=[Depends(require_api_auth)])
async def check_single_domain(domain_name: str):
    return await get_ssl_expiry_info(domain_name)

@app.delete("/api/domains/{domain_name}", dependencies=[Depends(require_api_auth)])
async def delete_domain(domain_name: str):
    with SessionLocal() as session:
        deleted = remove_domain(session, domain_name)
    if not deleted:
        raise HTTPException(status_code=404, detail="Domaine non trouvé.")
    return {"message": f"Domaine '{domain_name}' supprimé."}

@app.get("/api/domains/{domain_name}/alert-policy", dependencies=[Depends(require_api_auth)])
async def get_alert_policy(domain_name: str):
    with SessionLocal() as session:
        if not session.get(Domain, domain_name):
            raise HTTPException(status_code=404, detail="Domaine non trouvé.")
        policy = get_policy(session, domain_name)
        return {
            "domain": domain_name,
            "threshold_days": policy.threshold_days,
            "reminder_interval_hours": policy.reminder_interval_hours,
            "enabled": policy.enabled,
            "channel": policy.channel,
        }

@app.put("/api/domains/{domain_name}/alert-policy", dependencies=[Depends(require_api_auth)])
async def update_alert_policy(domain_name: str, update: AlertPolicyUpdate):
    with SessionLocal() as session:
        if not session.get(Domain, domain_name):
            raise HTTPException(status_code=404, detail="Domaine non trouvé.")
        policy = session.get(AlertPolicy, domain_name) or AlertPolicy(domain_name=domain_name)
        policy.threshold_days = update.threshold_days
        policy.reminder_interval_hours = update.reminder_interval_hours
        policy.enabled = update.enabled
        policy.channel = update.channel
        session.add(policy)
        session.commit()
        return {"message": "Politique d'alerte mise à jour.", **update.model_dump()}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
