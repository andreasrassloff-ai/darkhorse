"""Simple web interface to inspect Monero prices and recommendations."""

from __future__ import annotations

import argparse
import html
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, List
from wsgiref.simple_server import make_server

from .data import load_price_history, most_recent_date, validate_enough_data
from .defaults import (
    DEFAULT_ASSET_NAME,
    DEFAULT_DATA_PATH,
    DEFAULT_HOST,
    DEFAULT_MINIMUM_HISTORY,
    DEFAULT_PORT,
)
from .recommender import Recommendation, analyse_asset


@dataclass(frozen=True)
class DisplayEntry:
    """Container for information rendered in the HTML page."""

    asset: str
    latest_date: datetime | None
    recommendation: Recommendation
    recent_bars: List[tuple[datetime, float]]


def _prepare_entry(
    data_path: Path, asset_name: str, minimum_history: int
) -> tuple[DisplayEntry | None, List[str]]:
    errors: list[str] = []

    try:
        history = load_price_history(data_path)
    except FileNotFoundError:
        errors.append(f"Keine Kursdaten gefunden – erwartete Datei {data_path}")
        return None, errors
    except ValueError as exc:
        errors.append(str(exc))
        return None, errors

    try:
        validate_enough_data(history, minimum_history)
    except ValueError as exc:
        errors.append(str(exc))
        return None, errors

    recommendation = analyse_asset(asset_name, history)
    latest = most_recent_date(history)
    recent = [(bar.date, bar.close) for bar in history[-10:]]

    entry = DisplayEntry(
        asset=asset_name,
        latest_date=latest,
        recommendation=recommendation,
        recent_bars=recent,
    )

    return entry, errors


def _format_date(value: datetime | None) -> str:
    if value is None:
        return "–"
    return value.date().isoformat()


def _render_html(entry: DisplayEntry | None, errors: List[str]) -> str:
    parts: list[str] = [
        "<!DOCTYPE html>",
        "<html lang='de'>",
        "<head>",
        "  <meta charset='utf-8'>",
        "  <title>Monero-Übersicht</title>",
        "  <style>",
        "    body { font-family: system-ui, sans-serif; margin: 2rem; background: #f5f5f5; color: #222; }",
        "    h1 { margin-bottom: 1rem; }",
        "    .card { background: white; border-radius: 0.75rem; padding: 1.5rem; box-shadow: 0 0.5rem 1.5rem rgba(0,0,0,0.08); max-width: 28rem; }",
        "    .card h2 { margin-top: 0; font-size: 1.4rem; }",
        "    .recommendation { font-weight: bold; margin: 0.5rem 0; }",
        "    .confidence { color: #666; font-size: 0.9rem; }",
        "    ul { padding-left: 1.2rem; }",
        "    table { width: 100%; border-collapse: collapse; margin-top: 1rem; font-size: 0.9rem; }",
        "    th, td { border-bottom: 1px solid #ddd; padding: 0.3rem 0.4rem; text-align: left; }",
        "    th { color: #555; font-weight: 600; }",
        "    .errors { background: #ffecec; border: 1px solid #f5a3a3; color: #a40000; padding: 1rem; border-radius: 0.75rem; margin-bottom: 1.5rem; max-width: 32rem; }",
        "  </style>",
        "</head>",
        "<body>",
        "  <h1>Monero-Kurs &amp; Empfehlung</h1>",
    ]

    if errors:
        parts.append("  <section class='errors'>")
        parts.append("    <h2>Fehler beim Laden</h2>")
        parts.append("    <ul>")
        for message in errors:
            parts.append(f"      <li>{html.escape(message)}</li>")
        parts.append("    </ul>")
        parts.append("  </section>")

    if entry is not None:
        recommendation = entry.recommendation
        parts.append("  <article class='card'>")
        parts.append(f"    <h2>{html.escape(entry.asset)}</h2>")
        parts.append(
            f"    <p class='recommendation'>Empfehlung: {html.escape(recommendation.action)} "
            f"<span class='confidence'>(Konfidenz {recommendation.confidence:.2f})</span></p>"
        )
        parts.append(f"    <p>Letzter Handelstag: {_format_date(entry.latest_date)}</p>")
        parts.append("    <h3>Begründungen</h3>")
        parts.append("    <ul>")
        for reason in recommendation.reasons:
            parts.append(f"      <li>{html.escape(reason)}</li>")
        parts.append("    </ul>")
        parts.append("    <h3>Letzte Schlusskurse</h3>")
        parts.append("    <table>")
        parts.append("      <thead><tr><th>Datum</th><th>Schluss</th></tr></thead>")
        parts.append("      <tbody>")
        for date_value, close in entry.recent_bars[::-1]:
            parts.append(
                "        <tr><td>"
                + html.escape(date_value.date().isoformat())
                + "</td><td>"
                + html.escape(f"{close:.2f}")
                + "</td></tr>"
            )
        parts.append("      </tbody>")
        parts.append("    </table>")
        parts.append("  </article>")

    parts.append("</body>")
    parts.append("</html>")

    return "\n".join(parts)


def create_app(data_path: Path, asset_name: str, minimum_history: int):
    """Create a WSGI application that renders the overview page."""

    data_path = Path(data_path)

    def app(environ, start_response):  # type: ignore[override]
        entry, errors = _prepare_entry(data_path, asset_name, minimum_history)
        html_body = _render_html(entry, errors)
        payload = html_body.encode("utf-8")

        start_response(
            "200 OK",
            [
                ("Content-Type", "text/html; charset=utf-8"),
                ("Content-Length", str(len(payload))),
            ],
        )
        return [payload]

    return app


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Startet einen kleinen Webserver, der den aktuellen Monero-Trend darstellt."
        )
    )
    parser.add_argument(
        "--host",
        default=DEFAULT_HOST,
        help=f"Adresse, an die gebunden wird (Standard: {DEFAULT_HOST})",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PORT,
        help=f"Port für den Webserver (Standard: {DEFAULT_PORT})",
    )
    parser.add_argument(
        "--data",
        type=Path,
        default=DEFAULT_DATA_PATH,
        help=(
            "Pfad zur JSON-Datei mit Monero-Kursdaten "
            f"(Standard: {DEFAULT_DATA_PATH})."
        ),
    )
    parser.add_argument(
        "--min-history",
        type=int,
        default=DEFAULT_MINIMUM_HISTORY,
        help=(
            "Minimale Anzahl an Handelstagen für eine Auswertung "
            f"(Standard: {DEFAULT_MINIMUM_HISTORY})."
        ),
    )
    parser.add_argument(
        "--asset-name",
        default=DEFAULT_ASSET_NAME,
        help=(
            "Anzeigename für das gehandelte Asset "
            f"(Standard: {DEFAULT_ASSET_NAME})."
        ),
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    app = create_app(Path(args.data), args.asset_name, args.min_history)

    with make_server(args.host, args.port, app) as server:
        print(
            "Server gestartet auf "
            f"http://{server.server_address[0]}:{server.server_address[1]} "
            "– drücken Sie Strg+C zum Beenden."
        )
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("Server wird beendet...")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
