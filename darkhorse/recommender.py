"""Generate buy/hold/sell recommendations from indicator values."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence

from . import indicators
from .data import PriceBar, closing_prices


@dataclass(frozen=True)
class Recommendation:
    asset: str
    action: str
    confidence: float
    reasons: list[str]


def _format_percentage(value: float) -> str:
    return f"{value * 100:.1f}%"


def analyse_asset(asset: str, history: Sequence[PriceBar]) -> Recommendation:
    prices = closing_prices(history)
    reasons: list[str] = []

    short_sma_window = 20
    long_sma_window = 50
    trend_window = 5

    short_sma = indicators.simple_moving_average(prices, short_sma_window)
    long_sma = indicators.simple_moving_average(prices, long_sma_window)
    roc = indicators.rate_of_change(prices, trend_window)
    rsi = indicators.relative_strength_index(prices)

    action = "Hold"
    base_confidence = 0.2

    if short_sma is not None and long_sma is not None:
        delta = (short_sma - long_sma) / long_sma
        if delta > 0:
            action = "Buy"
            reasons.append(
                "Der kurzfristige gleitende Durchschnitt liegt über dem langfristigen, "
                "was auf einen Aufwärtstrend hindeutet."
            )
        elif delta < 0:
            action = "Sell"
            reasons.append(
                "Der kurzfristige gleitende Durchschnitt liegt unter dem langfristigen, "
                "was auf nachlassende Dynamik deutet."
            )
        base_confidence += min(abs(delta), 0.4)

    if roc is not None:
        if roc > 0:
            reasons.append(
                "Die letzten Schlusskurse steigen, die Dynamik ist positiv ("
                + _format_percentage(roc)
                + " in den letzten Tagen)."
            )
            base_confidence += min(roc, 0.2)
        else:
            reasons.append(
                "Die letzten Schlusskurse fallen, die Dynamik ist negativ ("
                + _format_percentage(roc)
                + " in den letzten Tagen)."
            )
            base_confidence += min(abs(roc), 0.2)
            if action == "Buy":
                action = "Hold"

    if rsi is not None:
        if rsi > 70:
            reasons.append(
                "Der RSI liegt über 70 und deutet auf eine überkaufte Situation hin."
            )
            if action == "Buy":
                action = "Hold"
        elif rsi < 30:
            reasons.append(
                "Der RSI liegt unter 30 und weist auf eine überverkaufte Situation hin."
            )
            if action == "Sell":
                action = "Hold"
        else:
            reasons.append("Der RSI bewegt sich in einer neutralen Zone.")

    confidence = min(max(base_confidence, 0.1), 0.95)

    if not reasons:
        reasons.append(
            "Nicht genügend Daten für eine klare Aussage – daher neutrale Empfehlung."
        )

    return Recommendation(
        asset=asset, action=action, confidence=confidence, reasons=reasons
    )
