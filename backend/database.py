"""Database access and the one-time migration from the legacy JSON store."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, create_engine, inspect, select, text
from sqlalchemy.orm import DeclarativeBase, Session, relationship, sessionmaker


class Base(DeclarativeBase):
    pass


class Domain(Base):
    __tablename__ = "domains"

    name = Column(String(253), primary_key=True)
    status = relationship(
        "CertificateStatus",
        back_populates="domain", cascade="all, delete-orphan", uselist=False
    )


class CertificateStatus(Base):
    __tablename__ = "certificate_statuses"

    domain_name = Column(
        String(253), ForeignKey("domains.name", ondelete="CASCADE"), primary_key=True
    )
    status = Column(String(32), nullable=False)
    days_left = Column(Integer, nullable=True)
    expiry_date = Column(String(64), nullable=True)
    valid_from = Column(String(64), nullable=True)
    valid_until = Column(String(64), nullable=True)
    issuer = Column(Text, nullable=True)
    subject = Column(Text, nullable=True)
    serial_number = Column(String(128), nullable=True)
    fingerprint = Column(String(128), nullable=True)
    san = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    error_type = Column(String(64), nullable=True)
    checked_at = Column(DateTime, nullable=False, default=lambda: datetime.now(timezone.utc).replace(tzinfo=None))
    domain = relationship("Domain", back_populates="status")


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./ssl_monitor.db")
LEGACY_DOMAINS_FILE = os.getenv("LEGACY_DOMAINS_FILE", "")
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def initialize_database() -> None:
    Base.metadata.create_all(engine)
    _upgrade_status_schema()
    if not LEGACY_DOMAINS_FILE:
        return

    legacy_path = Path(LEGACY_DOMAINS_FILE)
    if not legacy_path.exists():
        return
    try:
        legacy_domains = json.loads(legacy_path.read_text())
    except (OSError, json.JSONDecodeError):
        return
    if not isinstance(legacy_domains, list):
        return

    with SessionLocal.begin() as session:
        for domain in legacy_domains:
            if isinstance(domain, str) and domain.strip():
                session.execute(
                    text("INSERT INTO domains (name) VALUES (:name) ON CONFLICT (name) DO NOTHING"),
                    {"name": domain.strip()},
                )


def _upgrade_status_schema() -> None:
    """Add fields introduced after the initial JSON-to-database migration."""
    columns = {
        "valid_from": "VARCHAR(64)",
        "valid_until": "VARCHAR(64)",
        "issuer": "TEXT",
        "subject": "TEXT",
        "serial_number": "VARCHAR(128)",
        "fingerprint": "VARCHAR(128)",
        "san": "TEXT",
        "error_type": "VARCHAR(64)",
    }
    existing = {column["name"] for column in inspect(engine).get_columns("certificate_statuses")}
    missing = columns.keys() - existing
    if not missing:
        return
    with engine.begin() as connection:
        for name in missing:
            connection.execute(text(f"ALTER TABLE certificate_statuses ADD COLUMN {name} {columns[name]}"))


def list_domains(session: Session) -> list[str]:
    return list(session.scalars(select(Domain.name).order_by(Domain.name)))


def add_domains(session: Session, domains: Iterable[str]) -> int:
    added = 0
    for domain in domains:
        result = session.execute(
            text("INSERT INTO domains (name) VALUES (:name) ON CONFLICT (name) DO NOTHING"),
            {"name": domain},
        )
        added += result.rowcount
    session.commit()
    return added


def delete_domain(session: Session, domain: str) -> bool:
    result = session.execute(text("DELETE FROM domains WHERE name = :name"), {"name": domain})
    session.commit()
    return result.rowcount == 1


def list_statuses(session: Session) -> list[dict]:
    statuses = session.scalars(select(CertificateStatus).order_by(CertificateStatus.domain_name))
    return [
        {
            "domain": status.domain_name,
            "status": status.status,
            "days_left": status.days_left,
            "expiry_date": status.expiry_date,
            "valid_from": status.valid_from,
            "valid_until": status.valid_until,
            "issuer": status.issuer,
            "subject": status.subject,
            "serial_number": status.serial_number,
            "fingerprint": status.fingerprint,
            "san": json.loads(status.san) if status.san else [],
            "error_message": status.error_message,
            "error_type": status.error_type,
            "checked_at": status.checked_at.isoformat() if status.checked_at else None,
        }
        for status in statuses
    ]


def save_statuses(session: Session, statuses: Iterable[dict]) -> None:
    for certificate in statuses:
        session.execute(
            text(
                """INSERT INTO certificate_statuses
                (domain_name, status, days_left, expiry_date, valid_from, valid_until,
                 issuer, subject, serial_number, fingerprint, san, error_message, error_type, checked_at)
                SELECT name, :status, :days_left, :expiry_date, :valid_from, :valid_until,
                 :issuer, :subject, :serial_number, :fingerprint, :san, :error_message, :error_type, :checked_at
                FROM domains WHERE name = :domain_name
                ON CONFLICT (domain_name) DO UPDATE SET
                    status = excluded.status,
                    days_left = excluded.days_left,
                    expiry_date = excluded.expiry_date,
                    valid_from = excluded.valid_from,
                    valid_until = excluded.valid_until,
                    issuer = excluded.issuer,
                    subject = excluded.subject,
                    serial_number = excluded.serial_number,
                    fingerprint = excluded.fingerprint,
                    san = excluded.san,
                    error_message = excluded.error_message,
                    error_type = excluded.error_type,
                    checked_at = excluded.checked_at"""
            ),
            {
                "domain_name": certificate["domain"],
                "status": certificate["status"],
                "days_left": certificate.get("days_left"),
                "expiry_date": certificate.get("expiry_date"),
                "valid_from": certificate.get("valid_from"),
                "valid_until": certificate.get("valid_until"),
                "issuer": certificate.get("issuer"),
                "subject": certificate.get("subject"),
                "serial_number": certificate.get("serial_number"),
                "fingerprint": certificate.get("fingerprint"),
                "san": json.dumps(certificate.get("san", [])),
                "error_message": certificate.get("error_message"),
                "error_type": certificate.get("error_type"),
                "checked_at": _checked_at(certificate.get("checked_at")),
            },
        )
    session.commit()


def _checked_at(value: str | None) -> datetime:
    if value:
        try:
            return datetime.fromisoformat(value).replace(tzinfo=None)
        except ValueError:
            pass
    return datetime.now(timezone.utc).replace(tzinfo=None)
