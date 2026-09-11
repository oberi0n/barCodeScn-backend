import re

import pytest
from fastapi.testclient import TestClient

from app.main import app


@pytest.fixture
def client(tmp_path, monkeypatch):
    monkeypatch.setenv("SCANS_LOG_PATH", str(tmp_path / "scans.log"))
    with TestClient(app) as test_client:
        yield test_client, tmp_path / "scans.log"


def valid_scan(**overrides):
    payload = {
        "barcode": "3400930001234",
        "latitude": 49.123456,
        "longitude": 6.123456,
        "accuracy": 12.5,
    }
    payload.update(overrides)
    return payload


def test_healthz(client):
    response = client[0].get("/healthz")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_valid_scan_returns_created(client):
    response = client[0].post("/scan", json=valid_scan())
    assert response.status_code == 201
    assert response.json()["status"] == "ok"
    assert response.json()["barcode"] == "3400930001234"
    assert re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{3}Z", response.json()["received_at"])


@pytest.mark.parametrize("barcode", ["", "   "])
def test_empty_barcode_is_rejected(client, barcode):
    assert client[0].post("/scan", json=valid_scan(barcode=barcode)).status_code == 422


@pytest.mark.parametrize("latitude", [-90.1, 90.1])
def test_invalid_latitude_is_rejected(client, latitude):
    assert client[0].post("/scan", json=valid_scan(latitude=latitude)).status_code == 422


@pytest.mark.parametrize("longitude", [-180.1, 180.1])
def test_invalid_longitude_is_rejected(client, longitude):
    assert client[0].post("/scan", json=valid_scan(longitude=longitude)).status_code == 422


def test_scans_are_created_and_appended(client):
    api, log_path = client
    assert api.post("/scan", json=valid_scan()).status_code == 201
    assert api.post("/scan", json=valid_scan(barcode="9876543210", accuracy=None)).status_code == 201

    lines = log_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 2
    assert "barcode=3400930001234 | lat=49.123456 | lon=6.123456 | accuracy=12.5m" in lines[0]
    assert "barcode=9876543210 | lat=49.123456 | lon=6.123456" in lines[1]
    assert "accuracy=" not in lines[1]
