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


def _check_against_local_server(monkeypatch, handler):
    monkeypatch.setattr(cron_job, "MAX_RETRIES", 0)

    async def scenario():
        server = await asyncio.start_server(handler, "127.0.0.1", 0)
        monkeypatch.setattr(cron_job, "TLS_PORT", server.sockets[0].getsockname()[1])
        async with server:
            return await cron_job.get_ssl_expiry_info("127.0.0.1")

    return asyncio.run(scenario())


def test_tls_negotiation_failure_returns_structured_error(monkeypatch):
    async def plain_http(reader, writer):
        writer.write(b"HTTP/1.1 400 Bad Request\r\n\r\n")
        await writer.drain()
        writer.close()

    result = _check_against_local_server(monkeypatch, plain_http)

    assert result["status"] == "Erreur"
    assert result["error_type"] in {"certificat_invalide", "erreur_tls"}
    assert result["checked_at"]


def test_tls_handshake_timeout_is_classified(monkeypatch):
    monkeypatch.setattr(cron_job, "TLS_TIMEOUT", 0.2)

    async def silent(reader, writer):
        await asyncio.sleep(1)
        writer.close()

    result = _check_against_local_server(monkeypatch, silent)

    assert result["error_type"] == "timeout_tls"


def test_unexpected_error_does_not_abort_the_batch(monkeypatch):
    async def broken_check(_hostname):
        raise AttributeError("'StreamWriter' object has no attribute 'start_tls'")

    monkeypatch.setattr(cron_job, "_check_once", broken_check)

    result = asyncio.run(cron_job.get_ssl_expiry_info("example.com"))

    assert result["status"] == "Erreur"
    assert result["error_type"] == "erreur_inattendue"
