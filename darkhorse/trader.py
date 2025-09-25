
"""Simple live trading demo that rebalances between Monero and USD each minute."""


from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime, timezone
from typing import Iterable

from .defaults import (
    DEFAULT_ASSET_NAME,
    DEFAULT_MINIMUM_HISTORY,
    DEFAULT_START_USD,
)

from .live import LiveDataError, SimulatedMoneroFeed, fetch_monero_minute_bars

from .recommender import analyse_asset


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Startet eine Demo, die jede Minute aktuelle Monero-Preise lädt, "

            "die Analyse ausführt und den Bestand anteilig zwischen XMR und "
            "USD umschichtet."

        )
    )
    parser.add_argument(
        "--min-history",
        type=int,
        default=DEFAULT_MINIMUM_HISTORY,
        help=(
            "Mindestanzahl an Minutenkerzen für eine Auswertung. "
            "Standard: %(default)s."
        ),
    )
    parser.add_argument(
        "--history-limit",
        type=int,
        default=240,
        help=(
            "Wie viele Minutenkerzen zur Analyse herangezogen werden sollen. "
            "Standard: %(default)s."
        ),
    )
    parser.add_argument(
        "--interval",
        type=float,
        default=60.0,
        help="Anzahl Sekunden zwischen zwei Trades (Standard: 60).",
    )
    parser.add_argument(
        "--trade-fraction",
        type=float,
        default=0.4,
        help=(
            "Maximaler Anteil des verfügbaren Kapitals, der pro Zyklus umgeschichtet "
            "werden darf (0–1, Standard: %(default)s)."
        ),
    )
    parser.add_argument(

        "--iterations",
        type=int,
        default=0,
        help=(
            "Anzahl der Durchläufe. 0 bedeutet, dass die Demo endlos läuft "
            "(Standard)."
        ),
    )
    parser.add_argument(
        "--start-xmr",
        type=float,
        default=1.0,
        help="Startbestand in Monero. Standard: %(default)s XMR.",
    )
    parser.add_argument(
        "--start-usd",
        type=float,
        default=DEFAULT_START_USD,
        help="Startbestand in USD. Standard: %(default)s.",
    )
    return parser


def _log_portfolio(timestamp: datetime, price: float, xmr: float, usd: float) -> None:
    total_value = usd + xmr * price
    print(
        f"[{timestamp.isoformat()}] Preis: {price:.2f} USD | "
        f"Bestand: {xmr:.6f} XMR / {usd:.2f} USD | Gesamtwert: {total_value:.2f} USD",
        flush=True,
    )


def main(argv: Iterable[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    xmr_balance = float(args.start_xmr)
    usd_balance = float(args.start_usd)

    trade_fraction = min(max(float(args.trade_fraction), 0.0), 1.0)

    iteration = 0
    print(
        "Starte Live-Demo: Wir gewichten das Portfolio dynamisch zwischen XMR und USD neu."
    )

    history = []

    simulation_feed: SimulatedMoneroFeed | None = None
    simulation_active = False
    while True:
        try:
            history = fetch_monero_minute_bars(args.history_limit)
            if simulation_active:
                print(
                    "Live-Daten wieder verfügbar – beende Simulation.",
                    file=sys.stderr,
                )
            simulation_feed = None
            simulation_active = False
        except LiveDataError as exc:
            if simulation_feed is None:
                try:
                    simulation_feed = SimulatedMoneroFeed(args.history_limit)
                except LiveDataError as sim_exc:
                    print(
                        "Fehler beim Laden der Live-Daten: "
                        f"{exc}. Simulation ebenfalls nicht möglich: {sim_exc}",
                        file=sys.stderr,
                    )
                    time.sleep(max(args.interval, 1.0))
                    continue
                print(
                    "Live-Daten nicht verfügbar – verwende historische Daten zur Simulation.",
                    file=sys.stderr,
                )
            history = simulation_feed.next_bars()
            simulation_active = True

        if len(history) < args.min_history:
            print(
                "Zu wenige Datenpunkte erhalten – warte auf mehr Daten...",

                file=sys.stderr,
            )
            time.sleep(max(args.interval, 1.0))
            continue

        iteration += 1
        recommendation = analyse_asset(DEFAULT_ASSET_NAME, history[-args.min_history :])
        latest_bar = history[-1]
        price = latest_bar.close
        timestamp = latest_bar.date

        _log_portfolio(timestamp, price, xmr_balance, usd_balance)
        print(
            f"Empfehlung: {recommendation.action} (Konfidenz {recommendation.confidence:.2f})",
            flush=True,
        )


        effective_fraction = trade_fraction * recommendation.confidence
        if recommendation.action == "Buy":
            if usd_balance > 0 and effective_fraction > 0:
                usd_to_spend = usd_balance * effective_fraction
                xmr_purchased = usd_to_spend / price
                xmr_balance += xmr_purchased
                usd_balance -= usd_to_spend
                print(
                    " -> Kaufe "
                    f"{xmr_purchased:.6f} XMR für {usd_to_spend:.2f} USD "
                    f"(Anteil {effective_fraction:.2%}).",
                    flush=True,
                )
            else:
                print(
                    " -> Kein USD-Bestand oder zu geringe Konfidenz – kein Kauf.",
                    flush=True,
                )
        elif recommendation.action == "Sell":
            if xmr_balance > 0 and effective_fraction > 0:
                xmr_to_sell = xmr_balance * effective_fraction
                usd_gained = xmr_to_sell * price
                xmr_balance -= xmr_to_sell
                usd_balance += usd_gained
                print(
                    " -> Verkaufe "
                    f"{xmr_to_sell:.6f} XMR und erhalte {usd_gained:.2f} USD "
                    f"(Anteil {effective_fraction:.2%}).",
                    flush=True,
                )
            else:
                print(
                    " -> Kein XMR-Bestand oder zu geringe Konfidenz – kein Verkauf.",
                    flush=True,
                )

        else:
            print(" -> Halte Position, keine Aktion.", flush=True)

        print("-" * 80, flush=True)

        if args.iterations and iteration >= args.iterations:
            break

        time.sleep(max(args.interval, 0.0))

    if not history:
        print("Keine Kursdaten verfügbar – Demo wird beendet.")
        return 1

    final_price = history[-1].close
    print("Endstand der Demo:")
    _log_portfolio(datetime.now(timezone.utc), final_price, xmr_balance, usd_balance)
    return 0


if __name__ == "__main__":  # pragma: no cover - module behaviour
    raise SystemExit(main())

