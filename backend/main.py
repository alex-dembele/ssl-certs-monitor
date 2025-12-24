# Fichier: backend/main.py
import json
import re
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
# On importe la fonction de check unique
from cron_job import get_ssl_expiry_info

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

DOMAINS_FILE = "domains.json"
class DomainList(BaseModel): domains: List[str]

def read_domains() -> List[str]:
    try:
        with open(DOMAINS_FILE, "r") as f: return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        with open(DOMAINS_FILE, "w") as f: json.dump([], f)
        return []
def write_domains(domains: List[str]):
    with open(DOMAINS_FILE, "w") as f: json.dump(sorted(list(set(domains))), f, indent=2)

@app.get("/api/domains")
async def get_domains():
    return {"domains": read_domains()}

@app.post("/api/domains/bulk")
async def add_bulk_domains(domain_list: DomainList):
    current_domains = read_domains()
    domain_regex = re.compile(r'^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$')
    valid_new_domains = { d.strip() for d in domain_list.domains if domain_regex.match(d.strip()) and d.strip() not in current_domains }
    if not valid_new_domains:
        raise HTTPException(status_code=400, detail="Aucun nouveau domaine valide (format invalide ou doublon).")
    
    write_domains(current_domains + list(valid_new_domains))
    return {"message": f"{len(valid_new_domains)} domaine(s) ajouté(s) à la liste de surveillance."}

@app.get("/api/check/{domain_name}")
async def check_single_domain(domain_name: str):
    return await get_ssl_expiry_info(domain_name)

@app.delete("/api/domains/{domain_name}")
async def delete_domain(domain_name: str):
    domains = read_domains()
    if domain_name not in domains:
        raise HTTPException(status_code=404, detail="Domaine non trouvé.")
    domains.remove(domain_name)
    write_domains(domains)
    return {"message": f"Domaine '{domain_name}' supprimé."}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}