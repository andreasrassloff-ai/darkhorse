"""Compatibility wrapper exposing :mod:`darkhorse.main`."""

from __future__ import annotations


from darkhorse.main import *  # noqa: F401,F403
=======
import argparse
import sys
from pathlib import Path
from typing import Iterable, List, Sequence

from .data import load_price_history, most_recent_date, validate_enough_data
from .recommender import analyse_stock
from .specs import collect_specs


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
def main(argv: Iterable[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        specs = collect_specs(args.wkn, args.watchlist)
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
    from darkhorse.main import main as _main

    raise SystemExit(_main())
