"""Pluggable ConfiForms data sources.

The dashboard never talks to Confluence directly outside this module, so the
retrieval mechanism (REST API, JSON export view, or CSV export) can change
without touching the rest of the app. Select the active source with the
DATA_SOURCE_TYPE environment variable ("rest", "json", or "csv").
"""
from __future__ import annotations

import csv
import io
from abc import ABC, abstractmethod
from typing import Any

import requests

from config import Config


class DataSourceError(RuntimeError):
    """Raised when ConfiForms data cannot be retrieved or parsed."""


class DataSource(ABC):
    """Abstract source of raw ConfiForms entries."""

    @abstractmethod
    def fetch(self) -> list[dict[str, Any]]:
        """Return a list of raw entry dicts, unflattened and unformatted."""
        raise NotImplementedError


def _build_url(config: Config) -> str:
    endpoint = config.confiform_endpoint
    if not endpoint:
        raise DataSourceError("CONFIFORM_ENDPOINT is not configured.")
    if endpoint.startswith("http://") or endpoint.startswith("https://"):
        return endpoint
    if not config.confluence_url:
        raise DataSourceError("CONFLUENCE_URL is not configured.")
    return f"{config.confluence_url.rstrip('/')}/{endpoint.lstrip('/')}"


def _extract_entries(payload: Any) -> list[dict[str, Any]]:
    """Normalize the shape of a ConfiForms JSON response into a flat list.

    ConfiForms REST/JSON-export responses vary by version/configuration:
    sometimes a bare list of entries, sometimes wrapped under "entries" or
    "results". This accepts any of those shapes.
    """
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        for key in ("entries", "results", "data", "items"):
            value = payload.get(key)
            if isinstance(value, list):
                return value
        # A single entry returned as a bare object.
        return [payload]
    raise DataSourceError(f"Unrecognized ConfiForms response shape: {type(payload)!r}")


class ConfiFormsRestSource(DataSource):
    """Retrieves entries from the ConfiForms REST API."""

    def __init__(self, config: Config):
        self.config = config
        self.session = requests.Session()
        if config.confluence_username and config.confluence_api_token:
            self.session.auth = (config.confluence_username, config.confluence_api_token)

    def fetch(self) -> list[dict[str, Any]]:
        url = _build_url(self.config)
        try:
            response = self.session.get(
                url,
                timeout=self.config.request_timeout,
                verify=self.config.verify_ssl,
                headers={"Accept": "application/json"},
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise DataSourceError(f"REST request to ConfiForms failed: {exc}") from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise DataSourceError("ConfiForms REST response was not valid JSON.") from exc

        return _extract_entries(payload)


class ConfiFormsJsonExportSource(DataSource):
    """Retrieves entries from a ConfiForms JSON export view URL."""

    def __init__(self, config: Config):
        self.config = config
        self.session = requests.Session()
        if config.confluence_username and config.confluence_api_token:
            self.session.auth = (config.confluence_username, config.confluence_api_token)

    def fetch(self) -> list[dict[str, Any]]:
        url = _build_url(self.config)
        try:
            response = self.session.get(
                url,
                timeout=self.config.request_timeout,
                verify=self.config.verify_ssl,
                headers={"Accept": "application/json"},
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise DataSourceError(f"JSON export request to ConfiForms failed: {exc}") from exc

        try:
            payload = response.json()
        except ValueError as exc:
            raise DataSourceError("ConfiForms JSON export response was not valid JSON.") from exc

        return _extract_entries(payload)


class ConfiFormsCsvSource(DataSource):
    """Retrieves entries from a ConfiForms CSV export view URL."""

    def __init__(self, config: Config):
        self.config = config
        self.session = requests.Session()
        if config.confluence_username and config.confluence_api_token:
            self.session.auth = (config.confluence_username, config.confluence_api_token)

    def fetch(self) -> list[dict[str, Any]]:
        url = _build_url(self.config)
        try:
            response = self.session.get(
                url,
                timeout=self.config.request_timeout,
                verify=self.config.verify_ssl,
            )
            response.raise_for_status()
        except requests.RequestException as exc:
            raise DataSourceError(f"CSV export request to ConfiForms failed: {exc}") from exc

        response.encoding = response.encoding or "utf-8"
        reader = csv.DictReader(io.StringIO(response.text))
        return [dict(row) for row in reader]


_SOURCES: dict[str, type[DataSource]] = {
    "rest": ConfiFormsRestSource,
    "json": ConfiFormsJsonExportSource,
    "csv": ConfiFormsCsvSource,
}


def get_data_source(config: Config) -> DataSource:
    """Factory returning the configured DataSource implementation."""
    source_cls = _SOURCES.get(config.data_source_type)
    if source_cls is None:
        valid = ", ".join(sorted(_SOURCES))
        raise DataSourceError(
            f"Unknown DATA_SOURCE_TYPE '{config.data_source_type}'. Valid options: {valid}."
        )
    return source_cls(config)
