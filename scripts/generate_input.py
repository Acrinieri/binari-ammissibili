"""Genera un payload JSON compatibile con POST /tracks/suggestions."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Dict


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
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    train_payload: Dict[str, object] = {
        "train_code": args.train_code,
        "train_length_m": args.train_length,
        "train_category": args.train_category,
        "planned_track": args.planned_track if args.planned_track else None,
        "is_prm": bool(args.is_prm),
    }

    payload = {"trains": [train_payload]}

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
