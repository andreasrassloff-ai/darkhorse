"""Convenient entry point to start the web interface without parameters."""

from __future__ import annotations

from wsgiref.simple_server import make_server

from .defaults import (
    DEFAULT_ASSET_NAME,
    DEFAULT_DATA_PATH,
    DEFAULT_HOST,
    DEFAULT_MINIMUM_HISTORY,
    DEFAULT_PORT,
)
from .web import create_app


def main() -> int:
    """Start the web interface with the default configuration."""

    app = create_app(DEFAULT_DATA_PATH, DEFAULT_ASSET_NAME, DEFAULT_MINIMUM_HISTORY)

    with make_server(DEFAULT_HOST, DEFAULT_PORT, app) as server:
        print(
            "Server gestartet auf "
            f"http://{server.server_address[0]}:{server.server_address[1]} "
            "– drücken Sie Strg+C zum Beenden."
        )
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("Server wird beendet...")

    return 0


if __name__ == "__main__":  # pragma: no cover - module behaviour
    raise SystemExit(main())
