"""Flask application factory and routes for the ConfiForms dashboard."""
from __future__ import annotations

from flask import Flask, jsonify, render_template

from config import Config
from config import config as default_config
from services.cache import TTLCache
from services.confiforms import DataSource, DataSourceError, get_data_source
from services.transforms import build_dashboard_payload


def create_app(app_config: Config | None = None, data_source: DataSource | None = None) -> Flask:
    """Build the Flask app.

    `app_config`/`data_source` are injectable so tests can supply a fake
    data source instead of hitting a real Confluence instance.
    """
    app_config = app_config or default_config
    app = Flask(__name__)
    app.config["APP_CONFIG"] = app_config

    source = data_source or get_data_source(app_config)
    cache: TTLCache = TTLCache(ttl_seconds=app_config.refresh_interval)

    @app.get("/")
    def index():
        return render_template(
            "dashboard.html",
            refresh_interval=app_config.refresh_interval,
        )

    @app.get("/api/data")
    def api_data():
        try:
            raw_entries = cache.get_or_fetch(source.fetch)
        except DataSourceError as exc:
            return jsonify({"error": str(exc)}), 502

        payload = build_dashboard_payload(raw_entries, app_config.status_colors)
        return jsonify(payload.to_dict())

    @app.get("/health")
    def health():
        return jsonify({"status": "ok"})

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=default_config.port, debug=default_config.debug)
