"""Environment-driven application configuration.

Values are read from environment variables (optionally loaded from a
.env file via python-dotenv) so that no credentials live in source code.
"""
from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent / ".env")

DEFAULT_STATUS_COLORS = {
    "Open": "#28a745",
    "Pending": "#ffc107",
    "Blocked": "#dc3545",
    "Closed": "#6c757d",
}


def _get_bool(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in ("1", "true", "yes", "on")


def _get_int(name: str, default: int) -> int:
    value = os.environ.get(name)
    if value is None or value == "":
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _get_status_colors() -> dict:
    raw = os.environ.get("STATUS_COLORS")
    if not raw:
        return dict(DEFAULT_STATUS_COLORS)
    try:
        parsed = json.loads(raw)
        if isinstance(parsed, dict):
            return {**DEFAULT_STATUS_COLORS, **parsed}
    except json.JSONDecodeError:
        pass
    return dict(DEFAULT_STATUS_COLORS)


@dataclass(frozen=True)
class Config:
    # Data source selection: "rest" (default), "json", or "csv"
    data_source_type: str = field(
        default_factory=lambda: os.environ.get("DATA_SOURCE_TYPE", "rest").strip().lower()
    )

    # Confluence connection (used by the REST data source)
    confluence_url: str = field(default_factory=lambda: os.environ.get("CONFLUENCE_URL", ""))
    confluence_username: str = field(
        default_factory=lambda: os.environ.get("CONFLUENCE_USERNAME", "")
    )
    confluence_api_token: str = field(
        default_factory=lambda: os.environ.get("CONFLUENCE_API_TOKEN", "")
    )

    # ConfiForms form/space identifiers used to build REST/JSON/CSV endpoints
    confiform_endpoint: str = field(
        default_factory=lambda: os.environ.get("CONFIFORM_ENDPOINT", "")
    )

    # Caching / refresh
    refresh_interval: int = field(default_factory=lambda: _get_int("REFRESH_INTERVAL", 60))

    # Server
    port: int = field(default_factory=lambda: _get_int("PORT", 5000))
    debug: bool = field(default_factory=lambda: _get_bool("FLASK_DEBUG", False))

    # Presentation
    status_colors: dict = field(default_factory=_get_status_colors)

    # Networking
    request_timeout: int = field(default_factory=lambda: _get_int("REQUEST_TIMEOUT", 15))
    verify_ssl: bool = field(default_factory=lambda: _get_bool("VERIFY_SSL", True))


config = Config()
