import asyncio

import pytest

import backend.cron_job as cron_job


def test_invalid_hostname_is_reported_without_network_call():
    result = asyncio.run(cron_job.get_ssl_expiry_info("not a hostname"))

    assert result["status"] == "Erreur"
    assert result["error_type"] == "hostname_invalide"
    assert result["checked_at"]


def test_transient_errors_are_retried(monkeypatch):
    attempts = 0

    async def flaky_check(_hostname):
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise cron_job.SSLCheckError("timeout_connexion", "temporary", True)
        return {"domain": "example.com", "status": "OK", "checked_at": "now"}

    monkeypatch.setattr(cron_job, "_check_once", flaky_check)
    monkeypatch.setattr(cron_job, "RETRY_BACKOFF", 0)

    result = asyncio.run(cron_job.get_ssl_expiry_info("example.com"))

    assert result["status"] == "OK"
    assert attempts == 3


@pytest.mark.parametrize("error_type", ["timeout_dns", "timeout_connexion", "timeout_tls"])
def test_retryable_error_is_exposed_after_retries(monkeypatch, error_type):
    async def failing_check(_hostname):
        raise cron_job.SSLCheckError(error_type, "temporary", True)

    monkeypatch.setattr(cron_job, "_check_once", failing_check)
    monkeypatch.setattr(cron_job, "RETRY_BACKOFF", 0)
    monkeypatch.setattr(cron_job, "MAX_RETRIES", 1)

    result = asyncio.run(cron_job.get_ssl_expiry_info("example.com"))

    assert result["status"] == "Erreur"
    assert result["error_type"] == error_type
    assert result["checked_at"]
