"""Structured trading playbooks and risk guidelines for XMR/USDT daytrading."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

DISCLAIMER = "Hinweis: Keine Anlageberatung."

GENERAL_SETUP = {
    "markets": "XMR/USDT (Spot) oder Perpetuals; illiquide Paare meiden.",
    "timezone": "Europe/Berlin (CET/CEST).",
    "trading_windows": [
        "09:00–12:00 CET/CEST",
        "14:30–18:00 CET/CEST (hohe Liquidität zum US-Open)",
    ],
    "data_preparation": [
        "Kerzen: 1m, 3m, 5m und 15m (OHLCV).",
        "ATR(14) auf der jeweils genutzten Kerze als Volatilitätsfilter.",
        "EMA(50/200) als Trendfilter, sessionbasierter VWAP, RSI(14), Volumen-SMA(20).",
        "Gebühren & Slippage konservativ mit 0,10–0,20 % pro Roundtrip modellieren.",
        "Risk per Trade: 0,25–0,5 % des Kontos, Positionsgröße via Qty = (Konto * Risk%) / StopDistanz.",
    ],
}


@dataclass(frozen=True)
class Playbook:
    """Container for konkrete Trading-Regeln."""

    idea: str
    timeframe: str
    filters: Iterable[str]
    entry: Iterable[str]
    stop: Iterable[str]
    take_profit: Iterable[str]
    extra: Iterable[str] | None = None


PLAYBOOKS: dict[str, Playbook] = {
    "Momentum-Breakout": Playbook(
        idea=(
            "Ausbrüche mit Trendfilter und Volumenbestätigung handeln; eignet sich für"
            " intraday Trendfolge."
        ),
        timeframe="5m (optional 3m bei hoher Aktivität)",
        filters=[
            "Trend: EMA50 > EMA200 für Longs, EMA50 < EMA200 für Shorts.",
            "Volumen: Schlussvolumen > 1,5 × Volumen-SMA(20).",
            "Optional: ATR(14) über dem Median der letzten 50 Kerzen.",
        ],
        entry=[
            "Long: 5m-Close > Hoch der letzten 20 Kerzen + 0,1 × ATR(14).",
            "Short: 5m-Close < Tief der letzten 20 Kerzen − 0,1 × ATR(14).",
        ],
        stop=[
            "Initial: 1,5 × ATR(14) hinter dem Entry (bei Long unter Entry − 1,5 × ATR).",
            "Trailing: Chandelier Exit Highest(High,22) − 2,5 × ATR(22) (invertiert für Shorts).",
            "Alternative: Sobald R≥1 erreicht, mit 1,0 × ATR(14) trailen.",
        ],
        take_profit=[
            "Teilgewinn von 50 % bei R=1 sichern.",
            "Restposition via Trailing-Stop laufen lassen.",
            "Hard Max-Hold: 6–8 Stunden oder bis ein klarer VWAP-Bruch vorliegt.",
        ],
        extra=[
            "Abort-Regel: Wird der VWAP intraday deutlich gebrochen und schließen zwei"
            " Kerzen in Folge jenseits des VWAP, Position schließen.",
        ],
    ),
    "Mean-Reversion an VWAP": Playbook(
        idea=(
            "Kurzfristige Überdehnungen zurück zum VWAP spielen; ideal in seitwärts oder"
            " schwach trendenden Phasen."
        ),
        timeframe="1m–3m",
        filters=[
            "Schwacher Trend: |EMA50 − EMA200| / Preis < 0,5 %.",
            "Keine Trades 5 min vor bzw. 30 min nach wichtigen News (falls verfügbar).",
        ],
        entry=[
            "Long: Preis < VWAP − 1,0 × StdAbw(Preis vs. VWAP,20) und RSI(14) < 30",
            " sowie bullische Reversal-Kerze (z. B. 1m-Hammer oder 3m Bullish Engulfing).",
            "Short: Über VWAP mit RSI(14) > 70 analog handeln.",
        ],
        stop=[
            "Stop: 0,8 × ATR(14) unter Entry oder unter letztem Swing-Tief (engere Variante).",
        ],
        take_profit=[
            "Ziel 1: VWAP.",
            "Ziel 2: VWAP + 0,5 × StdAbw, falls Momentum anhält.",
            "Maximale Haltedauer 30–60 Minuten, keine Übernachtpositionen.",
        ],
    ),
    "Range-Break & Retest": Playbook(
        idea="Konservativer Ausbruchshandel nach bestätigtem Retest.",
        timeframe="5m–15m",
        filters=[
            "Range der letzten 40 Kerzen: High_R = Höchstes Hoch, Low_R = Tiefstes Tief.",
        ],
        entry=[
            "Long: 5m-Close > High_R, anschließend Retest auf High_R ± 0,1 × ATR(14)"
            " mit bullischer Reaktionskerze.",
            "Short: Analoge Logik am unteren Range-Rand.",
        ],
        stop=[
            "1,2 × ATR(14) hinter dem Ausbruchsniveau (nicht hinter dem Entry).",
            "Alternativ: Stop unter/über der Retest-Kerze.",
        ],
        take_profit=[
            "TP1 = 1 × ATR(14).",
            "TP2 = 2 × ATR(14).",
            "Restposition schließen, falls der Kurs gegen den Trend unter die EMA50 fällt.",
        ],
        extra=[
            "Fehlausbruchfilter: Keine Trades, wenn die Durchbruchskerze weniger als"
            " 0,5 × ATR(14) Range abdeckt.",
        ],
    ),
    "Trend-Pullback mit RSI-Shift": Playbook(
        idea="Trendanpassung nach Pullbacks in etablierten Trends.",
        timeframe="5m",
        filters=[
            "Starker Trend: EMA50 klar über/unter EMA200.",
            "Preis muss über EMA50 (Long) bzw. darunter (Short) notieren.",
            "RSI-Regime: Aufwärtstrends mit RSI-Floor 40–50, Abwärtstrends mit RSI-Cap 50–60.",
        ],
        entry=[
            "Pullback bis EMA50 oder 38,2–61,8 % Fibonacci des letzten Impulsschwungs.",
            "RSI(14) springt wieder über 50 (Long) bzw. unter 50 (Short).",
            "Schlusskurs schließt zurück über die EMA50 (Long) bzw. darunter (Short).",
        ],
        stop=[
            "Unter dem Pullback-Tief oder 1,0 × ATR(14) – jeweils die engere Variante.",
        ],
        take_profit=[
            "TP1 am letzten Swing-Hoch/Swing-Tief.",
            "TP2 über Parabolic SAR (Step 0,02, Max 0,2) oder einfachen 1 × ATR-Trailing-Stop.",
        ],
    ),
}

RISK_AND_SESSION_RULES = {
    "max_positions": "Maximal 1–2 gleichzeitige Positionen; Korrelation beachten.",
    "max_daily_loss": "Handel nach −1,5 % Tagesverlust stoppen.",
    "max_trades": "Maximal 5–8 Trades pro Tag, um Overtrading zu vermeiden.",
    "spread_limit": "Nicht handeln, wenn Spread/Preis > 0,05 %.",
    "volatility_filter": "Handel pausieren, falls ATR(14,5m) unter das 20. Perzentil der letzten 30 Tage fällt.",
    "news_filter": "News-Sperre: 5 min vor und 30 min nach Ereignissen; alternativ große 1m-Kerzen (>2 × ATR) meiden.",
    "data_quality": "Kerzen mit Volumen 0 ignorieren und Ausreißer winsorizen.",
}

BACKTEST_REQUIREMENTS = {
    "net_return": "Netto-Rendite nach Kosten ≥ 1,5 × tägliche Strategie-Volatilität.",
    "profit_factor": "Profitfaktor ≥ 1,3, täglicher Sharpe ≥ 1,0, maximaler Drawdown < 10 % (Paper).",
    "payoff_ratio": "Durchschnittlicher Gewinner / Verlierer ≥ 1,5; Trefferquote zweitrangig.",
    "slippage": "Zusätzliche Slippage von 0,05–0,10 % pro Trade simulieren.",
    "robustness": "Walk-Forward-Test (z. B. 3 Monate Training, 1 Monat Test) und Parameter ±20 % prüfen.",
}

API_FIELD_SUGGESTIONS = {
    "symbol": "XMRUSDT",
    "timeframes": "1m | 3m | 5m | 15m",
    "indicators": "ATR14, EMA50, EMA200, RSI14, Volumen-SMA20, sessionbasierter VWAP",
    "trade_params": "risk_pct, atr_mult_stop, atr_mult_entry_buffer, vol_mult, r_targets, max_daily_loss_pct, max_trades",
    "session_times": "Start/End inklusive Pausenfenster (CET/CEST).",
    "filters": "spread_max_pct, atr_min_threshold, trend_required (bool).",
    "example_default": (
        '{\n  "symbol": "XMRUSDT",\n  "timeframe": "5m",\n  "indicators": {"ATR": 14, '
        '"EMA_fast": 50, "EMA_slow": 200, "RSI": 14, "VolSMA": 20, "VWAP": "session"},\n'
        '  "filters": {"trend": "EMA50>EMA200", "vol_mult": 1.5, "atr_min_quantile": 0.2, '
        '"spread_max_pct": 0.05},\n  "entries": {"break_lookback": 20, "atr_buffer": 0.1},\n'
        '  "stops": {"atr_mult": 1.5},\n  "targets": {"tp1_R": 1.0, "tp2_R": 2.0, "trail": "ATR1.0"},\n'
        '  "risk": {"per_trade_pct": 0.003, "max_daily_loss_pct": 0.015, "max_trades": 6},\n'
        '  "sessions": [{"start": "09:00", "end": "12:00"}, {"start": "14:30", "end": "18:00"}],\n'
        '  "exit_rules": {"vwap_break_close_bars": 2, "max_hold_hours": 8}\n}'
    ),
}

ONBOARDING_STEPS = [
    "Playbook auswählen (z. B. Momentum-Breakout 5m).",
    "3–6 Monate Backtest mit realistischen Gebühren & Slippage durchführen.",
    "Top-2 Parameter-Varianten (z. B. atr_buffer 0,05–0,15; atr_stop 1,3–1,7) behalten.",
    "Strategie 2–4 Wochen papertraden, erst danach mit kleinen Größen live gehen.",
    "Alle relevanten Metriken loggen: Zeit, Spread, ATR, Volumen, Regime-Flags, Exit-Gründe.",
]


def format_playbook(name: str) -> str:
    playbook = PLAYBOOKS[name]
    lines: list[str] = [name, "-" * len(name), f"Idee: {playbook.idea}", f"Zeiteinheit: {playbook.timeframe}"]

    def _format_block(title: str, items: Iterable[str]) -> None:
        lines.append(f"{title}:")
        for item in items:
            lines.append(f"  - {item}")

    _format_block("Filter", playbook.filters)
    _format_block("Entry", playbook.entry)
    _format_block("Stop", playbook.stop)
    _format_block("Take-Profit", playbook.take_profit)
    if playbook.extra:
        _format_block("Zusatzregeln", playbook.extra)

    return "\n".join(lines)


def format_guidelines() -> str:
    """Return a readable representation of all trading hints."""

    sections: list[str] = [DISCLAIMER, ""]

    sections.append("Grundsetup")
    sections.append("=" * len("Grundsetup"))
    sections.append(f"Märkte: {GENERAL_SETUP['markets']}")
    sections.append(f"Zeitzone: {GENERAL_SETUP['timezone']}")
    sections.append("Handelsfenster:")
    for window in GENERAL_SETUP["trading_windows"]:
        sections.append(f"  - {window}")
    sections.append("Datenaufbereitung & Risiko:")
    for line in GENERAL_SETUP["data_preparation"]:
        sections.append(f"  - {line}")
    sections.append("")

    sections.append("Playbooks")
    sections.append("=" * len("Playbooks"))
    for name in PLAYBOOKS:
        sections.append(format_playbook(name))
        sections.append("")

    sections.append("Risiko- & Session-Parameter")
    sections.append("=" * len("Risiko- & Session-Parameter"))
    for value in RISK_AND_SESSION_RULES.values():
        sections.append(f"- {value}")
    sections.append("")

    sections.append("Backtesting-Metriken & Mindestanforderungen")
    sections.append("=" * len("Backtesting-Metriken & Mindestanforderungen"))
    for value in BACKTEST_REQUIREMENTS.values():
        sections.append(f"- {value}")
    sections.append("")

    sections.append("API-Felder für die App")
    sections.append("=" * len("API-Felder für die App"))
    for key, value in API_FIELD_SUGGESTIONS.items():
        if key == "example_default":
            sections.append("Beispiel-Default:")
            sections.append(value)
        else:
            sections.append(f"- {value}")
    sections.append("")

    sections.append("Pragmatischer Start")
    sections.append("=" * len("Pragmatischer Start"))
    for step in ONBOARDING_STEPS:
        sections.append(f"- {step}")

    return "\n".join(sections).rstrip() + "\n"


def print_guidelines() -> None:
    """Print all trading guidelines in a human-readable form."""

    print(format_guidelines())


__all__ = [
    "DISCLAIMER",
    "GENERAL_SETUP",
    "PLAYBOOKS",
    "RISK_AND_SESSION_RULES",
    "BACKTEST_REQUIREMENTS",
    "API_FIELD_SUGGESTIONS",
    "ONBOARDING_STEPS",
    "format_guidelines",
    "format_playbook",
    "print_guidelines",
]
