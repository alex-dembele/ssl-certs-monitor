"""Alert policies, state transitions and notification journal."""

from dataclasses import dataclass
from datetime import datetime, timedelta
import fnmatch
import json
from typing import Iterable

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Session

try:
    from .database import Base
    from .settings import GLOBAL_SCOPE, NotificationSettings, get_settings
except ImportError:
    from database import Base
    from settings import GLOBAL_SCOPE, NotificationSettings, get_settings


class AlertPolicy(Base):
    __tablename__ = "alert_policies"

    domain_name = Column(String(253), ForeignKey("domains.name", ondelete="CASCADE"), primary_key=True)
    threshold_days = Column(Integer, nullable=False, default=30)
    reminder_interval_hours = Column(Integer, nullable=False, default=168)
    enabled = Column(Boolean, nullable=False, default=True)
    channel = Column(String(32), nullable=False, default="email")


class AlertState(Base):
    __tablename__ = "alert_states"

    domain_name = Column(String(253), ForeignKey("domains.name", ondelete="CASCADE"), primary_key=True)
    state = Column(String(16), nullable=False, default="healthy")
    last_notified_at = Column(DateTime, nullable=True)


class NotificationLog(Base):
    __tablename__ = "notification_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    domain_name = Column(String(253), ForeignKey("domains.name", ondelete="CASCADE"), nullable=False)
    event_type = Column(String(16), nullable=False)
    channel = Column(String(32), nullable=False)
    success = Column(Boolean, nullable=False)
    error_message = Column(Text, nullable=True)
    idempotency_key = Column(String(64), nullable=True, unique=True)
    delivery_status = Column(String(16), nullable=False, default="delivered")
    attempts = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


class DomainContext(Base):
    __tablename__ = "domain_contexts"

    domain_name = Column(String(253), ForeignKey("domains.name", ondelete="CASCADE"), primary_key=True)
    organization = Column(String(128), nullable=True)
    team = Column(String(128), nullable=True)
    project = Column(String(128), nullable=True)
    environment = Column(String(64), nullable=True)
    criticality = Column(String(32), nullable=True)


class AlertRule(Base):
    __tablename__ = "alert_rules"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(128), nullable=False)
    scope_type = Column(String(32), nullable=False)
    scope_key = Column(String(253), nullable=False)
    owner_team = Column(String(128), nullable=False)
    priority = Column(Integer, nullable=False, default=0)
    severity = Column(String(32), nullable=False, default="warning")
    threshold_days = Column(Integer, nullable=False, default=30)
    reminder_interval_hours = Column(Integer, nullable=False, default=168)
    conditions = Column(Text, nullable=False, default="{}")
    channels = Column(Text, nullable=False, default='["email"]')
    enabled = Column(Boolean, nullable=False, default=True)


@dataclass(frozen=True)
class AlertEvent:
    domain: str
    event_type: str
    channel: str
    certificate: dict
    rule_id: int | None = None
    rule_name: str = "default"
    explanation: str = "Politique par défaut"
    # Moment où l'événement a été émis : distingue deux rappels du même certificat.
    occurred_at: str | None = None


VALID_SCOPES = {"organization", "team", "project", "environment", "domain"}


def _rule_conditions_match(rule: AlertRule, certificate: dict, context: DomainContext | None) -> bool:
    try:
        conditions = json.loads(rule.conditions or "{}")
    except json.JSONDecodeError:
        return False
    if conditions.get("statuses") and certificate.get("status") not in conditions["statuses"]:
        return False
    if conditions.get("error_types") and certificate.get("error_type") not in conditions["error_types"]:
        return False
    if conditions.get("criticalities") and (context is None or context.criticality not in conditions["criticalities"]):
        return False
    return True


def resolve_alert_rule(session: Session, domain: str, certificate: dict) -> AlertRule | None:
    context = session.get(DomainContext, domain)
    rules = session.query(AlertRule).filter(AlertRule.enabled.is_(True)).all()
    candidates = []
    context_values = {
        "organization": getattr(context, "organization", None),
        "team": getattr(context, "team", None),
        "project": getattr(context, "project", None),
        "environment": getattr(context, "environment", None),
    }
    specificity = {"organization": 1, "team": 2, "project": 3, "environment": 4, "domain": 5}
    for rule in rules:
        target = domain if rule.scope_type == "domain" else context_values.get(rule.scope_type)
        if not target or not fnmatch.fnmatch(target, rule.scope_key):
            continue
        if not _rule_conditions_match(rule, certificate, context):
            continue
        candidates.append((rule.priority, specificity.get(rule.scope_type, 0), rule.id, rule))
    return max(candidates, key=lambda item: (item[0], item[1], item[2]))[3] if candidates else None


