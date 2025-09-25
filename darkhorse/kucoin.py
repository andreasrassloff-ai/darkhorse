"""Utility helpers to download historical Monero data from KuCoin.

The live trading demo can make use of a local cache with historical price
information.  Because this repository should run in isolated environments we do
not ship a large dataset with it.  Instead this module provides a tiny command
line helper that downloads the required information from the public KuCoin API
and stores it in the JSON layout understood by :mod:`darkhorse.data`.

Typical usage::

    python -m darkhorse.kucoin --years 2 --interval 1hour --output data/xmr-kucoin-1h.json

The command will query the KuCoin REST endpoint in chunks, convert the returned
candles to :class:`~darkhorse.data.PriceBar` compatible dictionaries and write
them to ``output``.  The resulting file can then be supplied to the main
``darkhorse`` commands via ``--data`` or used by the trading demo as
simulation source.
"""

from __future__ import annotations

import argparse
import json
import math
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable, Iterator, List, Sequence
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen

from .data import PriceBar


_API_URL = "https://api.kucoin.com/api/v1/market/candles"


# Mapping taken from the KuCoin API documentation.  The platform restricts the
# number of records per response to at most 1500 candles.  Knowing the duration
# of each candle allows us to iteratively request large time ranges without
# missing data.
_INTERVAL_SECONDS: dict[str, int] = {
    "1min": 60,
    "3min": 180,
    "5min": 300,
    "15min": 900,
    "30min": 1_800,
    "1hour": 3_600,
    "2hour": 7_200,
    "4hour": 14_400,
    "6hour": 21_600,
    "8hour": 28_800,
    "12hour": 43_200,
    "1day": 86_400,
    "1week": 604_800,
}


class KuCoinError(RuntimeError):
    """Raised when interaction with the KuCoin API fails."""


@dataclass(frozen=True)
class KuCoinCandle:
    """Representation of a single KuCoin candle entry."""

    timestamp: datetime
    open: float
    close: float
    high: float
    low: float
    volume: float | None

    def as_price_bar(self) -> PriceBar:
        return PriceBar(
            date=self.timestamp,
            open=self.open,
            high=self.high,
            low=self.low,
            close=self.close,
            volume=self.volume,
        )


def _request_candles(
    symbol: str,
    interval: str,
    start_at: int,
    end_at: int,
) -> Sequence[Sequence[str]]:
    """Perform a single HTTP request against the KuCoin candle endpoint."""

    query = urlencode(
        {
            "type": interval,
            "symbol": symbol,
            "startAt": start_at,
            "endAt": end_at,
        }
    )
    url = f"{_API_URL}?{query}"

    try:
        with urlopen(url, timeout=20) as response:  # type: ignore[arg-type]
            payload = response.read()
    except (HTTPError, URLError) as exc:  # pragma: no cover - depends on network
        raise KuCoinError(f"HTTP request to KuCoin failed: {exc}") from exc

    try:
        data = json.loads(payload)
    except json.JSONDecodeError as exc:  # pragma: no cover - malformed payloads
        raise KuCoinError("Could not decode KuCoin response as JSON") from exc

    if not isinstance(data, dict):
        raise KuCoinError("Unexpected JSON structure returned by KuCoin API")

    if data.get("code") != "200000":
        raise KuCoinError(f"KuCoin API returned error code: {data.get('code')!r}")

    candles = data.get("data")
    if candles is None:
        return []
    if not isinstance(candles, list):
        raise KuCoinError("KuCoin API returned unexpected data format")
    # The response is documented to be sorted from most recent to oldest.  We
    # keep the raw order here and let the caller re-arrange if needed.
    return [candle for candle in candles if isinstance(candle, list)]


def _parse_candle(raw: Sequence[str]) -> KuCoinCandle:
    if len(raw) < 5:
        raise KuCoinError(f"Candle entry contains too few elements: {raw!r}")

    try:
        timestamp = datetime.fromtimestamp(float(raw[0]), tz=timezone.utc)
        open_price = float(raw[1])
        close_price = float(raw[2])
        high_price = float(raw[3])
        low_price = float(raw[4])
    except (TypeError, ValueError) as exc:
        raise KuCoinError(f"Invalid numerical value in candle entry {raw!r}") from exc

    volume: float | None = None
    if len(raw) >= 6:
        try:
            volume_value = float(raw[5])
        except (TypeError, ValueError):
            volume_value = math.nan
        if math.isfinite(volume_value):
            volume = volume_value

    return KuCoinCandle(timestamp, open_price, close_price, high_price, low_price, volume)


