import importlib
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

BACKEND_DIR = Path(__file__).resolve().parents[1]


@pytest.fixture()
def client(tmp_path, monkeypatch):
    # main.py importe ses modules sans préfixe de paquet, comme dans l'image Docker.
    monkeypatch.syspath_prepend(str(BACKEND_DIR))
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{tmp_path / 'api.db'}")
    monkeypatch.setenv("CORS_ORIGINS", "https://app.example.com")
    monkeypatch.delenv("BACKEND_API_TOKEN", raising=False)
    for name in ("main", "database", "alerts", "settings", "notifications", "cron_job", "domain_utils"):
        sys.modules.pop(name, None)
    return TestClient(importlib.import_module("main").app)


@pytest.mark.parametrize("path", ["/api/settings/organization", "/api/domains/example.com/alert-policy"])
def test_cors_preflight_allows_put(client, path):
    response = client.options(path, headers={
        "Origin": "https://app.example.com",
        "Access-Control-Request-Method": "PUT",
        "Access-Control-Request-Headers": "Content-Type",
    })

    assert response.status_code == 200
    assert "PUT" in response.headers["access-control-allow-methods"]


def test_settings_update_over_cors(client):
    response = client.put(
        "/api/settings/organization",
        json={"threshold_days": 14, "check_interval_minutes": 30, "channel": "email", "recipients": [], "enabled": True},
        headers={"Origin": "https://app.example.com"},
    )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "https://app.example.com"
    assert response.json()["check_interval_minutes"] == 30


def test_bulk_add_reports_added_duplicates_and_invalid_entries(client):
    response = client.post("/api/domains/bulk", json={"domains": ["Example.COM.", "example.com", "not a domain"]})

    assert response.status_code == 200
    body = response.json()
    assert body["added"] == ["example.com"]
    assert body["duplicates"] == ["example.com"]
    assert [item["value"] for item in body["invalid"]] == ["not a domain"]
