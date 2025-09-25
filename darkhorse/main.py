"""Command line interface for the Darkhorse Monero analysis toolkit."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Iterable

from .data import load_price_history, most_recent_date, validate_enough_data
from .defaults import DEFAULT_ASSET_NAME, DEFAULT_DATA_PATH, DEFAULT_MINIMUM_HISTORY
from .recommender import analyse_asset


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Analysiert historische Monero-Kursdaten und erstellt einfache Kauf-, "
            "Verkaufs- oder Halteempfehlungen."
        )
    )
    parser.add_argument(
        "--data",
        type=Path,
        default=DEFAULT_DATA_PATH,
        help=(
            "Pfad zur JSON-Datei mit Monero-Kursen. "
            "Standard ist data/monero.json."
        ),
    )
    parser.add_argument(
        "--min-history",
        type=int,
        default=DEFAULT_MINIMUM_HISTORY,
        help="Minimale Anzahl an Handelstagen für eine Auswertung (Standard: 60).",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        history = load_price_history(args.data)
    except FileNotFoundError:
        parser.error(f"Kursdatei {args.data} wurde nicht gefunden.")
    except ValueError as exc:
        parser.error(str(exc))

    try:
        validate_enough_data(history, args.min_history)
    except ValueError as exc:
        parser.error(str(exc))

    recommendation = analyse_asset(DEFAULT_ASSET_NAME, history)
    latest_date = most_recent_date(history)

    print("=" * 60)
    print(f"Analyse für {DEFAULT_ASSET_NAME}")
    if latest_date is not None:
        print(f"Letzter Handelstag: {latest_date.date().isoformat()}")
    print(
        "Empfehlung: "
        f"{recommendation.action} (Konfidenz {recommendation.confidence:.2f})"
    )
    print("Begründungen:")
    for reason in recommendation.reasons:
        print(f"  - {reason}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
