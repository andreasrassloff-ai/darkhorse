
"""Compatibility wrapper exposing :mod:`darkhorse.web`."""

from __future__ import annotations

from darkhorse.web import *  # noqa: F401,F403


if __name__ == "__main__":
    from darkhorse.web import main as _main

    raise SystemExit(_main())
=======
"""Simple web interface to inspect prices and recommendations."""

from __future__ import annotations

import argparse
import html
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Sequence
from urllib.parse import parse_qs
from wsgiref.simple_server import make_server

from .data import load_price_history, most_recent_date, validate_enough_data
from .recommender import Recommendation, analyse_stock
from .specs import WknSpec, collect_specs, parse_wkn_argument


@dataclass(frozen=True)
class DisplayEntry:
    """Container for information rendered in the HTML page."""

    wkn: str
    latest_date: datetime | None
    recommendation: Recommendation
    recent_bars: List[tuple[datetime, float]]


def _prepare_entries(specs: Sequence[WknSpec], minimum_history: int) -> tuple[List[DisplayEntry], List[str]]:
    entries: list[DisplayEntry] = []
    errors: list[str] = []

    for wkn, path in specs:
        try:
            history = load_price_history(path)
            validate_enough_data(history, minimum_history)
            recommendation = analyse_stock(wkn, history)
        except FileNotFoundError:
            errors.append(f"{wkn}: Keine Kursdaten gefunden – erwartete Datei {path}")
            continue
        except ValueError as exc:
            errors.append(f"{wkn}: {exc}")
            continue

        latest = most_recent_date(history)
        recent = [(bar.date, bar.close) for bar in history[-10:]]
        entries.append(
            DisplayEntry(
                wkn=wkn,
                latest_date=latest,
                recommendation=recommendation,
                recent_bars=recent,
            )
        )

    entries.sort(key=lambda entry: entry.wkn)
    return entries, errors


def _format_date(value: datetime | None) -> str:
    if value is None:
        return "–"
    return value.date().isoformat()


def _render_html(entries: Sequence[DisplayEntry], errors: Sequence[str]) -> str:
    parts: list[str] = [
        "<!DOCTYPE html>",
        "<html lang='de'>",
        "<head>",
        "  <meta charset='utf-8'>",
        "  <title>Aktienübersicht</title>",
        "  <style>",
        "    body { font-family: system-ui, sans-serif; margin: 2rem; background: #f5f5f5; color: #222; }",
        "    h1 { margin-bottom: 1rem; }",
        "    .grid { display: grid; gap: 1.5rem; grid-template-columns: repeat(auto-fit, minmax(22rem, 1fr)); }",
        "    .card { background: white; border-radius: 0.75rem; padding: 1.5rem; box-shadow: 0 0.5rem 1.5rem rgba(0,0,0,0.08); }",
        "    .card h2 { margin-top: 0; font-size: 1.3rem; }",
        "    .recommendation { font-weight: bold; margin: 0.5rem 0; }",
        "    .confidence { color: #666; font-size: 0.9rem; }",
        "    ul { padding-left: 1.2rem; }",
        "    table { width: 100%; border-collapse: collapse; margin-top: 1rem; font-size: 0.9rem; }",
        "    th, td { border-bottom: 1px solid #ddd; padding: 0.3rem 0.4rem; text-align: left; }",
        "    th { color: #555; font-weight: 600; }",
        "    .errors { background: #ffecec; border: 1px solid #f5a3a3; color: #a40000; padding: 1rem; border-radius: 0.75rem; margin-bottom: 1.5rem; }",
        "  </style>",
        "</head>",
        "<body>",
        "  <h1>Kurse &amp; Empfehlungen</h1>",
    ]

    if errors:
        parts.append("  <section class='errors'>")
        parts.append("    <h2>Fehler beim Laden</h2>")
        parts.append("    <ul>")
        for message in errors:
            parts.append(f"      <li>{html.escape(message)}</li>")
        parts.append("    </ul>")
        parts.append("  </section>")

    parts.append("  <section class='grid'>")
    for entry in entries:
        recommendation = entry.recommendation
        parts.append("    <article class='card'>")
        parts.append(f"      <h2>{html.escape(entry.wkn)}</h2>")
        parts.append(
            f"      <p class='recommendation'>Empfehlung: {html.escape(recommendation.action)} "
            f"<span class='confidence'>(Konfidenz {recommendation.confidence:.2f})</span></p>"
        )
        parts.append(f"      <p>Letzter Handelstag: {_format_date(entry.latest_date)}</p>")
        parts.append("      <h3>Begründungen</h3>")
        parts.append("      <ul>")
        for reason in recommendation.reasons:
            parts.append(f"        <li>{html.escape(reason)}</li>")
        parts.append("      </ul>")
        parts.append("      <h3>Letzte Schlusskurse</h3>")
        parts.append("      <table>")
        parts.append("        <thead><tr><th>Datum</th><th>Schluss</th></tr></thead>")
        parts.append("        <tbody>")
        for date_value, close in entry.recent_bars[::-1]:
            parts.append(
                "          <tr><td>"
                + html.escape(date_value.date().isoformat())
                + "</td><td>"
                + html.escape(f"{close:.2f}")
                + "</td></tr>"
            )
        parts.append("        </tbody>")
        parts.append("      </table>")
        parts.append("    </article>")
    parts.append("  </section>")
    parts.append("</body>")
    parts.append("</html>")

    return "\n".join(parts)


