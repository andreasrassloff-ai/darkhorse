"""Convenient entry point to start the web interface without parameters."""

from __future__ import annotations

import sys
from wsgiref.simple_server import make_server

from .defaults import (
    DEFAULT_HOST,
    DEFAULT_MINIMUM_HISTORY,
    DEFAULT_PORT,
    DEFAULT_WATCHLIST_PATH,
)
from .specs import load_watchlist
from .web import create_app


def _load_default_specs():
    try:
        specs = load_watchlist(DEFAULT_WATCHLIST_PATH)
    except FileNotFoundError as exc:  # pragma: no cover - defensive programming
        print(
            f"Standard-Watchlist {DEFAULT_WATCHLIST_PATH} wurde nicht gefunden.",
            file=sys.stderr,
        )
        raise SystemExit(2) from exc
    except ValueError as exc:  # pragma: no cover - defensive programming
        print(str(exc), file=sys.stderr)
        raise SystemExit(2) from exc

    if not specs:
        print(
            f"Die Standard-Watchlist {DEFAULT_WATCHLIST_PATH} enthält keine Einträge.",
            file=sys.stderr,
        )
        raise SystemExit(2)

    return specs


def main() -> int:
    """Start the web interface with the default configuration."""

    specs = _load_default_specs()
    app = create_app(specs, DEFAULT_MINIMUM_HISTORY)

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
