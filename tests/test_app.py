import pytest

from app import create_app
from config import Config
from services.confiforms import DataSource, DataSourceError


class FakeDataSource(DataSource):
    def __init__(self, rows=None, error=None):
        self.rows = rows or []
        self.error = error
        self.calls = 0

    def fetch(self):
        self.calls += 1
        if self.error:
            raise self.error
        return self.rows


SAMPLE_ROWS = [
    {"Title": "Server migration", "Status": "Open", "Owner": "Alice", "Progress": "40%", "DueDate": "2026-08-10"},
    {"Title": "Patch rollout", "Status": "Blocked", "Owner": "Bob", "Progress": 90, "DueDate": "2026-07-01"},
]


@pytest.fixture
def test_config():
    return Config(status_colors={"Open": "#28a745", "Blocked": "#dc3545"}, refresh_interval=60)


def test_index_renders_dashboard_shell(test_config):
    app = create_app(app_config=test_config, data_source=FakeDataSource(SAMPLE_ROWS))
    client = app.test_client()

    response = client.get("/")

    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "ConfiForms Dashboard" in body
    assert 'id="cf-table"' in body
    assert "data-refresh-interval=\"60\"" in body


def test_api_data_returns_normalized_payload(test_config):
    app = create_app(app_config=test_config, data_source=FakeDataSource(SAMPLE_ROWS))
    client = app.test_client()

    response = client.get("/api/data")
    payload = response.get_json()

    assert response.status_code == 200
    assert len(payload["rows"]) == 2
    assert payload["rows"][0]["Progress"] == 40.0
    assert payload["status_colors"]["Open"] == "#28a745"
    field_names = {c["field"] for c in payload["columns"]}
    assert {"Title", "Status", "Owner", "Progress", "DueDate"} <= field_names


def test_api_data_caches_between_requests(test_config):
    source = FakeDataSource(SAMPLE_ROWS)
    app = create_app(app_config=test_config, data_source=source)
    client = app.test_client()

    client.get("/api/data")
    client.get("/api/data")

    assert source.calls == 1


def test_api_data_returns_502_on_data_source_error(test_config):
    app = create_app(app_config=test_config, data_source=FakeDataSource(error=DataSourceError("boom")))
    client = app.test_client()

    response = client.get("/api/data")

    assert response.status_code == 502
    assert "boom" in response.get_json()["error"]


def test_health_endpoint(test_config):
    app = create_app(app_config=test_config, data_source=FakeDataSource(SAMPLE_ROWS))
    client = app.test_client()

    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}