def create_app(default_specs: Sequence[WknSpec], minimum_history: int):
    """Create a WSGI application that renders the overview page."""

    default_specs = list(default_specs)

    def app(environ, start_response):  # type: ignore[override]
        query = parse_qs(environ.get("QUERY_STRING", ""))
        if "wkn" in query:
            specs: list[WknSpec] = []
            for raw in query.get("wkn", []):
                if raw:
                    specs.append(parse_wkn_argument(raw))
        else:
            specs = list(default_specs)

        entries, errors = _prepare_entries(specs, minimum_history)
        html_body = _render_html(entries, errors)
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
            "Startet einen kleinen Webserver, der Kurse und Empfehlungen für die "
            "angegebenen Wertpapiere anzeigt."
        )
    )
    parser.add_argument("--host", default="127.0.0.1", help="Adresse, an die gebunden wird (Standard: 127.0.0.1)")
    parser.add_argument("--port", type=int, default=8000, help="Port für den Webserver (Standard: 8000)")
    parser.add_argument(
        "--wkn",
        action="append",
        help=(
            "Wertpapierkennnummer mit optionalem Pfad zur JSON-Datei. "
            "Beispiel: DE0001234567=data/meine_daten.json. Ohne Pfad wird data/<WKN>.json erwartet."
        ),
    )
    parser.add_argument(
        "--watchlist",
        type=Path,
        help=(
            "Pfad zu einer JSON-Datei mit mehreren WKN-Einträgen. Einträge können als Liste von Strings oder Objekten mit den "
            "Schlüsseln 'wkn' und optional 'path' angegeben werden."
        ),
    )
    parser.add_argument(
        "--min-history",
        type=int,
        default=60,
        help="Minimale Anzahl an Handelstagen für eine Auswertung (Standard: 60).",
    )
    return parser


def main(argv: Iterable[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        specs = collect_specs(args.wkn, args.watchlist)
    except FileNotFoundError:
        parser.error(f"Watchlist-Datei {args.watchlist} wurde nicht gefunden.")
    except ValueError as exc:
        parser.error(str(exc))
        return 2

    if not specs:
        parser.error(
            "Es wurde keine WKN angegeben. Verwenden Sie --wkn oder --watchlist."
        )
        return 2

    app = create_app(specs, args.min_history)

    with make_server(args.host, args.port, app) as server:
        print(
            f"Server gestartet auf http://{server.server_address[0]}:{server.server_address[1]} "
            "– drücken Sie Strg+C zum Beenden."
        )
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            print("Server wird beendet...")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

