import sys
sys.path.insert(0, r"C:\Confluence Table\dashboard")

from app import create_app
from config import Config
from services.confiforms import DataSource
from waitress import serve

SAMPLE_ROWS = [
    {"Operation": "Password reset", "Case ID": "CASE-1001", "Target": "svc-account-01", "Status": "Open", "Awaited From": "2026-07-30"},
    {"Operation": "Access request", "Case ID": "CASE-1002", "Target": "jsmith", "Status": "Blocked", "Awaited From": "2026-07-20"},
    {"Operation": "Firewall change", "Case ID": "CASE-1003", "Target": "10.20.30.0/24", "Status": "Closed", "Awaited From": "2026-06-15"},
    {"Operation": "License renewal", "Case ID": "CASE-1004", "Target": "confluence-dc", "Status": "Pending", "Awaited From": "2026-08-01"},
]


class MockSource(DataSource):
    def fetch(self):
        return SAMPLE_ROWS


test_config = Config(
    status_colors={"Open": "#28a745", "Pending": "#ffc107", "Blocked": "#dc3545", "Closed": "#6c757d"},
    refresh_interval=60,
)

app = create_app(app_config=test_config, data_source=MockSource())

if __name__ == "__main__":
    serve(app, host="127.0.0.1", port=5099)
