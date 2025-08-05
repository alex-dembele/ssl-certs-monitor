# Fichier: backend/main.py

import json
import re
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List

# On importe la fonction de vérification unique depuis notre script de fond
# Cela évite de dupliquer le code de la logique SSL
from cron_job import get_ssl_expiry_info

# --- Initialisation de l'API ---
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Constantes et Modèles ---
DOMAINS_FILE = "domains.json"

class DomainList(BaseModel):
    domains: List[str]

# --- Fonctions utilitaires pour lire/écrire la liste des domaines ---
def read_domains() -> List[str]:
    """Lit la liste des domaines depuis le fichier JSON."""
    try:
        with open(DOMAINS_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # Si le fichier n'existe pas ou est corrompu, on en crée un vide
        with open(DOMAINS_FILE, "w") as f:
            json.dump([], f)
        return []

def write_domains(domains: List[str]):
    """Écrit la liste des domaines dans le fichier JSON, en la triant et en supprimant les doublons."""
    with open(DOMAINS_FILE, "w") as f:
        json.dump(sorted(list(set(domains))), f, indent=2)

# --- Endpoints de l'API ---

@app.get("/api/domains")
async def get_domains():
    """Retourne la liste complète des noms de domaines surveillés."""
    return {"domains": read_domains()}

@app.get("/api/check/{domain_name}")
async def check_single_domain(domain_name: str):
    """
    Effectue une vérification SSL à la demande pour un seul domaine.
    C'est l'endpoint que le frontend appelle après un ajout pour un affichage immédiat.
    """
    return await get_ssl_expiry_info(domain_name)

@app.post("/api/domains/bulk")
async def add_bulk_domains(domain_list: DomainList):
    """
    Ajoute un ou plusieurs domaines à la liste de surveillance.
    Répond instantanément sans faire de vérification.
    """
    current_domains = read_domains()
    domain_regex = re.compile(r'^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$')
    
    valid_new_domains = {
        domain.strip() for domain in domain_list.domains 
        if domain_regex.match(domain.strip()) and domain.strip() not in current_domains
    }
    
    if not valid_new_domains:
        raise HTTPException(status_code=400, detail="Aucun nouveau domaine valide à ajouter (format invalide ou doublon).")
        
    updated_domains = current_domains + list(valid_new_domains)
    write_domains(updated_domains)
    
    return {"message": f"{len(valid_new_domains)} domaine(s) ajouté(s) à la liste de surveillance."}

@app.delete("/api/domains/{domain_name}")
async def delete_domain(domain_name: str):
    """Supprime un domaine de la liste de surveillance."""
    domains = read_domains()
    if domain_name not in domains:
        raise HTTPException(status_code=404, detail="Domaine non trouvé.")
    
    domains.remove(domain_name)
    write_domains(domains)
    
    return {"message": f"Domaine '{domain_name}' supprimé."}