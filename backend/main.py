# Fichier: backend/main.py
import os
import json
from datetime import datetime, timezone
from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import Any, List, Literal
from database import Domain, SessionLocal, add_domains, delete_domain as remove_domain, initialize_database, list_domains, list_statuses
from alerts import AlertEvent, AlertPolicy, AlertRule, DomainContext, VALID_SCOPES, get_policy, resolve_alert_rule, rule_to_dict
from settings import DEFAULTS, SettingsAuditLog, get_settings, settings_to_dict
from notifications import deliver_events
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

class SettingsUpdate(BaseModel):
    threshold_days: int = Field(default=30, ge=1, le=3650)
    check_interval_minutes: int = Field(default=60, ge=1, le=10080)
    channel: str = Field(default="email", pattern="^(email|webhook|slack|teams|discord)$")
    recipients: List[str] = Field(default_factory=list, max_length=50)
    enabled: bool = True

class NotificationTest(BaseModel):
    scope: str = Field(default="personal", pattern="^(personal|organization)$")

class AlertRulePayload(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    scope_type: Literal["organization", "team", "project", "environment", "domain"]
    scope_key: str = Field(min_length=1, max_length=253)
    priority: int = Field(default=0, ge=-10000, le=10000)
    severity: str = Field(default="warning", pattern="^(info|warning|critical)$")
    threshold_days: int = Field(default=30, ge=1, le=3650)
    reminder_interval_hours: int = Field(default=168, ge=0, le=8760)
    conditions: dict[str, Any] = Field(default_factory=dict)
    channels: List[Literal["email", "webhook", "slack", "teams", "discord"]] = Field(default_factory=lambda: ["email"])
    enabled: bool = True

class DomainContextUpdate(BaseModel):
    organization: str | None = Field(default=None, max_length=128)
    team: str | None = Field(default=None, max_length=128)
    project: str | None = Field(default=None, max_length=128)
    environment: str | None = Field(default=None, max_length=64)
    criticality: str | None = Field(default=None, max_length=32)

class AlertPreviewRequest(BaseModel):
    domain: str
    certificate: dict[str, Any]

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
    invalid = []
    candidates = []
    duplicates = []
    seen = set()
    for value in domain_list.domains:
        normalized = normalize_domain(value)
        if normalized is None:
            invalid.append({"value": value, "reason": "Format de domaine invalide."})
        elif normalized in seen:
            duplicates.append(normalized)
        else:
            seen.add(normalized)
            candidates.append(normalized)

    with SessionLocal() as session:
        added = add_domains(session, candidates)
    duplicates.extend(domain for domain in candidates if domain not in added)
    return {
        "message": f"{len(added)} domaine(s) ajouté(s), {len(duplicates)} doublon(s), {len(invalid)} entrée(s) invalide(s).",
        "added": added,
        "duplicates": sorted(set(duplicates)),
        "invalid": invalid,
    }

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

@app.get("/api/settings", dependencies=[Depends(require_api_auth)])
async def read_settings():
    with SessionLocal() as session:
        return {
            "personal": settings_to_dict(get_settings(session, "personal")),
            "organization": settings_to_dict(get_settings(session, "organization")),
            "smtp_configured": bool(os.getenv("SMTP_SERVER") and os.getenv("SMTP_SENDER_EMAIL") and os.getenv("SMTP_PASSWORD")),
        }

@app.put("/api/settings/{scope}", dependencies=[Depends(require_api_auth)])
async def update_settings(scope: str, update: SettingsUpdate):
    if scope not in {"personal", "organization"}:
        raise HTTPException(status_code=422, detail="Portée de paramètres invalide.")
    with SessionLocal() as session:
        settings = get_settings(session, scope)
        changed = []
        for field in ("threshold_days", "check_interval_minutes", "channel", "enabled"):
            value = getattr(update, field)
            if getattr(settings, field) != value:
                setattr(settings, field, value)
                changed.append(field)
        recipients = [recipient.strip() for recipient in update.recipients if recipient.strip()]
        if json.loads(settings.recipients or "[]") != recipients:
            settings.recipients = json.dumps(recipients)
            changed.append("recipients")
        settings.updated_at = datetime.now(timezone.utc).replace(tzinfo=None)
        session.add(settings)
        session.add(SettingsAuditLog(scope=scope, changed_fields=json.dumps(changed)))
        session.commit()
        return settings_to_dict(settings)

@app.post("/api/notifications/test", dependencies=[Depends(require_api_auth)])
async def test_notification(request: NotificationTest):
    with SessionLocal() as session:
        settings = get_settings(session, request.scope)
        recipients = json.loads(settings.recipients or "[]")
    if not settings.enabled:
        raise HTTPException(status_code=400, detail="Les notifications sont désactivées pour cette portée.")
    event = AlertEvent("notification-test", "test", settings.channel, {"status": "OK", "days_left": None})
    deliveries = deliver_events([event], email_recipients=recipients or None)
    delivery = deliveries[0]
    if not delivery.success:
        raise HTTPException(status_code=502, detail=delivery.error_message or "Échec de la notification de test.")
    return {"message": "Notification de test envoyée.", "channel": settings.channel, "attempts": delivery.attempts}

def require_team(team_id: str | None) -> str:
    if not team_id:
        raise HTTPException(status_code=403, detail="X-Team-Id est requis pour gérer les règles.")
    return team_id

@app.get("/api/alert-rules", dependencies=[Depends(require_api_auth)])
async def list_alert_rules(team_id: str | None = Header(default=None, alias="X-Team-Id")):
    owner = require_team(team_id)
    with SessionLocal() as session:
        return {"rules": [rule_to_dict(rule) for rule in session.query(AlertRule).filter(AlertRule.owner_team == owner).order_by(AlertRule.priority.desc(), AlertRule.id)]}

@app.post("/api/alert-rules", dependencies=[Depends(require_api_auth)])
async def create_alert_rule(rule: AlertRulePayload, team_id: str | None = Header(default=None, alias="X-Team-Id")):
    owner = require_team(team_id)
    if rule.scope_type not in VALID_SCOPES:
        raise HTTPException(status_code=422, detail="Portée de règle invalide.")
    with SessionLocal() as session:
        created = AlertRule(
            name=rule.name, scope_type=rule.scope_type, scope_key=rule.scope_key, owner_team=owner,
            priority=rule.priority, severity=rule.severity, threshold_days=rule.threshold_days,
            reminder_interval_hours=rule.reminder_interval_hours, conditions=json.dumps(rule.conditions),
            channels=json.dumps(rule.channels), enabled=rule.enabled,
        )
        session.add(created)
        session.commit()
        return rule_to_dict(created)

@app.put("/api/alert-rules/{rule_id}", dependencies=[Depends(require_api_auth)])
async def update_alert_rule(rule_id: int, rule: AlertRulePayload, team_id: str | None = Header(default=None, alias="X-Team-Id")):
    owner = require_team(team_id)
    with SessionLocal() as session:
        current = session.get(AlertRule, rule_id)
        if current is None:
            raise HTTPException(status_code=404, detail="Règle non trouvée.")
        if current.owner_team != owner:
            raise HTTPException(status_code=403, detail="Cette règle appartient à une autre équipe.")
        for field in ("name", "scope_type", "scope_key", "priority", "severity", "threshold_days", "reminder_interval_hours", "enabled"):
            setattr(current, field, getattr(rule, field))
        current.conditions = json.dumps(rule.conditions)
        current.channels = json.dumps(rule.channels)
        session.commit()
        return rule_to_dict(current)

@app.delete("/api/alert-rules/{rule_id}", dependencies=[Depends(require_api_auth)])
async def delete_alert_rule(rule_id: int, team_id: str | None = Header(default=None, alias="X-Team-Id")):
    owner = require_team(team_id)
    with SessionLocal() as session:
        current = session.get(AlertRule, rule_id)
        if current is None:
            raise HTTPException(status_code=404, detail="Règle non trouvée.")
        if current.owner_team != owner:
            raise HTTPException(status_code=403, detail="Cette règle appartient à une autre équipe.")
        session.delete(current)
        session.commit()
    return {"message": "Règle supprimée."}

@app.put("/api/domains/{domain_name}/context", dependencies=[Depends(require_api_auth)])
async def update_domain_context(domain_name: str, update: DomainContextUpdate, team_id: str | None = Header(default=None, alias="X-Team-Id")):
    owner = require_team(team_id)
    with SessionLocal() as session:
        if not session.get(Domain, domain_name):
            raise HTTPException(status_code=404, detail="Domaine non trouvé.")
        if update.team and update.team != owner:
            raise HTTPException(status_code=403, detail="Une équipe ne peut pas modifier le contexte d'une autre équipe.")
        context = session.get(DomainContext, domain_name) or DomainContext(domain_name=domain_name)
        for field in ("organization", "team", "project", "environment", "criticality"):
            setattr(context, field, getattr(update, field))
        session.add(context)
        session.commit()
        return {field: getattr(context, field) for field in ("domain_name", "organization", "team", "project", "environment", "criticality")}

@app.post("/api/alert-rules/preview", dependencies=[Depends(require_api_auth)])
async def preview_alert_rule(request: AlertPreviewRequest, team_id: str | None = Header(default=None, alias="X-Team-Id")):
    require_team(team_id)
    with SessionLocal() as session:
        rule = resolve_alert_rule(session, request.domain, request.certificate)
        if rule is None:
            return {"matched": False, "explanation": "Aucune règle spécifique ; politique par défaut."}
        return {"matched": True, "explanation": f"Règle '{rule.name}' (priorité {rule.priority})", "rule": rule_to_dict(rule)}

@app.post("/api/alert-rules/{rule_id}/test", dependencies=[Depends(require_api_auth)])
async def test_alert_rule(rule_id: int, team_id: str | None = Header(default=None, alias="X-Team-Id")):
    owner = require_team(team_id)
    with SessionLocal() as session:
        rule = session.get(AlertRule, rule_id)
        if rule is None:
            raise HTTPException(status_code=404, detail="Règle non trouvée.")
        if rule.owner_team != owner:
            raise HTTPException(status_code=403, detail="Cette règle appartient à une autre équipe.")
        return {"dry_run": True, "message": "Règle valide ; aucune notification réelle n'a été envoyée.", "rule": rule_to_dict(rule)}
