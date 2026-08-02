"""Windows production entrypoint, served via Waitress.

Usage:
    python wsgi.py
"""
from waitress import serve

from app import app
from config import config

if __name__ == "__main__":
    serve(app, host="0.0.0.0", port=config.port)
