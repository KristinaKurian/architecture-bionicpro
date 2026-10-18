"""Security and freshness contract tests, without external services."""
from datetime import date, timedelta, datetime, timezone

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.auth import get_principal
import app.main as main

YESTERDAY = datetime.now(timezone.utc).date() - timedelta(days=1)

class StubConn:
    def close(self):
        pass

@pytest.fixture
def client(monkeypatch):
    app.dependency_overrides[get_principal] = lambda: {
        'iss': 'http://localhost:8080/realms/reports-realm', 'sub': 'demo-sub'
    }
    monkeypatch.setattr(main, 'get_crm_conn', lambda: StubConn())
    monkeypatch.setattr(main, 'get_clickhouse', lambda: StubConn())
    monkeypatch.setattr(main, 'resolve_patient_and_prostheses', lambda *args: (1, {'p-100'}))
    monkeypatch.setattr(main, 'get_processed_days', lambda *_: {YESTERDAY})
    monkeypatch.setattr(main, 'get_report_rows', lambda *_: [
        (YESTERDAY, 'p-100', 3, 80.0, 50.0, 90.0),
        (YESTERDAY, 'p-200', 3, 99.0, 50.0, 90.0),  # foreign: never returned
    ])
    with TestClient(app) as api:
        yield api
    app.dependency_overrides.clear()


def url():
    return f'/reports?from_date={YESTERDAY}&to_date={YESTERDAY}'


def test_unauthenticated_denied():
    with TestClient(app) as api:
        result = api.get(url())
    assert result.status_code == 401


def test_only_own_prosthesis_is_returned(client):
    result = client.get(url())
    assert result.status_code == 200
    assert result.headers['content-type'].startswith('text/csv')
    assert 'p-100' in result.text
    assert 'p-200' not in result.text
    assert result.headers['cache-control'] == 'private, no-store'


def test_explicitly_requested_foreign_prosthesis_denied(client):
    result = client.get(url() + '&prosthesis_id=p-200')
    assert result.status_code == 403


def test_future_data_or_unprocessed_period_not_reported(client, monkeypatch):
    monkeypatch.setattr(main, 'get_processed_days', lambda *_: set())
    assert client.get(url()).status_code == 409
    tomorrow = datetime.now(timezone.utc).date() + timedelta(days=1)
    assert client.get(f'/reports?from_date={tomorrow}&to_date={tomorrow}').status_code == 422


def test_no_patient_mapping_denied(client, monkeypatch):
    monkeypatch.setattr(main, 'resolve_patient_and_prostheses', lambda *args: (None, set()))
    assert client.get(url()).status_code == 403
