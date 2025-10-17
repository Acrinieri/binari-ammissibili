from __future__ import annotations

from typing import Dict, Iterable, Mapping, Tuple

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..constants import DEFAULT_SIGNAL_CODE, TRACK_SIGNAL_MAP
from ..models import Track

_NORMALISED_SIGNAL_MAP: Mapping[str, str] = {
    key.strip().upper(): value for key, value in TRACK_SIGNAL_MAP.items()
}


def resolve_signal_code(name: str) -> str:
    """Return the signal code for the given track name."""
    if not name:
        return DEFAULT_SIGNAL_CODE
    return _NORMALISED_SIGNAL_MAP.get(name.strip().upper(), DEFAULT_SIGNAL_CODE)


def ensure_signal_code_column(session: Session) -> None:
    """Ensure the tracks table has the signal_code column (SQLite ALTER if needed)."""
    result = session.execute(text("PRAGMA table_info(tracks)"))
    columns = {row[1] for row in result}
    if "signal_code" not in columns:
        session.execute(text("ALTER TABLE tracks ADD COLUMN signal_code VARCHAR(16)"))
        session.commit()


def apply_signal_code_defaults(session: Session, track_names: Iterable[str] | None = None) -> None:
    """Populate missing signal codes based on the configured mapping."""
    query = session.query(Track)
    if track_names:
        query = query.filter(Track.name.in_(track_names))
    dirty = False
    for track in query.all():
        desired = resolve_signal_code(track.name)
        if not track.signal_code or track.signal_code == DEFAULT_SIGNAL_CODE or track.signal_code.strip() == "":
            if track.signal_code != desired:
                track.signal_code = desired
                dirty = True
    if dirty:
        session.commit()


def normalise_signal_string(value: str | None) -> Tuple[str, bool]:
    if value is None:
        return "", False
    raw = str(value).strip()
    if not raw:
        return "", False
    has_suffix = raw.lower().endswith("f")
    core = raw[:-1] if has_suffix else raw
    return core.strip().upper(), has_suffix


def build_signal_lookup(dataset: Mapping[str, Mapping[str, object]]) -> Dict[str, str]:
    lookup: Dict[str, str] = {}
    for name, info in dataset.items():
        signal = info.get("signal_code")
        if signal is None:
            continue
        signal_str = str(signal).strip()
        if signal_str:
            lookup[signal_str.upper()] = name
    return lookup


def signal_for_track(dataset: Mapping[str, Mapping[str, object]], track_name: str) -> str:
    info = dataset.get(track_name) or {}
    signal = info.get("signal_code")
    if signal is None:
        return DEFAULT_SIGNAL_CODE
    signal_str = str(signal).strip()
    return signal_str if signal_str else DEFAULT_SIGNAL_CODE


def format_signal_output(signal: str, append_suffix: bool) -> str:
    if not signal:
        return DEFAULT_SIGNAL_CODE
    signal_str = str(signal).strip()
    if not signal_str:
        return DEFAULT_SIGNAL_CODE
    if append_suffix and signal_str.upper() != DEFAULT_SIGNAL_CODE:
        return f"{signal_str}f"
    return signal_str
