
"""Compatibility wrapper exposing :mod:`darkhorse.specs`."""

from __future__ import annotations

from darkhorse.specs import *  # noqa: F401,F403
=======
"""Utilities for parsing watchlists and WKN specifications."""

from __future__ import annotations

from pathlib import Path
from typing import List, Sequence, Tuple
import json


WknSpec = Tuple[str, Path]


def parse_wkn_argument(argument: str) -> WknSpec:
    """Return the WKN and optional path encoded in an argument string."""

    if "=" in argument:
        wkn, _, raw_path = argument.partition("=")
        return wkn.strip(), Path(raw_path.strip())
    return argument.strip(), Path(f"data/{argument.strip()}.json")


def load_watchlist(path: Path) -> List[WknSpec]:
    """Parse watchlist entries from the provided JSON file."""

    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    entries: list[WknSpec] = []

    def _append_entry(raw_wkn: str, raw_path: str | None) -> None:
        wkn = str(raw_wkn).strip()
        if not wkn:
            raise ValueError("Watchlist-Eintrag ohne WKN gefunden")

        if raw_path:
            candidate = Path(str(raw_path).strip())
            if not candidate.is_absolute():
                candidate = path.parent / candidate
            resolved_path = candidate
        else:
            resolved_path = Path(f"data/{wkn}.json")

        entries.append((wkn, resolved_path))

    if isinstance(payload, list):
        for index, item in enumerate(payload):
            if isinstance(item, str):
                _append_entry(item, None)
            elif isinstance(item, dict):
                _append_entry(item.get("wkn", ""), item.get("path"))
            else:
                raise ValueError(
                    f"Watchlist-Eintrag an Position {index} hat ein unbekanntes Format"
                )
    elif isinstance(payload, dict):
        for wkn, raw_path in payload.items():
            if raw_path is None or isinstance(raw_path, str):
                _append_entry(wkn, raw_path)
            else:
                raise ValueError(
                    f"Watchlist-Eintrag für {wkn} hat ein unbekanntes Format"
                )
    else:
        raise ValueError("Watchlist-Datei muss eine Liste oder ein Objekt enthalten")

    return entries


def collect_specs(
    direct_specs: Sequence[str] | None, watchlist_path: Path | None
) -> List[WknSpec]:
    """Combine direct WKN arguments and optional watchlist entries."""

    specs: list[WknSpec] = []

    if watchlist_path is not None:
        specs.extend(load_watchlist(watchlist_path))

    if direct_specs:
        for spec in direct_specs:
            specs.append(parse_wkn_argument(spec))

    return specs

