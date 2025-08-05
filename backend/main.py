# Fichier: backend/main.py

import json
import re
from typing import List
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from monitor_logic import get_ssl_expiry_info

app = FastAPI()

# --- Configuration CORS ---
# Permet au frontend (tournant sur un autre port) d'appeler cette API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Pour la simplicité, on autorise tout. En production, mettez l'URL de votre frontend.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DOMAINS_FILE = "domains.json"

# --- Modèles Pydantic pour la validation des données entrantes ---
class Domain(BaseModel):
    name: str

class DomainList(BaseModel):
    domains: List[str]

# --- Fonctions utilitaires pour lire/écrire dans le fichier de domaines ---
def read_domains() -> List[str]:
    """Lit la liste des domaines depuis le fichier JSON."""
    try:
        with open(DOMAINS_FILE, "r") as f:
            domains = json.load(f)
            return domains
    except (FileNotFoundError, json.JSONDecodeError):
        # Si le fichier n'existe pas ou est vide/corrompu, on retourne une liste vide
        return []

def write_domains(domains: List[str]):
    """Écrit la liste des domaines dans le fichier JSON, en s'assurant qu'elle est unique et triée."""
    # Utiliser un set pour garantir l'unicité puis reconvertir en liste triée
    unique_sorted_domains = sorted(list(set(domains)))
    with open(DOMAINS_FILE, "w") as f:
        json.dump(unique_sorted_domains, f, indent=2)

# --- Points de terminaison (endpoints) de l'API ---

@app.get("/api/status")
async def get_all_statuses():
    """Récupère et vérifie le statut de tous les domaines enregistrés."""
    domains = read_domains()
    # Utilisation d'une liste en compréhension pour appeler la fonction de vérification sur chaque domaine
    statuses = [get_ssl_expiry_info(domain) for domain in domains]
    return statuses

@app.post("/api/domains")
async def add_domain(domain: Domain):
    """Ajoute un nouveau domaine unique à la liste de surveillance."""
    domains = read_domains()
    if domain.name in domains:
        raise HTTPException(status_code=409, detail="Le domaine existe déjà.")
    domains.append(domain.name)
    write_domains(domains)
    return {"message": f"Domaine '{domain.name}' ajouté avec succès.", "domain": domain.name}

@app.post("/api/domains/bulk")
async def add_bulk_domains(domain_list: DomainList):
    """Ajoute une liste de domaines, en ignorant les doublons et les formats invalides."""
    current_domains = read_domains()
    
    # Expression régulière pour valider le format de base d'un nom de domaine
    domain_regex = re.compile(
        r'^(?:[a-zA-Z0-9]'  # Doit commencer par une lettre ou un chiffre
        r'(?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)' # Sous-domaines
        r'+[a-zA-Z]{2,}$' # TLD (Top-Level Domain)
    )
    
    valid_new_domains = {
        domain.strip() for domain in domain_list.domains 
        if domain.strip() and domain_regex.match(domain.strip()) and domain.strip() not in current_domains
    }
    
    if not valid_new_domains:
        raise HTTPException(status_code=400, detail="Aucun nouveau domaine valide à ajouter.")
        
    updated_domains = current_domains + list(valid_new_domains)
    write_domains(updated_domains)
    
    return {"message": f"{len(valid_new_domains)} nouveau(x) domaine(s) ajouté(s) avec succès."}

@app.delete("/api/domains/{domain_name}")
async def delete_domain(domain_name: str):
    """Supprime un domaine de la liste de surveillance."""
    domains = read_domains()
    if domain_name not in domains:
        raise HTTPException(status_code=404, detail="Domaine non trouvé.")
    domains.remove(domain_name)
    write_domains(domains)
    return {"message": f"Domaine '{domain_name}' supprimé avec succès."}