"""Utility CLI per automatizzare il flusso JSON → API → destinazione.

Esempio d'uso:
    python -m scripts.json_pipeline \
        --input data/input.json \
        --api-url http://127.0.0.1:8000/tracks/suggestions \
        --forward-url https://example.com/consumer-endpoint
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, Optional

import requests

DEFAULT_API_URL = "http://127.0.0.1:8000/tracks/suggestions"


def load_json(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"File di input non trovato: {path}")
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except json.JSONDecodeError as exc:
        raise ValueError(f"JSON di input non valido ({path}): {exc}") from exc


def call_api(payload: Dict[str, Any], api_url: str, timeout: float) -> Dict[str, Any]:
    response = requests.post(api_url, json=payload, timeout=timeout)
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        detail = response.text[:500]
        raise RuntimeError(
            f"Chiamata API fallita ({response.status_code}): {detail}"
        ) from exc
    try:
        return response.json()
    except ValueError as exc:
        raise RuntimeError("Risposta dell'API non è JSON valido") from exc


def forward_output(
    data: Dict[str, Any],
    forward_url: Optional[str],
    output_path: Optional[Path],
    timeout: float,
) -> None:
    if forward_url:
        response = requests.post(forward_url, json=data, timeout=timeout)
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            detail = response.text[:500]
            raise RuntimeError(
                f"Inoltro fallito ({response.status_code}): {detail}"
            ) from exc
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with output_path.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Automatizza l'invio di un JSON all'API delle alternative e l'inoltro della risposta."
    )
    parser.add_argument(
        "--input",
        required=True,
        help="Percorso del file JSON di input da inviare all'API.",
    )
    parser.add_argument(
        "--api-url",
        default=DEFAULT_API_URL,
        help=f"Endpoint dell'API FastAPI. Default: {DEFAULT_API_URL}",
    )
    parser.add_argument(
        "--forward-url",
        help="Endpoint della seconda applicazione a cui inoltrare il JSON di risposta (POST).",
    )
    parser.add_argument(
        "--output-path",
        help="Percorso file dove salvare la risposta JSON (opzionale, utile per audit).",
    )
    parser.add_argument(
        "--timeout",
        type=float,
        default=10.0,
        help="Timeout (secondi) per le chiamate HTTP.",
    )
    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output_path) if args.output_path else None

    payload = load_json(input_path)
    response_data = call_api(payload, args.api_url, timeout=args.timeout)
    forward_output(response_data, args.forward_url, output_path, timeout=args.timeout)


if __name__ == "__main__":
    main()
