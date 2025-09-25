"""Indicator calculations used for the recommendation engine."""

from __future__ import annotations

from collections import deque
from typing import Iterable, List, Sequence


def simple_moving_average(values: Sequence[float], window: int) -> float | None:
    if len(values) < window or window <= 0:
        return None
    return sum(values[-window:]) / window


def exponential_moving_average(values: Sequence[float], window: int) -> float | None:
    if len(values) < window or window <= 0:
        return None
    k = 2 / (window + 1)
    ema = values[0]
    for price in values[1:]:
        ema = price * k + ema * (1 - k)
    return ema


def rate_of_change(values: Sequence[float], window: int) -> float | None:
    if len(values) <= window or window <= 0:
        return None
    past = values[-window - 1]
    if past == 0:
        return None
    return (values[-1] - past) / past


def relative_strength_index(values: Sequence[float], period: int = 14) -> float | None:
    if len(values) <= period:
        return None

    gains = 0.0
    losses = 0.0
    for prev, current in zip(values[-period - 1 : -1], values[-period:]):
        change = current - prev
        if change > 0:
            gains += change
        else:
            losses -= change

    if losses == 0:
        return 100.0

    rs = gains / losses
    return 100 - (100 / (1 + rs))

