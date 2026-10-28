"""Persistent notification preferences for personal and organization scopes."""

from datetime import datetime, timezone
import json

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.orm import Session

try:
    from .database import Base
except ImportError:
    from database import Base


class NotificationSettings(Base):
    __tablename__ = "notification_settings"

    scope = Column(String(20), primary_key=True)
    threshold_days = Column(Integer, nullable=False, default=30)
    check_interval_minutes = Column(Integer, nullable=False, default=60)
    channel = Column(String(32), nullable=False, default="email")
    recipients = Column(Text, nullable=False, default="[]")
    enabled = Column(Boolean, nullable=False, default=True)
    updated_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))


class SettingsAuditLog(Base):
    __tablename__ = "settings_audit_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    scope = Column(String(20), nullable=False)
    changed_fields = Column(Text, nullable=False)
    changed_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))


DEFAULTS = {"threshold_days": 30, "check_interval_minutes": 60, "channel": "email", "recipients": [], "enabled": True}


def get_settings(session: Session, scope: str) -> NotificationSettings:
    return session.get(NotificationSettings, scope) or NotificationSettings(
        scope=scope, threshold_days=30, check_interval_minutes=60,
        channel="email", recipients="[]", enabled=True,
    )


def settings_to_dict(settings: NotificationSettings) -> dict:
    return {
        "scope": settings.scope,
        "threshold_days": settings.threshold_days,
        "check_interval_minutes": settings.check_interval_minutes,
        "channel": settings.channel,
        "recipients": json.loads(settings.recipients or "[]"),
        "enabled": settings.enabled,
        "updated_at": settings.updated_at.isoformat() if settings.updated_at else None,
    }
