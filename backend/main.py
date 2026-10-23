# Fichier: backend/main.py
import re
import os
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from database import SessionLocal, add_domains, delete_domain as remove_domain, initialize_database, list_domains, list_statuses
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

@app.get("/health")
async def health_check():
    return {"status": "healthy"}
