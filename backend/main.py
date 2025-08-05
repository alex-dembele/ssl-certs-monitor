# Fichier: backend/main.py

import json
import re
import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List

# On importe la fonction de vérification depuis notre script de la tâche de fond
from cron_job import get_ssl_expiry_info

# --- Configuration de l'application FastAPI ---
app = FastAPI(
    title="SSL-Cert-Monitor API",
    description="API pour gérer la liste des domaines à surveiller.",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Pour le développement. En production, limitez à l'URL de votre frontend.
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Constantes et Modèles Pydantic ---
DOMAINS_FILE = "domains.json"

class Domain(BaseModel):
    name: str

class DomainList(BaseModel):
    domains: List[str]

# --- Fonctions utilitaires pour lire/écrire dans le fichier de domaines ---
def read_domains() -> List[str]:
    """Lit la liste des domaines depuis le fichier JSON."""
    try:
        with open(DOMAINS_FILE, "r") as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        # Si le fichier n'existe pas ou est vide/corrompu, on retourne une liste vide.
        return []

def write_domains(domains: List[str]):
    """Écrit la liste des domaines dans le fichier JSON, en s'assurant de l'unicité et de l'ordre."""
    # set() pour garantir l'unicité, sorted() pour un ordre prévisible
    unique_sorted_domains = sorted(list(set(domains)))
    with open(DOMAINS_FILE, "w") as f:
        json.dump(unique_sorted_domains, f, indent=2)


# --- Endpoints de l'API ---

@app.get("/api/check/{domain_name}", summary="Vérifier un seul domaine")
async def check_single_domain(domain_name: str):
    """
    Exécute une vérification SSL/TLS pour un seul domaine spécifié et retourne son statut immédiatement.
    C'est utilisé pour le feedback instantané lors de l'ajout d'un nouveau domaine.
    """
    return await get_ssl_expiry_info(domain_name)

@app.post("/api/domains/bulk", summary="Ajouter des domaines en masse")
async def add_bulk_domains(domain_list: DomainList):
    """
    Ajoute une liste de domaines. Valide le format, ignore les doublons
    et les domaines déjà existants.
    """
    current_domains = read_domains()
    domain_regex = re.compile(
        r'^(?:[a-zA-Z0-9](?:[a-zA-Z0-9-]{0,61}[a-zA-Z0-9])?\.)+[a-zA-Z]{2,}$'
    )
    
    valid_new_domains = {
        domain.strip().lower() for domain in domain_list.domains 
        if domain_regex.match(domain.strip()) and domain.strip().lower() not in current_domains
    }
    
    if not valid_new_domains:
        raise HTTPException(
            status_code=400, 
            detail="Aucun nouveau domaine valide à ajouter. Ils sont peut-être déjà dans la liste ou leur format est invalide."
        )
        
    updated_domains = current_domains + list(valid_new_domains)
    write_domains(updated_domains)
    
    return {"message": f"{len(valid_new_domains)} nouveau(x) domaine(s) ajouté(s)."}

@app.delete("/api/domains/{domain_name}", summary="Supprimer un domaine")
async def delete_domain(domain_name: str):
    """Supprime un domaine de la liste de surveillance."""
    domains = read_domains()
    domain_to_delete = domain_name.lower()

    if domain_to_delete not in domains:
        raise HTTPException(status_code=404, detail="Domaine non trouvé.")
    
    domains.remove(domain_to_delete)
    write_domains(domains)
    
    return {"message": f"Domaine '{domain_name}' supprimé."}