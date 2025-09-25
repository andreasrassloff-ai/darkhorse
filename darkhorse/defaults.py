"""Default configuration values for the Darkhorse toolkit."""

from __future__ import annotations

from pathlib import Path

# Standardwerte für den zentralen Start der Anwendung. Diese Werte können bei
# Bedarf angepasst werden, ohne die eigentliche Logik von CLI oder Webserver zu
# verändern.
DEFAULT_DATA_PATH = Path("data/monero.json")
DEFAULT_ASSET_NAME = "Monero (XMR)"
DEFAULT_MINIMUM_HISTORY = 60
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 8000
DEFAULT_START_USD = 0.0
