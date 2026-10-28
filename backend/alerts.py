"""Alert policies, state transitions and notification journal."""

from dataclasses import dataclass
from datetime import datetime, timedelta
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


@dataclass(frozen=True)
class AlertEvent:
    domain: str
    event_type: str
    channel: str
    certificate: dict
    # Moment où l'événement a été émis : distingue deux rappels du même certificat.
    occurred_at: str | None = None


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
        state = session.get(AlertState, domain)
        current_state = state.state if state else "healthy"
        is_critical = certificate["status"] == "Erreur" or (
            certificate.get("days_left") is not None and certificate["days_left"] < policy.threshold_days
        )
        if not policy.enabled:
            continue
        if is_critical and current_state == "healthy":
            events.append(AlertEvent(domain, "problem", policy.channel, certificate, occurred_at))
        elif is_critical and current_state == "critical" and state and state.last_notified_at:
            if now >= state.last_notified_at + timedelta(hours=policy.reminder_interval_hours):
                events.append(AlertEvent(domain, "reminder", policy.channel, certificate, occurred_at))
        elif not is_critical and current_state == "critical":
            events.append(AlertEvent(domain, "resolved", policy.channel, certificate, occurred_at))
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
