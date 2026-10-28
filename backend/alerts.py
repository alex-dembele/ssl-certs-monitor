"""Alert policies, state transitions and notification journal."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Iterable

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Session

try:
    from .database import Base
except ImportError:
    from database import Base


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
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)


@dataclass(frozen=True)
class AlertEvent:
    domain: str
    event_type: str
    channel: str
    certificate: dict


def get_policy(session: Session, domain: str) -> AlertPolicy:
    return session.get(AlertPolicy, domain) or AlertPolicy(
        domain_name=domain, threshold_days=30, reminder_interval_hours=168, enabled=True, channel="email"
    )


def select_alert_events(session: Session, results: Iterable[dict], now: datetime | None = None) -> list[AlertEvent]:
    now = now or datetime.utcnow()
    events = []
    for certificate in results:
        domain = certificate["domain"]
        policy = get_policy(session, domain)
        state = session.get(AlertState, domain)
        current_state = state.state if state else "healthy"
        is_critical = certificate["status"] == "Erreur" or (
            certificate.get("days_left") is not None and certificate["days_left"] < policy.threshold_days
        )
        if not policy.enabled:
            continue
        if is_critical and current_state == "healthy":
            events.append(AlertEvent(domain, "problem", policy.channel, certificate))
        elif is_critical and current_state == "critical" and state and state.last_notified_at:
            if now >= state.last_notified_at + timedelta(hours=policy.reminder_interval_hours):
                events.append(AlertEvent(domain, "reminder", policy.channel, certificate))
        elif not is_critical and current_state == "critical":
            events.append(AlertEvent(domain, "resolved", policy.channel, certificate))
    return events


def record_notification(session: Session, events: Iterable[AlertEvent], success: bool, error_message: str | None = None, now: datetime | None = None) -> None:
    now = now or datetime.utcnow()
    for event in events:
        session.add(NotificationLog(
            domain_name=event.domain, event_type=event.event_type, channel=event.channel,
            success=success, error_message=error_message, created_at=now,
        ))
        if success:
            state = session.get(AlertState, event.domain)
            if state is None:
                state = AlertState(domain_name=event.domain)
                session.add(state)
            state.state = "healthy" if event.event_type == "resolved" else "critical"
            state.last_notified_at = now
    session.commit()
