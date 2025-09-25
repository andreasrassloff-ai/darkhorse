"""Entry point forwarding to :mod:`darkhorse.__main__`."""

from __future__ import annotations

from darkhorse.__main__ import main


if __name__ == "__main__":
    raise SystemExit(main())