def iter_candles(
    symbol: str,
    interval: str,
    start: datetime,
    end: datetime,
    *,
    batch_sleep: float = 0.2,
    batch_size: int = 1_500,
) -> Iterator[KuCoinCandle]:
    """Yield candles for ``symbol`` between ``start`` and ``end`` (inclusive)."""

    if interval not in _INTERVAL_SECONDS:
        raise KuCoinError(f"Unsupported interval {interval!r}")

    interval_seconds = _INTERVAL_SECONDS[interval]
    start_ts = int(start.replace(tzinfo=timezone.utc).timestamp())
    end_ts = int(end.replace(tzinfo=timezone.utc).timestamp())

    if start_ts >= end_ts:
        raise KuCoinError("start must be earlier than end")

    # KuCoin returns results in descending order.  We fetch in chunks moving the
    # window forward to avoid requesting overlapping slices.
    cursor = start_ts
    while cursor < end_ts:
        window_end = min(end_ts, cursor + interval_seconds * batch_size)
        raw_candles = _request_candles(symbol, interval, cursor, window_end)

        if not raw_candles:
            cursor = window_end + interval_seconds
            continue

        # We iterate the response in reverse order so that consumers receive
        # candles sorted by timestamp in ascending order.
        for raw_candle in reversed(raw_candles):
            candle = _parse_candle(raw_candle)
            if candle.timestamp < datetime.fromtimestamp(cursor, tz=timezone.utc):
                continue
            if candle.timestamp > datetime.fromtimestamp(end_ts, tz=timezone.utc):
                continue
            yield candle

        last_timestamp = raw_candles[0][0]
        try:
            cursor = int(float(last_timestamp)) + interval_seconds
        except (TypeError, ValueError):
            cursor = window_end + interval_seconds

        if batch_sleep:
            time.sleep(batch_sleep)  # pragma: no cover - slow path for politeness


def collect_price_bars(
    symbol: str,
    interval: str,
    start: datetime,
    end: datetime,
    *,
    batch_sleep: float = 0.2,
    batch_size: int = 1_500,
) -> List[PriceBar]:
    """Return a list of :class:`PriceBar` entries for the requested range."""

    candles = list(
        iter_candles(
            symbol,
            interval,
            start,
            end,
            batch_sleep=batch_sleep,
            batch_size=batch_size,
        )
    )
    bars = [candle.as_price_bar() for candle in candles]
    bars.sort(key=lambda bar: bar.date)
    return bars


def _serialize_bars(bars: Iterable[PriceBar]) -> list[dict[str, object]]:
    serialised: list[dict[str, object]] = []
    for bar in bars:
        serialised.append(
            {
                "date": bar.date.isoformat(),
                "open": bar.open,
                "high": bar.high,
                "low": bar.low,
                "close": bar.close,
                "volume": bar.volume,
            }
        )
    return serialised


def _default_output_path(interval: str) -> Path:
    filename = f"xmr-kucoin-{interval}.json"
    return Path("data") / filename


def _build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Lädt historische Kurse von KuCoin herunter und speichert sie im "
            "JSON-Format des Projekts."
        )
    )
    parser.add_argument(
        "--symbol",
        default="XMR-USDT",
        help="Handelspaar, das abgerufen werden soll (Standard: %(default)s).",
    )
    parser.add_argument(
        "--interval",
        default="1hour",
        choices=sorted(_INTERVAL_SECONDS.keys()),
        help="Kerzenintervall, z.B. 1min, 1hour oder 1day (Standard: %(default)s).",
    )
    parser.add_argument(
        "--years",
        type=float,
        default=2.0,
        help=(
            "Wie viele Jahre historischer Daten geladen werden sollen. "
            "Kann nicht zusammen mit --start genutzt werden (Standard: %(default)s)."
        ),
    )
    parser.add_argument(
        "--start",
        type=_parse_iso_datetime,
        help="Optionaler Startzeitpunkt im ISO-Format (z.B. 2022-01-01T00:00:00).",
    )
    parser.add_argument(
        "--end",
        type=_parse_iso_datetime,
        default=lambda: datetime.now(tz=timezone.utc),
        help="Optionaler Endzeitpunkt im ISO-Format (Standard: aktuelle Zeit).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Zieldatei für die Kursdaten (Standard: data/xmr-kucoin-<interval>.json).",
    )
    parser.add_argument(
        "--no-sleep",
        action="store_true",
        help=(
            "Verzichtet auf kurze Pausen zwischen API-Aufrufen. Dies beschleunigt "
            "Downloads, kann aber zu Rate-Limits führen."
        ),
    )
    return parser


def _parse_iso_datetime(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value).astimezone(timezone.utc)
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"Ungültiges Datum {value!r}: {exc}") from exc


def _resolve_time_range(
    start: datetime | None,
    end: datetime | None,
    years: float,
) -> tuple[datetime, datetime]:
    resolved_end = end or datetime.now(tz=timezone.utc)
    if start is None:
        resolved_start = resolved_end - timedelta(days=365 * years)
    else:
        resolved_start = start

    if resolved_start >= resolved_end:
        raise KuCoinError("Startzeitpunkt muss vor dem Endzeitpunkt liegen")
    return resolved_start, resolved_end


def main(argv: Iterable[str] | None = None) -> int:
    parser = _build_argument_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)

    end = args.end() if callable(args.end) else args.end
    start, end = _resolve_time_range(args.start, end, args.years)

    batch_sleep = 0.0 if args.no_sleep else 0.2

    try:
        bars = collect_price_bars(
            args.symbol,
            args.interval,
            start,
            end,
            batch_sleep=batch_sleep,
        )
    except KuCoinError as exc:
        parser.error(str(exc))
        return 2  # pragma: no cover - error path after parser.error

    output_path = args.output or _default_output_path(args.interval)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    payload = {"prices": _serialize_bars(bars)}
    with output_path.open("w", encoding="utf-8") as fp:
        json.dump(payload, fp, indent=2)
        fp.write("\n")

    print(
        "Gespeicherte KuCoin-Daten:",
        output_path,
        f"({len(bars)} Kerzen, {args.interval})",
        flush=True,
    )
    return 0


if __name__ == "__main__":  # pragma: no cover - manual usage
    raise SystemExit(main())