def rule_to_dict(rule: AlertRule) -> dict:
    return {
        "id": rule.id, "name": rule.name, "scope_type": rule.scope_type, "scope_key": rule.scope_key,
        "owner_team": rule.owner_team, "priority": rule.priority, "severity": rule.severity,
        "threshold_days": rule.threshold_days, "reminder_interval_hours": rule.reminder_interval_hours,
        "conditions": json.loads(rule.conditions or "{}"), "channels": json.loads(rule.channels or "[]"),
        "enabled": rule.enabled,
    }


def get_policy(session: Session, domain: str, defaults: NotificationSettings | None = None) -> AlertPolicy:
    """Politique propre au domaine, sinon celle dérivée des paramètres globaux."""
    policy = session.get(AlertPolicy, domain)
    if policy is not None:
        return policy
    defaults = defaults or get_settings(session, GLOBAL_SCOPE)
    return AlertPolicy(
        domain_name=domain, threshold_days=defaults.threshold_days, reminder_interval_hours=168,
        enabled=defaults.enabled, channel=defaults.channel,
    )


def select_alert_events(session: Session, results: Iterable[dict], now: datetime | None = None) -> list[AlertEvent]:
    now = now or datetime.utcnow()
    occurred_at = now.isoformat(timespec="seconds")
    settings = get_settings(session, GLOBAL_SCOPE)
    if not settings.enabled:
        return []
    events = []
    for certificate in results:
        domain = certificate["domain"]
        policy = get_policy(session, domain, settings)
        rule = resolve_alert_rule(session, domain, certificate)
        threshold_days = rule.threshold_days if rule else policy.threshold_days
        reminder_interval_hours = rule.reminder_interval_hours if rule else policy.reminder_interval_hours
        channel = json.loads(rule.channels or "[\"email\"]")[0] if rule else policy.channel
        rule_name = rule.name if rule else "default"
        explanation = f"Règle '{rule_name}' (priorité {rule.priority})" if rule else "Politique par défaut"
        state = session.get(AlertState, domain)
        current_state = state.state if state else "healthy"
        is_critical = certificate["status"] == "Erreur" or (
            certificate.get("days_left") is not None and certificate["days_left"] < threshold_days
        )
        if not policy.enabled:
            continue
        if is_critical and current_state == "healthy":
            events.append(AlertEvent(domain, "problem", channel, certificate, rule.id if rule else None, rule_name, explanation, occurred_at))
        elif is_critical and current_state == "critical" and state and state.last_notified_at:
            if now >= state.last_notified_at + timedelta(hours=reminder_interval_hours):
                events.append(AlertEvent(domain, "reminder", channel, certificate, rule.id if rule else None, rule_name, explanation, occurred_at))
        elif not is_critical and current_state == "critical":
            events.append(AlertEvent(domain, "resolved", channel, certificate, rule.id if rule else None, rule_name, explanation, occurred_at))
    return events


def record_notification(session: Session, events: Iterable[AlertEvent], success: bool, error_message: str | None = None, now: datetime | None = None, delivery_status: str = "delivered", attempts: int = 1, idempotency_key: str | None = None) -> None:
    now = now or datetime.utcnow()
    for event in events:
        log = session.query(NotificationLog).filter_by(idempotency_key=idempotency_key).first() if idempotency_key else None
        if log is None:
            log = NotificationLog(domain_name=event.domain, event_type=event.event_type, channel=event.channel, idempotency_key=idempotency_key)
            session.add(log)
        log.success = success
        log.error_message = error_message
        log.created_at = now
        log.delivery_status = delivery_status
        log.attempts = attempts
        if success:
            state = session.get(AlertState, event.domain)
            if state is None:
                state = AlertState(domain_name=event.domain)
                session.add(state)
            state.state = "healthy" if event.event_type == "resolved" else "critical"
            state.last_notified_at = now
    session.commit()
