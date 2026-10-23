"""Canonicalisation and validation of monitored domain names."""

import re


DOMAIN_LABEL = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$")


def normalize_domain(value: str) -> str | None:
    """Return the canonical ASCII form of a domain, or None when invalid."""
    if not isinstance(value, str):
        return None
    candidate = value.strip().rstrip(".").lower()
    if not candidate or len(candidate) > 253 or "/" in candidate or ":" in candidate:
        return None
    try:
        ascii_domain = candidate.encode("idna").decode("ascii")
    except UnicodeError:
        return None
    labels = ascii_domain.split(".")
    if len(labels) < 2 or len(labels[-1]) < 2 or any(not DOMAIN_LABEL.fullmatch(label) for label in labels):
        return None
    return ascii_domain
