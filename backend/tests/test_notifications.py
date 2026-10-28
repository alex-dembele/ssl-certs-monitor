from backend.alerts import AlertEvent
from backend.notifications import deliver_events, idempotency_key, sign_webhook_payload, verify_webhook_signature


def test_webhook_signature_requires_recent_timestamp():
    payload = b'{"event":"problem"}'
    signature = sign_webhook_payload(payload, "1000", "secret")

    assert verify_webhook_signature(payload, "1000", signature, "secret", now=1100)
    assert not verify_webhook_signature(payload, "1000", signature, "secret", now=1401)
    assert not verify_webhook_signature(payload, "1000", "sha256=invalid", "secret", now=1100)


def test_delivery_retries_and_records_dead_letter(monkeypatch):
    event = AlertEvent("example.com", "problem", "unknown", {"status": "Erreur"})
    result = deliver_events([event], max_attempts=2)[0]

    assert result.success is False
    assert result.status == "dead_letter"
    assert result.attempts == 0
    assert len(idempotency_key(event)) == 64
