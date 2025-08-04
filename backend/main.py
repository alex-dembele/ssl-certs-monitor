import json
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from monitor_logic import get_ssl_expiry_info

app = FastAPI()

# --- Configuration CORS pour autoriser le frontend à appeler l'API ---
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # En production, mettez l'URL de votre frontend
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DOMAINS_FILE = "domains.json"

class Domain(BaseModel):
    name: str

def read_domains() -> List[str]:
    try:
        with open(DOMAINS_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def write_domains(domains: List[str]):
    with open(DOMAINS_FILE, "w") as f:
        json.dump(sorted(list(set(domains))), f, indent=2)

@app.get("/api/status")
async def get_all_statuses():
    """Récupère et vérifie le statut de tous les domaines enregistrés."""
    domains = read_domains()
    statuses = [get_ssl_expiry_info(domain) for domain in domains]
    return statuses

@app.post("/api/domains")
async def add_domain(domain: Domain):
    """Ajoute un nouveau domaine à la liste de surveillance."""
    domains = read_domains()
    if domain.name in domains:
        raise HTTPException(status_code=409, detail="Le domaine existe déjà.")
    domains.append(domain.name)
    write_domains(domains)
    return {"message": f"Domaine '{domain.name}' ajouté avec succès.", "domain": domain.name}

@app.delete("/api/domains/{domain_name}")
async def delete_domain(domain_name: str):
    """Supprime un domaine de la liste de surveillance."""
    domains = read_domains()
    if domain_name not in domains:
        raise HTTPException(status_code=404, detail="Domaine non trouvé.")
    domains.remove(domain_name)
    write_domains(domains)
    return {"message": f"Domaine '{domain_name}' supprimé avec succès."}