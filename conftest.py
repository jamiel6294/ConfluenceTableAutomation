"""Ensures the dashboard/ package root is importable when running pytest
from any working directory (app.py, config.py etc. use absolute imports)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
