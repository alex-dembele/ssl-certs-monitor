"""Database access and the one-time migration from the legacy JSON store."""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Iterable

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text, create_engine, select, text
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
    error_message = Column(Text, nullable=True)
    checked_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    domain = relationship("Domain", back_populates="status")


DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./ssl_monitor.db")
LEGACY_DOMAINS_FILE = os.getenv("LEGACY_DOMAINS_FILE", "")
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def initialize_database() -> None:
    Base.metadata.create_all(engine)
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
            "error_message": status.error_message,
        }
        for status in statuses
    ]


def save_statuses(session: Session, statuses: Iterable[dict]) -> None:
    for certificate in statuses:
        session.execute(
            text(
                """INSERT INTO certificate_statuses
                (domain_name, status, days_left, expiry_date, error_message, checked_at)
                SELECT name, :status, :days_left, :expiry_date, :error_message, :checked_at
                FROM domains WHERE name = :domain_name
                ON CONFLICT (domain_name) DO UPDATE SET
                    status = excluded.status,
                    days_left = excluded.days_left,
                    expiry_date = excluded.expiry_date,
                    error_message = excluded.error_message,
                    checked_at = excluded.checked_at"""
            ),
            {
                "domain_name": certificate["domain"],
                "status": certificate["status"],
                "days_left": certificate.get("days_left"),
                "expiry_date": certificate.get("expiry_date"),
                "error_message": certificate.get("error_message"),
                "checked_at": datetime.utcnow(),
            },
        )
    session.commit()
