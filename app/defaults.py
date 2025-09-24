"""Default configuration values for the Darkhorse app."""

from __future__ import annotations

from pathlib import Path

# Standardwerte für den zentralen Start der Anwendung. Diese Werte können bei
# Bedarf angepasst werden, ohne die eigentliche Logik von CLI oder Webserver zu
# verändern.
DEFAULT_WATCHLIST_PATH = Path("watchlists/beobachtungsliste.json")
DEFAULT_MINIMUM_HISTORY = 60
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000
