"""Core logic for computing admissible tracks based on the provided ruleset."""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Any, Dict, List, NamedTuple, Optional, Tuple

logger = logging.getLogger(__name__)

TrackDataset = Dict[str, Dict[str, Any]]

ROMAN = {
    "I": 1,
    "II": 2,
    "III": 3,
    "IV": 4,
    "V": 5,
    "VI": 6,
    "VII": 7,
    "VIII": 8,
    "IX": 9,
    "X": 10,
    "XI": 11,
    "XII": 12,
    "XIII": 13,
    "XIV": 14,
    "XV": 15,
    "XVI": 16,
    "XVII": 17,
    "XVIII": 18,
    "XIX": 19,
    "XX": 20,
    "XXI": 21,
    "XXII": 22,
    "XXIII": 23,
    "XXIV": 24,
    "XXV": 25,
}

LH_CATEGORIES = {
    "LH",
    "EC",
    "EN",
    "IC",
    "ICN",
    "EXP",
    "NCL",
    "ES*",
    "FR",
    "FA",
    "FB",
    "NTV",
}


class TrackMetadata(NamedTuple):
    num: Optional[int]
    suffix: str
    len_compl: int
    cap_fun: int


@dataclass(frozen=True)
class CandidateRecord:
    name: str
    priority_class: int
    proximity: float
    neg_similarity: int
    same_number_bonus: int
    len_delta: int
    sort_num: float
    suffix_flag: int
    similarity: int
    len_compl: int
    cap_fun: int
    num: Optional[int]
    suffix: str


def _is_lh(train_type: Optional[str]) -> bool:
    """Return True when the train type belongs to long-distance classes."""
    return (train_type or "").upper().strip() in LH_CATEGORIES


def _parse_track_name(name: str) -> Tuple[Optional[int], str, str]:
    """
    Normalise and split a track name.

    Returns a tuple (number, suffix, normalised_name).
    """
    if not isinstance(name, str):
        return None, "", ""
    normalised = " ".join(name.strip().upper().split())
    if not normalised:
        return None, "", ""
    parts = normalised.split()
    first = parts[0]
    number = int(first) if first.isdigit() else ROMAN.get(first)
    suffix = parts[1] if len(parts) > 1 else ""
    return number, suffix, normalised


def _class_matches_es_star(train_type: str) -> bool:
    """True when the class is ES or ES*."""
    tt = (train_type or "").upper().strip()
    return tt in {"ES", "ES*"}


def _profile_tuple(info: Dict[str, Any]) -> Tuple[int, int]:
    """Return (high_platform_flag, low_platform_flag) for the track."""
    high = 1 if (info.get("marciapiede_alto_m") or 0) > 0 else 0
    low = 1 if (info.get("marciapiede_basso_m") or 0) > 0 else 0
    return high, low


def _track_similarity_score(
    candidate_info: Dict[str, Any],
    planned_info: Optional[Dict[str, Any]],
) -> int:
    """Score similarity with the planned track."""
    if not planned_info:
        return 0
    score = 0
    candidate_len = candidate_info.get("marciapiede_complessivo_m") or 0
    planned_len = planned_info.get("marciapiede_complessivo_m") or 0
    if candidate_len > 0 and candidate_len == planned_len:
        score += 2
    if _profile_tuple(candidate_info) == _profile_tuple(planned_info):
        score += 1
    return score


def _priority_class(train_type: str, num: Optional[int]) -> int:
    """
    Long distance trains prefer tracks 2-13.
    Tracks 1 and 14 are second choice. Others are excluded earlier.
    """
    if _is_lh(train_type) and isinstance(num, int):
        return 0 if 2 <= num <= 13 else 1
    return 0


def _proximity_rank(
    candidate_num: Optional[int],
    candidate_suffix: str,
    planned_num: Optional[int],
    planned_suffix: str,
) -> float:
    """Distance metric between track numbers."""
    if candidate_num is None or planned_num is None:
        return math.inf
    if candidate_num == planned_num and candidate_suffix != planned_suffix:
        return 1
    return abs(candidate_num - planned_num)


def _normalise_capacity(info: Dict[str, Any]) -> int:
    """Return the functional capacity length handling common typos."""
    value = (
        info.get("capacita_funzionale_m")
        or info.get("capacita_funzionle_m")
        or 0
    )
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _validate_track_data(track_name: str, info: Dict[str, Any]) -> bool:
    """Ensure required fields are present and numeric."""
    value = info.get("marciapiede_complessivo_m")
    if value is None:
        logger.warning(
            "Track '%s' missing 'marciapiede_complessivo_m'. It will be ignored.",
            track_name,
        )
        return False
    try:
        int(value)
    except (TypeError, ValueError):
        logger.warning(
            "Track '%s' has non-numeric 'marciapiede_complessivo_m': %r",
            track_name,
            value,
        )
        return False
    return True


