"""Utilities to fetch live Monero pricing data from public APIs.

In isolated environments without internet access the live API cannot be
reached. To keep the demo applications operational we therefore offer a
light-weight simulation that replays historical Monero prices and maps them
onto a synthetic minute timeline. The trading CLI can seamlessly fall back to
this simulator when network requests fail."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List

from .data import PriceBar, load_price_history
from .kucoin import KuCoinError, collect_price_bars


_SIMULATION_DATA = Path(__file__).resolve().parent.parent / "data" / "monero.json"
_KUCOIN_SIMULATION_DATA = (
    Path(__file__).resolve().parent.parent / "data" / "xmr-kucoin-1hour.json"
)


class LiveDataError(RuntimeError):
    """Raised when fetching live market data fails."""


class SimulatedMoneroFeed:
    """Generate synthetic minute bars based on historical Monero prices."""

    def __init__(self, limit: int = 240, *, history_path: Path | None = None) -> None:
        if limit <= 0:
            raise ValueError("limit must be positive")

        dataset = history_path or (
            _KUCOIN_SIMULATION_DATA if _KUCOIN_SIMULATION_DATA.exists() else _SIMULATION_DATA
        )
        try:
            source = load_price_history(dataset)
        except (OSError, ValueError) as exc:
            raise LiveDataError(
                f"Konnte Simulationsdaten nicht laden: {exc}"
            ) from exc

        if not source:
            raise LiveDataError("Keine historischen Monero-Daten für Simulation vorhanden")

        self._limit = limit
        self._source = source
        self._index = 0
        self._history: list[PriceBar] = []
        self._seed_history()

    def _next_record(self) -> PriceBar:
        record = self._source[self._index]
        self._index = (self._index + 1) % len(self._source)
        return record

    def _seed_history(self) -> None:
        start_time = datetime.now(timezone.utc) - timedelta(minutes=self._limit)
        previous_close: float | None = None
        for offset in range(self._limit):
            record = self._next_record()
            timestamp = start_time + timedelta(minutes=offset)
            bar = self._build_bar(timestamp, record, previous_close)
            previous_close = bar.close
            self._history.append(bar)

    def _build_bar(
        self, timestamp: datetime, record: PriceBar, previous_close: float | None
    ) -> PriceBar:
        open_price = previous_close if previous_close is not None else record.open
        close_price = record.close
        high_price = max(open_price, close_price, record.high)
        low_price = min(open_price, close_price, record.low)
        return PriceBar(
            date=timestamp,
            open=open_price,
            high=high_price,
            low=low_price,
            close=close_price,
            volume=record.volume,
        )

    def current_bars(self) -> list[PriceBar]:
        """Return the currently simulated history."""

        return list(self._history)

    def next_bars(self) -> list[PriceBar]:
        """Advance the simulation by one minute and return the history."""

        record = self._next_record()
        now = datetime.now(timezone.utc)
        timestamp = (
            max(self._history[-1].date + timedelta(minutes=1), now)
            if self._history
            else now
        )
        bar = self._build_bar(timestamp, record, self._history[-1].close if self._history else None)
        self._history.append(bar)
        if len(self._history) > self._limit:
            self._history = self._history[-self._limit :]
        return list(self._history)


def fetch_monero_minute_bars(limit: int = 240) -> List[PriceBar]:
    """Return recent minute candles for Monero priced in USD."""

    if limit <= 0:
        raise LiveDataError("limit must be positive")

    end = datetime.now(timezone.utc)
    # Request slightly more data than necessary to cope with short gaps.
    start = end - timedelta(minutes=max(limit * 2, 10))

    try:
        bars = collect_price_bars("XMR-USDT", "1min", start, end)
    except KuCoinError as exc:  # pragma: no cover - depends on network
        raise LiveDataError(f"Konnte KuCoin-Daten nicht laden: {exc}") from exc

    if not bars:
        raise LiveDataError("KuCoin API lieferte keine Kursdaten")

    return bars[-limit:]

