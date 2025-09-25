"""Compatibility wrapper exposing :mod:`darkhorse.main`."""

from __future__ import annotations

from darkhorse.main import *  # noqa: F401,F403


if __name__ == "__main__":
    from darkhorse.main import main as _main

    raise SystemExit(_main())
