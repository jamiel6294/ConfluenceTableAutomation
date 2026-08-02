"""Normalizes raw ConfiForms entries into a Pandas DataFrame and, from it,
the Column/row payload the frontend consumes.

This module has no network dependency and is pure data transformation,
which keeps it easy to unit test in isolation from ConfiForms/Confluence.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone
from typing import Any

import pandas as pd

from models.schema import Column, DashboardPayload, FieldKind

_STATUS_NAME_RE = re.compile(r"status$", re.IGNORECASE)
_OWNER_NAME_RE = re.compile(r"(owner|assignee)", re.IGNORECASE)
_DATE_NAME_RE = re.compile(r"(date|due|deadline|awaited)", re.IGNORECASE)
_PROGRESS_NAME_RE = re.compile(r"(progress|percent|_pct$)", re.IGNORECASE)

DAYS_AGO_FIELD = "Days Ago"

# Fields ConfiForms adds internally that aren't meaningful to display.
_HIDDEN_FIELDS = {"entryId", "formName", "spaceKey", "userKey", "modificationDate_hidden"}


def _flatten_value(value: Any) -> Any:
    """Reduce ConfiForms' nested field-value objects to a scalar/string."""
    if isinstance(value, dict):
        for key in ("value", "label", "name", "text"):
            if key in value:
                return _flatten_value(value[key])
        if not value:
            return ""
        return ", ".join(str(_flatten_value(v)) for v in value.values())
    if isinstance(value, (list, tuple, set)):
        return ", ".join(str(_flatten_value(v)) for v in value)
    return value


def flatten_entries(raw_entries: list[dict[str, Any]]) -> pd.DataFrame:
    """Flatten raw ConfiForms entries into a rectangular DataFrame."""
    flattened = [
        {k: _flatten_value(v) for k, v in entry.items() if k not in _HIDDEN_FIELDS}
        for entry in raw_entries
    ]
    return pd.DataFrame(flattened)


def _infer_kind(field_name: str) -> FieldKind:
    if _STATUS_NAME_RE.search(field_name):
        return FieldKind.STATUS
    if _OWNER_NAME_RE.search(field_name):
        return FieldKind.OWNER
    if _PROGRESS_NAME_RE.search(field_name):
        return FieldKind.PROGRESS
    if _DATE_NAME_RE.search(field_name):
        return FieldKind.DATE
    return FieldKind.TEXT


def _humanize_field_name(field_name: str) -> str:
    """Derive a display title from a field name.

    Already human-readable names (e.g. "Case ID", "Awaited From") are left
    untouched so acronyms survive; programmatic identifiers (snake_case,
    camelCase) are split into words and title-cased.
    """
    if " " in field_name:
        return field_name.strip()
    spaced = re.sub(r"[_\-]+", " ", field_name)
    spaced = re.sub(r"(?<!^)(?=[A-Z])", " ", spaced)
    return spaced.strip().title()


def infer_columns(df: pd.DataFrame) -> list[Column]:
    columns: list[Column] = []
    for field_name in df.columns:
        kind = _infer_kind(field_name)
        title = _humanize_field_name(field_name)
        columns.append(Column(field=field_name, title=title, kind=kind))
    return columns


def _coerce_progress(value: Any) -> float | None:
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().rstrip("%")
    try:
        return float(text)
    except ValueError:
        return None


def _coerce_date(value: Any) -> str | None:
    if value is None or value == "":
        return None
    if isinstance(value, (datetime, pd.Timestamp)):
        dt = value
    else:
        try:
            dt = pd.to_datetime(value, utc=False)
        except (ValueError, TypeError):
            return str(value)
    if pd.isna(dt):
        return None
    return dt.isoformat()


def _clean_row(row: dict[str, Any], columns: list[Column]) -> dict[str, Any]:
    cleaned: dict[str, Any] = {}
    for column in columns:
        value = row.get(column.field)
        if pd.isna(value) if not isinstance(value, (list, dict)) else False:
            value = None

        if column.kind == FieldKind.PROGRESS:
            value = _coerce_progress(value)
        elif column.kind == FieldKind.DATE:
            value = _coerce_date(value)
        elif value is not None and not isinstance(value, (str, int, float, bool)):
            value = str(value)

        cleaned[column.field] = value
    return cleaned


def _normalize_name(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


def _find_awaited_from_field(columns: list[Column]) -> str | None:
    """Locate the ConfiForms field that holds the entry's created/awaited date.

    ConfiForms exposes this as "Awaited From" — despite the name, it's the
    date the entry was submitted, used here to derive how long a status has
    been outstanding.
    """
    for column in columns:
        if "awaitedfrom" in _normalize_name(column.field):
            return column.field
    return None


def _compute_days_ago(iso_date: str | None) -> int | None:
    if not iso_date:
        return None
    try:
        parsed = pd.to_datetime(iso_date)
    except (ValueError, TypeError):
        return None
    if pd.isna(parsed):
        return None
    today = pd.Timestamp.now().normalize()
    return int((today - parsed.normalize()).days)


def _add_days_ago_column(columns: list[Column], rows: list[dict[str, Any]]) -> None:
    """Appends a computed "Days Ago" column based on the Awaited From date.

    This is derived entirely in Python (not extracted from ConfiForms) since
    ConfiForms IFTTT rules can't express "days since created" directly.
    """
    awaited_from_field = _find_awaited_from_field(columns)
    if awaited_from_field is None:
        return

    columns.append(Column(field=DAYS_AGO_FIELD, title=DAYS_AGO_FIELD, kind=FieldKind.NUMBER))
    for row in rows:
        row[DAYS_AGO_FIELD] = _compute_days_ago(row.get(awaited_from_field))


def build_dashboard_payload(
    raw_entries: list[dict[str, Any]], status_colors: dict[str, str]
) -> DashboardPayload:
    df = flatten_entries(raw_entries)

    if df.empty:
        return DashboardPayload(
            columns=[],
            rows=[],
            status_colors=status_colors,
            generated_at=datetime.now(timezone.utc).isoformat(),
        )

    columns = infer_columns(df)
    rows = [_clean_row(row, columns) for row in df.to_dict(orient="records")]
    _add_days_ago_column(columns, rows)

    return DashboardPayload(
        columns=columns,
        rows=rows,
        status_colors=status_colors,
        generated_at=datetime.now(timezone.utc).isoformat(),
    )
