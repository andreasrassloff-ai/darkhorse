"""Utilities to run Darkhorse comfortably on a Raspberry Pi."""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path
from textwrap import dedent
from typing import Iterable
from wsgiref.simple_server import make_server

from .defaults import (
    DEFAULT_ASSET_NAME,
    DEFAULT_MINIMUM_HISTORY,
)
from .web import create_app

# A sensible default location for persistent data on a Raspberry Pi installation.
DEFAULT_PI_DATA_PATH = Path.home() / ".local/share/darkhorse/monero.json"
DEFAULT_PI_HOST = "0.0.0.0"
DEFAULT_PI_PORT = 8080


def _sample_data_file() -> Path:
    """Return the path to the bundled example data file."""

    package_root = Path(__file__).resolve().parent
    candidates = [
        package_root / "data" / "monero.json",
        package_root.parent / "data" / "monero.json",
    ]
    for candidate in candidates:
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        "Keine Beispieldaten gefunden. Bitte stellen Sie sicher, dass "
        "'data/monero.json' vorhanden ist."
    )


def _ensure_data_file(path: Path, *, overwrite: bool) -> Path:
    """Create *path* (or copy the sample data) when requested."""

    if path.is_dir():
        path = path / "monero.json"

    path.parent.mkdir(parents=True, exist_ok=True)

    if path.exists() and not overwrite:
        return path

    shutil.copyfile(_sample_data_file(), path)
    return path


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Hilfsprogramm, um Darkhorse auf einem Raspberry Pi als lokalen "
            "Dienst zu starten. Es kümmert sich um sinnvolle Standardwerte, "
            "bereitet bei Bedarf Beispieldaten vor und kann eine systemd-"
            "Unit-Vorlage ausgeben."
        )
    )
    parser.add_argument(
        "--host",
        default=DEFAULT_PI_HOST,
        help=(
            "Adresse, an die gebunden wird (Standard: "
            f"{DEFAULT_PI_HOST})."
        ),
    )
    parser.add_argument(
        "--port",
        type=int,
        default=DEFAULT_PI_PORT,
        help=f"Port für den Webserver (Standard: {DEFAULT_PI_PORT}).",
    )
    parser.add_argument(
        "--data",
        type=Path,
        default=DEFAULT_PI_DATA_PATH,
        help=(
            "Pfad zur JSON-Datei mit Monero-Kursdaten (Standard: "
            f"{DEFAULT_PI_DATA_PATH})."
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
    parser.add_argument(
        "--init-data",
        action="store_true",
        help=(
            "Legt die Zieldatei an und kopiert die Beispieldaten, falls sie "
            "noch nicht existiert."
        ),
    )
    parser.add_argument(
        "--force-data",
        action="store_true",
        help=(
            "Erzwingt das Überschreiben bestehender Daten (nur sinnvoll in "
            "Kombination mit --init-data)."
        ),
    )
    parser.add_argument(
        "--print-systemd",
        action="store_true",
        help="Gibt eine Beispiel-Konfigurationsdatei für systemd aus und beendet sich.",
    )
    return parser


def _render_systemd_unit(command: str, working_dir: Path) -> str:
    return dedent(
        f"""
        [Unit]
        Description=Darkhorse Monero Analyse
        After=network.target

        [Service]
        Type=simple
        WorkingDirectory={working_dir}
        ExecStart={command}
        Restart=on-failure
        RestartSec=5

        [Install]
        WantedBy=multi-user.target
        """
    ).strip()


def _format_command(args: argparse.Namespace) -> str:
    command_parts = [
        "/usr/bin/env",
        "python3",
        "-m",
        "darkhorse.pi",
        "--host",
        str(args.host),
        "--port",
        str(args.port),
        "--data",
        str(Path(args.data).expanduser()),
        "--min-history",
        str(args.min_history),
        "--asset-name",
        str(args.asset_name),
    ]
    return " ".join(command_parts)


def main(argv: Iterable[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.print_systemd:
        command = _format_command(args)
        unit = _render_systemd_unit(command, Path.cwd())
        print(unit)
        return 0

    data_path = Path(args.data)

    if args.init_data:
        try:
            data_path = _ensure_data_file(data_path, overwrite=args.force_data)
        except FileNotFoundError as exc:  # pragma: no cover - defensive branch
            parser.error(str(exc))
    else:
        if data_path.is_dir():
            data_path = data_path / "monero.json"
        if not data_path.exists():
            parser.error(
                f"Keine Kursdaten gefunden ({data_path}). Verwenden Sie --init-data, "
                "um die Beispieldatei anzulegen."
            )

    app = create_app(data_path, args.asset_name, args.min_history)

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


if __name__ == "__main__":  # pragma: no cover - module behaviour
    raise SystemExit(main())
