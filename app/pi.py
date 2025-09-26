"""Compatibility wrapper exposing :mod:`darkhorse.pi`."""

from __future__ import annotations

from darkhorse.pi import *  # noqa: F401,F403


if __name__ == "__main__":
    from darkhorse.pi import main as _main

    raise SystemExit(_main())
