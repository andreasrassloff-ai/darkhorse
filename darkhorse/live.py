"""Utilities to fetch live Monero pricing data from public APIs."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, List
from urllib.error import URLError, HTTPError
from urllib.request import urlopen
import json

from .data import PriceBar

# CoinGecko offers free access to market data without the need for API keys.
# We rely on the minute resolution endpoint which returns up to 24 hours of
# price history.  The returned payload is a mapping with the key "prices"
# whose values are pairs of ``[timestamp, price]``.
_MARKET_CHART_URL = (
    "https://api.coingecko.com/api/v3/coins/monero/market_chart"
    "?vs_currency=usd&days=1&interval=minute"
)


class LiveDataError(RuntimeError):
    """Raised when fetching live market data fails."""


def _fetch_json(url: str) -> Any:
    try:
        with urlopen(url, timeout=15) as response:  # type: ignore[arg-type]
            if response.status != 200:
                raise LiveDataError(f"Unexpected status code {response.status} from API")
            payload = response.read()
    except (HTTPError, URLError) as exc:  # pragma: no cover - depends on network
        raise LiveDataError(f"Could not download live data: {exc}") from exc

    try:
        return json.loads(payload)
    except json.JSONDecodeError as exc:  # pragma: no cover - malformed data
        raise LiveDataError("Received malformed JSON payload from API") from exc


def fetch_monero_minute_bars(limit: int = 240) -> List[PriceBar]:
    """Return recent minute candles for Monero priced in USD.

    Parameters
    ----------
    limit:
        Maximum number of minute bars to return. The API yields up to 24 hours
        of data; the latest ``limit`` entries are used to keep calculations
        efficient.
    """

    payload = _fetch_json(_MARKET_CHART_URL)
    prices = payload.get("prices")
    if not isinstance(prices, list):
        raise LiveDataError("API response does not contain a 'prices' list")

    bars: List[PriceBar] = []
    for entry in prices[-limit:]:
        if not isinstance(entry, list) or len(entry) != 2:
            raise LiveDataError("Unexpected price entry structure in API response")
        timestamp_ms, price = entry
        try:
            timestamp = datetime.fromtimestamp(float(timestamp_ms) / 1000.0, tz=timezone.utc)
            price_value = float(price)
        except (TypeError, ValueError) as exc:
            raise LiveDataError("Invalid timestamp or price value in API response") from exc

        bars.append(
            PriceBar(
                date=timestamp,
                open=price_value,
                high=price_value,
                low=price_value,
                close=price_value,
                volume=None,
            )
        )

    if not bars:
        raise LiveDataError("API response did not return any price entries")

    return bars

