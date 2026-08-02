from datetime import datetime, timedelta

from models.schema import FieldKind
from services.transforms import build_dashboard_payload, flatten_entries, infer_columns


RAW_ENTRIES = [
    {
        "Title": "Server migration",
        "Status": {"value": "Open"},
        "Owner": {"value": "Alice"},
        "Progress": "40%",
        "DueDate": "2026-08-10",
    },
    {
        "Title": "Patch rollout",
        "Status": "Blocked",
        "Owner": "Bob",
        "Progress": 90,
        "DueDate": "2026-07-01",
    },
]


def test_flatten_entries_unwraps_nested_field_values():
    df = flatten_entries(RAW_ENTRIES)
    assert df.loc[0, "Status"] == "Open"
    assert df.loc[0, "Owner"] == "Alice"
    assert df.loc[1, "Status"] == "Blocked"


def test_infer_columns_assigns_expected_kinds():
    df = flatten_entries(RAW_ENTRIES)
    columns = {c.field: c.kind for c in infer_columns(df)}
    assert columns["Status"] == FieldKind.STATUS
    assert columns["Owner"] == FieldKind.OWNER
    assert columns["Progress"] == FieldKind.PROGRESS
    assert columns["DueDate"] == FieldKind.DATE
    assert columns["Title"] == FieldKind.TEXT


def test_build_dashboard_payload_coerces_progress_and_dates():
    payload = build_dashboard_payload(RAW_ENTRIES, status_colors={"Open": "#28a745"})

    assert len(payload.rows) == 2
    assert payload.rows[0]["Progress"] == 40.0
    assert payload.rows[1]["Progress"] == 90.0
    assert payload.rows[0]["DueDate"].startswith("2026-08-10")
    assert payload.status_colors == {"Open": "#28a745"}
    assert payload.generated_at != ""


def test_build_dashboard_payload_handles_empty_input():
    payload = build_dashboard_payload([], status_colors={})
    assert payload.rows == []
    assert payload.columns == []


def test_column_titles_preserve_acronyms_and_split_identifiers():
    df = flatten_entries(
        [{"Case ID": "CASE-100", "Awaited From": "2026-07-20", "DueDate": "2026-08-01", "user_owner": "Alice"}]
    )
    titles = {c.field: c.title for c in infer_columns(df)}
    assert titles["Case ID"] == "Case ID"
    assert titles["Awaited From"] == "Awaited From"
    assert titles["DueDate"] == "Due Date"
    assert titles["user_owner"] == "User Owner"


def test_awaited_from_is_classified_as_date():
    df = flatten_entries(
        [{"Operation": "Password reset", "Case ID": "CASE-100", "Awaited From": "2026-07-20"}]
    )
    columns = {c.field: c.kind for c in infer_columns(df)}
    assert columns["Awaited From"] == FieldKind.DATE


def test_build_dashboard_payload_adds_days_ago_column_from_awaited_from():
    awaited_date = (datetime.now() - timedelta(days=5)).strftime("%Y-%m-%d")
    entries = [
        {
            "Operation": "Password reset",
            "Case ID": "CASE-100",
            "Target": "svc-account",
            "Status": "Pending",
            "Awaited From": awaited_date,
        }
    ]

    payload = build_dashboard_payload(entries, status_colors={})

    field_names = [c.field for c in payload.columns]
    assert field_names[-1] == "Days Ago"
    assert payload.columns[-1].kind == FieldKind.NUMBER
    assert payload.rows[0]["Days Ago"] == 5


def test_build_dashboard_payload_omits_days_ago_without_awaited_from():
    payload = build_dashboard_payload(RAW_ENTRIES, status_colors={})
    field_names = [c.field for c in payload.columns]
    assert "Days Ago" not in field_names


def test_build_dashboard_payload_days_ago_handles_missing_date():
    entries = [
        {
            "Operation": "Password reset",
            "Case ID": "CASE-100",
            "Status": "Pending",
            "Awaited From": "",
        }
    ]
    payload = build_dashboard_payload(entries, status_colors={})
    assert payload.rows[0]["Days Ago"] is None
