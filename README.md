# ConfiForms Dashboard

A standalone Python/Flask application that retrieves ConfiForms data from
Atlassian Confluence Data Center and renders it as a modern, interactive
dashboard (Bootstrap 5 + Tabulator), embedded back into Confluence via an
iframe. No Confluence plugin development required.

## Architecture

```
Confluence (ConfiForms) --REST/JSON/CSV--> Flask app --JSON--> Browser (Tabulator)
```

- `services/confiforms.py` — pluggable data sources (REST API, JSON export,
  CSV export) behind a common `DataSource` interface.
- `services/cache.py` — thread-safe TTL cache so Confluence isn't hit on
  every page load/poll.
- `services/transforms.py` — Pandas-based normalization: flattens ConfiForms
  field values, infers column types (status/owner/date/progress/text),
  coerces dates and percentages.
- `app.py` — Flask routes: `/` (dashboard shell), `/api/data` (JSON payload
  consumed by Tabulator), `/health`.
- `static/js/dashboard.js` — Tabulator setup: search, filters, sorting,
  pagination, export, auto-refresh, conditional row/badge/progress styling.

## Installation

Requires Python 3.11+.

```powershell
cd dashboard
python -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
copy .env.example .env
```

Edit `.env` with your Confluence/ConfiForms details (see Configuration below).

## Configuration

All configuration is via environment variables (loaded from `.env` if
present) — see `.env.example` for the full list. Key variables:

| Variable | Purpose |
|---|---|
| `DATA_SOURCE_TYPE` | `rest`, `json`, or `csv` — which retrieval mechanism to use |
| `CONFLUENCE_URL` | Base Confluence URL |
| `CONFLUENCE_USERNAME` / `CONFLUENCE_API_TOKEN` | Service account credentials (never hardcode these) |
| `CONFIFORM_ENDPOINT` | Path or full URL to the ConfiForms export/REST endpoint |
| `REFRESH_INTERVAL` | Seconds between auto-refreshes (default 60) |
| `STATUS_COLORS` | Optional JSON object overriding badge colors |
| `PORT` | Port the app listens on |

## Running locally (development)

```powershell
.venv\Scripts\python.exe app.py
```

Visit `http://localhost:5000`.

## Running in production (Windows, Waitress)

```powershell
.venv\Scripts\python.exe wsgi.py
```

For Linux deployment, use Gunicorn instead: `gunicorn -w 4 -b 0.0.0.0:5000 app:app`.

Put the app behind a reverse proxy (Nginx/Apache/IIS) terminating HTTPS, and
restrict access to the internal network. Do not expose the Flask dev server
(`app.py` directly) in production — always use Waitress/Gunicorn.

## Embedding in Confluence

Add an **iframe** macro (or raw HTML macro, if enabled) to the target
Confluence page pointing at the dashboard's HTTPS URL, e.g.:

```html
<iframe src="https://dashboard.internal.example.com/" width="100%" height="900" frameborder="0"></iframe>
```

## Testing

```powershell
.venv\Scripts\python.exe -m pytest tests/ -v
```

Tests cover the cache, data source parsing/error handling, transform logic,
and the Flask routes (via a fake in-memory data source — no live Confluence
connection required).

## Troubleshooting

- **502 from `/api/data`**: the configured data source failed — check
  `CONFLUENCE_URL`, `CONFIFORM_ENDPOINT`, and credentials in `.env`, and the
  Flask server logs for the underlying request error.
- **Empty dashboard, no error**: the data source returned zero entries —
  confirm the ConfiForms endpoint/form name is correct.
- **Self-signed certificate errors**: set `VERIFY_SSL=false` only for
  trusted internal testing, never in production.
- **Dashboard not updating**: check `REFRESH_INTERVAL` and browser console
  for fetch errors; use the manual refresh button to force a poll.

## Administrator Guide

- Status badge colors are configurable via `STATUS_COLORS` without code
  changes.
- Column types (status/owner/date/progress) are inferred automatically from
  field names — rename ConfiForms fields to include `status`, `owner`,
  `date`, or `progress`/`percent` to get the corresponding rich rendering;
  everything else renders as searchable/filterable text.
- To switch data source (e.g. from REST to CSV export) change
  `DATA_SOURCE_TYPE` and `CONFIFORM_ENDPOINT` — no code changes required.

All 26 tests still pass. Summary of changes made:

services/transforms.py: "Awaited From" is now classified as a date field, and a computed "Days Ago" column (int((today - awaited_date).days)) is automatically appended — pure Python, no ConfiForms IFTTT needed. It's detected generically by field name, so it'll work across all 3 of your table views as long as they share the "Awaited From" field. Also fixed column-title generation to preserve acronyms/spacing ("Case ID" no longer becomes "Case Id").
static/js/dashboard.js: added a number column type with red/amber severity coloring past 7/14 days; locked column widths (widthGrow: 0) so "Days Ago" no longer stretches disproportionately; default sort is now Days Ago ascending (earliest → longest wait).
Tests updated/added (26 total, all passing) and verified visually via a live smoke test.
For the 3-page merge/switcher: your current DataSource abstraction already takes one CONFIFORM_ENDPOINT. The natural extension later is a small config list of named endpoints and a toolbar tab/button group that calls /api/data?view=<name> — happy to build that when you're ready.