"""Provider-independent notification channels and delivery safeguards."""

from dataclasses import dataclass
import hashlib
import hmac
import json
import os
import time
from email.message import EmailMessage
from typing import Protocol
from urllib.error import URLError
from urllib.request import Request, urlopen
import smtplib

try:
    from .alerts import AlertEvent
except ImportError:
    from alerts import AlertEvent


@dataclass(frozen=True)
class DeliveryResult:
    event: AlertEvent
    success: bool
    status: str
    attempts: int
    idempotency_key: str
    error_message: str | None = None


class NotificationChannel(Protocol):
    name: str

    def send(self, events: list[AlertEvent], idempotency_key: str) -> None: ...


def idempotency_key(event: AlertEvent) -> str:
    certificate = event.certificate
    stable = {
        "domain": event.domain,
        "event": event.event_type,
        "status": certificate.get("status"),
        "expiry": certificate.get("expiry_date"),
        "fingerprint": certificate.get("fingerprint"),
        "occurred_at": event.occurred_at,
    }
    return hashlib.sha256(json.dumps(stable, sort_keys=True).encode()).hexdigest()


def _render(events: list[AlertEvent]) -> str:
    lines = ["SSL-Cert-Monitor notification", ""]
    for event in events:
        lines.extend([
            f"Domain: {event.domain}",
            f"Event: {event.event_type}",
            f"Status: {event.certificate.get('status')}",
            f"Rule: {getattr(event, 'explanation', 'default')}",
            f"Days left: {event.certificate.get('days_left', 'n/a')}",
            "",
        ])
    return "\n".join(lines)


class EmailChannel:
    name = "email"

    def __init__(self, recipients: list[str] | None = None):
        self.recipients = recipients

    def send(self, events: list[AlertEvent], idempotency_key: str) -> None:
        sender = os.getenv("SMTP_SENDER_EMAIL")
        password = os.getenv("SMTP_PASSWORD")
        recipients = self.recipients or [item.strip() for item in os.getenv("ALERT_RECIPIENTS", "").split(",") if item.strip()]
        server_name = os.getenv("SMTP_SERVER")
        if not all([sender, password, recipients, server_name]):
            raise RuntimeError("Configuration SMTP incomplète.")
        message = EmailMessage()
        message["Subject"] = f"SSL-Cert-Monitor : {len(events)} notification(s)"
        message["From"] = sender
        message["To"] = ", ".join(recipients)
        message["X-Idempotency-Key"] = idempotency_key
        message.set_content(_render(events))
        with smtplib.SMTP(server_name, int(os.getenv("SMTP_PORT", "587"))) as server:
            server.starttls()
            server.login(sender, password)
            server.send_message(message)


class WebhookChannel:
    name = "webhook"

    def __init__(self, url_env: str, secret_env: str):
        self.url_env = url_env
        self.secret_env = secret_env

    def send(self, events: list[AlertEvent], idempotency_key: str) -> None:
        url = os.getenv(self.url_env)
        secret = os.getenv(self.secret_env)
        if not url or not secret:
            raise RuntimeError(f"Configuration absente pour {self.name}.")
        timestamp = str(int(time.time()))
        body = json.dumps({"idempotency_key": idempotency_key, "events": [event.__dict__ for event in events]}, default=str).encode()
        signature = sign_webhook_payload(body, timestamp, secret)
        request = Request(url, data=body, headers={
            "Content-Type": "application/json",
            "X-SSL-Monitor-Timestamp": timestamp,
            "X-SSL-Monitor-Signature": signature,
            "X-Idempotency-Key": idempotency_key,
        }, method="POST")
        try:
            with urlopen(request, timeout=float(os.getenv("ALERT_WEBHOOK_TIMEOUT", "10"))) as response:
                if response.status >= 300:
                    raise RuntimeError(f"Webhook HTTP {response.status}")
        except URLError as error:
            raise RuntimeError(str(error)) from error


class SlackChannel(WebhookChannel):
    name = "slack"


class TeamsChannel(WebhookChannel):
    name = "teams"


class DiscordChannel(WebhookChannel):
    name = "discord"


def sign_webhook_payload(payload: bytes, timestamp: str, secret: str) -> str:
    return "sha256=" + hmac.new(secret.encode(), timestamp.encode() + b"." + payload, hashlib.sha256).hexdigest()


def verify_webhook_signature(payload: bytes, timestamp: str, signature: str, secret: str, max_age: int = 300, now: int | None = None) -> bool:
    try:
        if abs((now or int(time.time())) - int(timestamp)) > max_age:
            return False
    except ValueError:
        return False
    expected = sign_webhook_payload(payload, timestamp, secret)
    return hmac.compare_digest(expected, signature)


def deliver_events(events: list[AlertEvent], max_attempts: int = 3, email_recipients: list[str] | None = None) -> list[DeliveryResult]:
    channels: dict[str, NotificationChannel] = {
        "email": EmailChannel(email_recipients),
        "webhook": WebhookChannel("ALERT_WEBHOOK_URL", "ALERT_WEBHOOK_SECRET"),
        "slack": SlackChannel("SLACK_WEBHOOK_URL", "SLACK_WEBHOOK_SECRET"),
        "teams": TeamsChannel("TEAMS_WEBHOOK_URL", "TEAMS_WEBHOOK_SECRET"),
        "discord": DiscordChannel("DISCORD_WEBHOOK_URL", "DISCORD_WEBHOOK_SECRET"),
    }
    results = []
    backoff = float(os.getenv("ALERT_RETRY_BACKOFF", "0.5"))
    for event in events:
        key = idempotency_key(event)
        channel = channels.get(event.channel)
        if channel is None:
            results.append(DeliveryResult(event, False, "dead_letter", 0, key, f"Canal inconnu: {event.channel}"))
            continue
        error = None
        for attempt in range(1, max_attempts + 1):
            try:
                channel.send([event], key)
                results.append(DeliveryResult(event, True, "delivered", attempt, key))
                break
            except Exception as exc:
                error = str(exc)
                if attempt < max_attempts:
                    time.sleep(backoff * (2 ** (attempt - 1)))
        else:
            results.append(DeliveryResult(event, False, "dead_letter", max_attempts, key, error))
    return results
