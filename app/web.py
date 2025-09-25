"""Compatibility wrapper exposing :mod:`darkhorse.web`."""

from __future__ import annotations

from darkhorse.web import *  # noqa: F401,F403


if __name__ == "__main__":
    from darkhorse.web import main as _main

    raise SystemExit(_main())
