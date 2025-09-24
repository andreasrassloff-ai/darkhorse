"""Command line interface for the stock analysis app."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Iterable, List, Sequence

from .data import load_price_history, most_recent_date, validate_enough_data
from .recommender import analyse_stock


def _parse_wkn_argument(argument: str) -> tuple[str, Path]:
    if "=" in argument:
        wkn, _, path = argument.partition("=")
        return wkn.strip(), Path(path.strip())
    return argument.strip(), Path(f"data/{argument.strip()}.json")


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Liest historische Kursdaten ein und erstellt einfache Kauf-, "
            "Verkaufs- oder Halteempfehlungen."
        )
    )
    parser.add_argument(
        "--wkn",
        action="append",
        help=(
            "Wertpapierkennnummer mit optionalem Pfad zur JSON-Datei. "
            "Beispiel: DE0001234567=data/meine_daten.json. Ohne Pfad wird"
            " data/<WKN>.json erwartet."
        ),
    )
    parser.add_argument(
        "--watchlist",
        type=Path,
        help=(
            "Pfad zu einer JSON-Datei mit mehreren WKN-Einträgen. Einträge "
            "können als Liste von Strings oder Objekten mit den Schlüsseln "
            "'wkn' und optional 'path' angegeben werden."
        ),
    )
    parser.add_argument(
        "--min-history",
        type=int,
        default=60,
        help="Minimale Anzahl an Handelstagen für eine Auswertung (Standard: 60).",
    )
    return parser


def _load_watchlist(path: Path) -> List[tuple[str, Path]]:
    """Parse watchlist entries from a JSON file."""

    with path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)

    entries: list[tuple[str, Path]] = []

    def _append_entry(raw_wkn: str, raw_path: str | None) -> None:
        wkn = str(raw_wkn).strip()
        if not wkn:
            raise ValueError("Watchlist-Eintrag ohne WKN gefunden")

        resolved_path: Path
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


def _collect_specs(
    direct_specs: Sequence[str] | None, watchlist_path: Path | None
) -> List[tuple[str, Path]]:
    specs: list[tuple[str, Path]] = []

    if watchlist_path is not None:
        specs.extend(_load_watchlist(watchlist_path))

    if direct_specs:
        for spec in direct_specs:
            specs.append(_parse_wkn_argument(spec))

    return specs


def main(argv: Iterable[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        specs = _collect_specs(args.wkn, args.watchlist)
    except FileNotFoundError:
        parser.error(f"Watchlist-Datei {args.watchlist} wurde nicht gefunden.")
    except ValueError as exc:
        parser.error(str(exc))
    if not specs:
        parser.error(
            "Es wurde keine WKN angegeben. Verwenden Sie --wkn oder --watchlist."
        )

    exit_code = 0
    errors: list[str] = []
    for wkn, path in specs:
        try:
            history = load_price_history(path)
            validate_enough_data(history, args.min_history)
            recommendation = analyse_stock(wkn, history)
        except FileNotFoundError:
            errors.append(
                f"{wkn}: Keine Kursdaten gefunden – erwartete Datei {path}"
            )
        except ValueError as exc:
            errors.append(f"{wkn}: {exc}")
        else:
            latest_date = most_recent_date(history)
            print("=" * 60)
            print(f"Analyse für {wkn}")
            if latest_date is not None:
                print(f"Letzter Handelstag: {latest_date.date().isoformat()}")
            print(f"Empfehlung: {recommendation.action} (Konfidenz {recommendation.confidence:.2f})")
            print("Begründungen:")
            for reason in recommendation.reasons:
                print(f"  - {reason}")

    if errors:
        exit_code = 1
        for message in errors:
            print(message, file=sys.stderr)

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())

