"""Utilities to interact with the tracks dataset."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List

from sqlalchemy.orm import Session

from .models import Track

DATA_FILE = Path(__file__).resolve().parent / "data" / "tracks.json"


class DatasetError(RuntimeError):
    """Raised when the dataset cannot be loaded."""


def ensure_tracks_seeded(session: Session) -> None:
    """Populate the database from the JSON file if the table is empty."""
    has_tracks = session.query(Track).first()
    if has_tracks:
        return

    if not DATA_FILE.exists():
        raise DatasetError(f"Dataset file not found: {DATA_FILE}")

    try:
        payload = json.loads(DATA_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise DatasetError(f"Invalid JSON in dataset file: {exc}") from exc

    tracks = payload.get("binari")
    if not isinstance(tracks, dict) or not tracks:
        raise DatasetError("Dataset file must contain a non-empty 'binari' object.")

    def _int(value: Any) -> int:
        try:
            return int(value)
        except (TypeError, ValueError):
            return 0

    for name, info in tracks.items():
        raw_capacity = info.get("capacita_funzionale_m")
        if raw_capacity in (None, ""):
            raw_capacity = info.get("capacita_funzioanle_m")
        if raw_capacity in (None, ""):
            cap_value = None
        else:
            cap_value = _int(raw_capacity)

        session.add(
            Track(
                name=name,
                marciapiede_complessivo_m=_int(info.get("marciapiede_complessivo_m")),
                marciapiede_alto_m=_int(info.get("marciapiede_alto_m")),
                marciapiede_basso_m=_int(info.get("marciapiede_basso_m")),
                capacita_funzionale_m=cap_value,
            )
        )
    session.commit()


def load_tracks_dataset(session: Session) -> Dict[str, Dict[str, Any]]:
    """Return the dataset as a dict keyed by track name."""
    result: Dict[str, Dict[str, Any]] = {}
    tracks: List[Track] = session.query(Track).order_by(Track.name).all()
    for track in tracks:
        result[track.name] = {
            "marciapiede_complessivo_m": track.marciapiede_complessivo_m,
            "marciapiede_alto_m": track.marciapiede_alto_m,
            "marciapiede_basso_m": track.marciapiede_basso_m,
            "capacita_funzionale_m": track.capacita_funzionale_m,
        }
    return result