def _build_track_metadata(tracks: TrackDataset) -> Dict[str, TrackMetadata]:
    """Construct cached metadata per track."""
    track_meta: Dict[str, TrackMetadata] = {}
    for name, info in tracks.items():
        if not _validate_track_data(name, info):
            continue
        num, suffix, normalised = _parse_track_name(name)
        len_compl = int(info.get("marciapiede_complessivo_m") or 0)
        cap_fun = _normalise_capacity(info)
        track_meta[normalised] = TrackMetadata(num, suffix, len_compl, cap_fun)
    return track_meta


def _resolve_planned_track(
    planned_track: Optional[str],
    track_meta: Dict[str, TrackMetadata],
    tracks: TrackDataset,
) -> Tuple[Optional[int], str, Optional[Dict[str, Any]]]:
    """Find the planned track and its info."""
    if not planned_track:
        return None, "", None

    planned_num, planned_suffix, planned_norm = _parse_track_name(planned_track)
    lookup = {
        (meta.num, meta.suffix): norm_name for norm_name, meta in track_meta.items()
    }
    resolved_norm = lookup.get((planned_num, planned_suffix), planned_norm)
    planned_info = tracks.get(resolved_norm)
    if not planned_info:
        logger.warning(
            "Planned track '%s' not found in dataset. Proximity scoring disabled.",
            planned_track,
        )
    return planned_num, planned_suffix or "", planned_info


def _is_track_excluded(
    norm_name: str,
    num: Optional[int],
    suffix: str,
    train_type: str,
    is_inv: bool,
    planned_num: Optional[int],
    planned_suffix: str,
) -> bool:
    """Check exclusion rules before ranking."""
    if norm_name == "SSE AMB.":
        return True

    if planned_num is not None and num == planned_num and suffix == planned_suffix:
        return True

    if suffix == "BIS" and not is_inv:
        return True

    if train_type == "PRM" and (
        norm_name == "I NORD" or (num == 1 and " NORD" in norm_name)
    ):
        return True

    if _class_matches_es_star(train_type) and num == 15:
        return True

    if _is_lh(train_type):
        if not (isinstance(num, int) and 1 <= num <= 14):
            return True

    return False


def _meets_length_requirements(
    len_compl: int,
    cap_fun: int,
    train_length: int,
    is_inv: bool,
) -> bool:
    """Check length and capacity requirements."""
    if not is_inv and len_compl <= 0:
        return False

    if is_inv:
        if cap_fun > 0:
            return cap_fun >= train_length
        return len_compl == 0 or len_compl >= train_length

    return len_compl >= train_length


def _build_candidate_record(
    norm_name: str,
    meta: TrackMetadata,
    train_type: str,
    planned_num: Optional[int],
    planned_suffix: str,
    planned_info: Optional[Dict[str, Any]],
    tracks: TrackDataset,
) -> CandidateRecord:
    """Produce the sorting tuple and metadata for a candidate track."""
    prox = _proximity_rank(meta.num, meta.suffix, planned_num, planned_suffix)
    cand_info = tracks.get(norm_name, {})
    sim = _track_similarity_score(cand_info, planned_info)
    planned_len = (
        int(planned_info.get("marciapiede_complessivo_m") or 0)
        if planned_info
        else 0
    )
    len_delta = abs((planned_len or meta.len_compl) - meta.len_compl)
    pclass = _priority_class(train_type, meta.num)
    sort_num = float(meta.num) if isinstance(meta.num, int) else math.inf
    suffix_flag = 1 if meta.suffix else 0
    same_number_bonus = (
        -1
        if (planned_num is not None and meta.num == planned_num and meta.suffix != planned_suffix)
        else 0
    )
    return CandidateRecord(
        name=norm_name,
        priority_class=pclass,
        proximity=prox,
        neg_similarity=-sim,
        same_number_bonus=same_number_bonus,
        len_delta=len_delta,
        sort_num=sort_num,
        suffix_flag=suffix_flag,
        similarity=sim,
        len_compl=meta.len_compl,
        cap_fun=meta.cap_fun,
        num=meta.num,
        suffix=meta.suffix,
    )


