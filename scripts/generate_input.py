"""Genera un payload JSON compatibile con POST /tracks/suggestions."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Optional


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Crea un file JSON per l'endpoint /tracks/suggestions."
    )
    parser.add_argument(
        "--output",
        required=True,
        help="Percorso dove salvare il JSON prodotto.",
    )
    parser.add_argument(
        "--train-code",
        required=True,
        help="Codice treno da fornire al backend.",
    )
    parser.add_argument(
        "--train-length",
        type=float,
        required=True,
        help="Lunghezza del treno in metri.",
    )
    parser.add_argument(
        "--train-category",
        default="REG",
        help="Categoria del treno (default: REG).",
    )
    parser.add_argument(
        "--planned-track",
        help="Binario previsto (opzionale).",
    )
    parser.add_argument(
        "--is-prm",
        action="store_true",
        help="Imposta il flag PRM.",
    )
    parser.add_argument(
        "--tracks-override-file",
        help="Percorso a un JSON con dataset custom da usare come tracks_override.",
    )
    return parser


def load_tracks_override(path: Optional[str]) -> Optional[Dict[str, Any]]:
    if not path:
        return None
    source = Path(path)
    if not source.is_file():
        raise FileNotFoundError(f"tracks_override file non trovato: {source}")
    try:
        with source.open("r", encoding="utf-8") as handle:
            data = json.load(handle)
    except json.JSONDecodeError as exc:
        raise ValueError(f"tracks_override non valido ({source}): {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("tracks_override deve essere un oggetto JSON")
    return data


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    payload: Dict[str, Any] = {
        "train_code": args.train_code,
        "train_length_m": args.train_length,
        "train_category": args.train_category,
        "planned_track": args.planned_track if args.planned_track else None,
        "is_prm": bool(args.is_prm),
    }

    tracks_override = load_tracks_override(args.tracks_override_file)
    if tracks_override is not None:
        payload["tracks_override"] = tracks_override

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
