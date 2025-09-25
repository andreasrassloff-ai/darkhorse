"""Utilities for loading historical price data for stocks.

The application expects JSON files that contain either a list of candle
objects or a mapping with the key ``"prices"`` whose value is that list. Each
object must provide at least the following fields:

```
date, open, high, low, close
```

``volume`` is optional. The values are parsed into :class:`PriceBar` records
which are then used by the analysis module. The loader is intentionally
lightweight so that the application stays dependency free and works in
constrained environments.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable, List, Sequence


@dataclass(frozen=True)
class PriceBar:
    """Representation of a single OHLCV candle.

    Attributes
    ----------
    date:
        Trading day of the observation.
    open, high, low, close:
        Price points for the period.
    volume:
        Optional trade volume. Missing data is represented by ``None``.
    """

    date: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float | None


def _parse_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        stripped = value.strip()
        if stripped == "":
            return None
        return float(stripped.replace(",", "."))
    raise ValueError(f"Cannot interpret value {value!r} as float")


def _require_float(name: str, value: Any) -> float:
    parsed = _parse_float(value)
    if parsed is None:
        raise ValueError(f"Missing value for '{name}'")
    return parsed


def load_price_history(path: str | Path) -> List[PriceBar]:
    """Load price history from a JSON file.

    Parameters
    ----------
    path:
        Location of the JSON file. Both :class:`str` and :class:`Path` objects
        are accepted.

    Returns
    -------
    list of :class:`PriceBar`
        Sorted by date in ascending order.
    """

    path = Path(path)
    import json

    with path.open("r", encoding="utf-8") as f:
        payload = json.load(f)

    if isinstance(payload, dict):
        records = payload.get("prices")
        if records is None:
            raise ValueError(
                "JSON file must contain a list of price bars or a 'prices' key"
            )
    elif isinstance(payload, list):
        records = payload
    else:
        raise ValueError("Unexpected JSON structure for price history")

    if not isinstance(records, list):
        raise ValueError("'prices' entry must be a list of objects")

    bars: list[PriceBar] = []
    for index, row in enumerate(records):
        if not isinstance(row, dict):
            raise ValueError(f"Entry {index} is not an object")
        if "date" not in row:
            raise ValueError(f"Entry {index} does not specify a 'date'")

        try:
            bars.append(
                PriceBar(
                    date=datetime.fromisoformat(str(row["date"])),
                    open=_require_float("open", row.get("open")),
                    high=_require_float("high", row.get("high")),
                    low=_require_float("low", row.get("low")),
                    close=_require_float("close", row.get("close")),
                    volume=_parse_float(row.get("volume")),
                )
            )
        except ValueError as exc:
            raise ValueError(f"Invalid entry at index {index}: {exc}") from exc

    bars.sort(key=lambda bar: bar.date)
    return bars


def closing_prices(bars: Sequence[PriceBar]) -> List[float]:
    """Extract a list with only the closing prices from the bars."""

    return [bar.close for bar in bars]


def most_recent_date(bars: Sequence[PriceBar]) -> datetime | None:
    """Return the most recent trading date in the sequence."""

    if not bars:
        return None
    return max(bar.date for bar in bars)


def validate_enough_data(bars: Sequence[PriceBar], minimum: int) -> None:
    """Ensure that enough data is available for indicator calculation."""

    if len(bars) < minimum:
        raise ValueError(
            "Not enough price history to analyse. "
            f"Expected at least {minimum} data points, got {len(bars)}."
        )