def _build_reason(
    record: CandidateRecord,
    train_type: str,
    train_length_m: int,
    planned_num: Optional[int],
    planned_suffix: str,
    planned_info: Optional[Dict[str, Any]],
    tracks: TrackDataset,
) -> str:
    """Produce a human-readable explanation for the suggested track."""
    parts: List[str] = []
    info = tracks.get(record.name, {})

    if train_type == "INV":
        if record.len_compl == 0:
            parts.append("Nessun marciapiede disponibile: priorita per treni INV.")
        else:
            parts.append(
                f"Marciapiede da {record.len_compl} m compatibile con la categoria INV."
            )
        if record.cap_fun > 0:
            parts.append(
                f"Capacita funzionale {record.cap_fun} m sufficiente per il treno da {train_length_m} m."
            )
        if record.suffix == "BIS":
            parts.append(
                "Binario BIS privilegiato rispetto ai binari con marciapiede per categoria INV."
            )
    else:
        parts.append(
            f"Marciapiede da {record.len_compl} m >= lunghezza treno {train_length_m} m."
        )

    if _is_lh(train_type):
        if record.priority_class == 0:
            parts.append("Binario nella fascia prioritaria per lunga percorrenza (2-13).")
        else:
            parts.append("Binario di supporto per lunga percorrenza (1 o 14).")

    if planned_num is not None:
        if record.num == planned_num and record.suffix != planned_suffix:
            parts.append("Variante dello stesso numero del binario previsto.")
        elif record.num is not None and math.isfinite(record.proximity):
            distance = int(record.proximity)
            if distance == 0:
                parts.append("Stesso numero del binario previsto.")
            elif distance == 1:
                parts.append("Adiacente al binario previsto.")
            else:
                parts.append(f"Distanza di {distance} numeri dal binario previsto.")
        elif not math.isfinite(record.proximity):
            parts.append("Numero non confrontabile con il binario previsto.")

    if record.similarity >= 2:
        parts.append("Marciapiede identico al previsto.")
    elif record.similarity == 1:
        parts.append("Profilo marciapiede coerente con il previsto.")

    high, low = _profile_tuple(info)
    if high and not low:
        parts.append("Disponibile marciapiede alto.")
    elif low and not high:
        parts.append("Disponibile marciapiede basso.")
    elif high and low:
        parts.append("Disponibili marciapiedi alto e basso.")

    if not parts:
        parts.append("Rispetta tutti i vincoli configurati.")

    return " ".join(parts)


def select_tracks(
    train_code: str,
    train_length_m: int,
    train_category: str,
    tracks: TrackDataset,
    planned_track: Optional[str] = None,
) -> List[Dict[str, str]]:
    """Return up to seven admissible tracks with explanatory notes."""
    if train_length_m <= 0:
        raise ValueError("Train length must be greater than zero.")

    train_type = (train_category or "").upper().strip()
    is_inv = train_type == "INV"

    metadata = _build_track_metadata(tracks)
    if not metadata:
        raise ValueError("No valid tracks found in dataset.")

    planned_num, planned_suffix, planned_info = _resolve_planned_track(
        planned_track, metadata, tracks
    )

    candidates: List[CandidateRecord] = []
    for norm_name, meta in metadata.items():
        if _is_track_excluded(
            norm_name,
            meta.num,
            meta.suffix,
            train_type,
            is_inv,
            planned_num,
            planned_suffix,
        ):
            continue

        if not _meets_length_requirements(
            meta.len_compl,
            meta.cap_fun,
            train_length_m,
            is_inv,
        ):
            continue

        candidates.append(
            _build_candidate_record(
                norm_name,
                meta,
                train_type,
                planned_num,
                planned_suffix,
                planned_info,
                tracks,
            )
        )

    def _sort_key(record: CandidateRecord) -> Tuple:
        base = (
            record.priority_class,
            record.proximity,
            record.neg_similarity,
            record.same_number_bonus,
            record.len_delta,
            record.sort_num,
            record.suffix_flag,
        )
        if train_type == "INV":
            has_platform = 0 if record.len_compl == 0 else 1
            bis_rank = 0 if record.suffix == "BIS" else 1
            return (has_platform, bis_rank) + base
        return base

    candidates.sort(key=_sort_key)
    results: List[Dict[str, str]] = []
    for candidate in candidates[:7]:
        reason = _build_reason(
            candidate,
            train_type,
            train_length_m,
            planned_num,
            planned_suffix,
            planned_info,
            tracks,
        )
        results.append({"track": candidate.name, "reason": reason})
    return results
