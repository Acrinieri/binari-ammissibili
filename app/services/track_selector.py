"""Core logic for computing admissible tracks based on the provided ruleset."""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass
from typing import Any, Dict, List, NamedTuple, Optional, Tuple

from ..config_service import CategoryRuleConfig, PriorityConfig

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
    similarity_score: int
    same_number_bonus: float
    len_delta: int
    sort_num: float
    suffix_flag: int
    len_compl: int
    cap_fun: int
    num: Optional[int]
    suffix: str


def _parse_track_name(name: str) -> Tuple[Optional[int], str, str]:
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


def _profile_tuple(info: Dict[str, Any]) -> Tuple[int, int]:
    high = 1 if (info.get("marciapiede_alto_m") or 0) > 0 else 0
    low = 1 if (info.get("marciapiede_basso_m") or 0) > 0 else 0
    return high, low


def _track_similarity_score(
    candidate_info: Dict[str, Any],
    planned_info: Optional[Dict[str, Any]],
) -> int:
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


def _proximity_rank(
    candidate_num: Optional[int],
    candidate_suffix: str,
    planned_num: Optional[int],
    planned_suffix: str,
) -> float:
    if candidate_num is None or planned_num is None:
        return math.inf
    if candidate_num == planned_num and candidate_suffix != planned_suffix:
        return 1
    return abs(candidate_num - planned_num)


def _normalise_capacity(info: Dict[str, Any]) -> int:
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
    if not planned_track:
        return None, "", None

    planned_num, planned_suffix, planned_norm = _parse_track_name(planned_track)
    lookup = {
        (meta.num, meta.suffix): norm_name for norm_name, meta in track_meta.items()
    }
    resolved_norm = lookup.get((planned_num, planned_suffix), planned_norm)
    planned_info = tracks.get(resolved_norm)
    if not planned_info and planned_track:
        logger.warning(
            "Planned track '%s' not found nei dati. Prossimita disabilitata.",
            planned_track,
        )
    return planned_num, planned_suffix or "", planned_info


def _priority_class(num: Optional[int], rule: CategoryRuleConfig) -> int:
    if not isinstance(num, int):
        return 0

    if rule.min_track_number is not None and num < rule.min_track_number:
        return 1
    if rule.max_track_number is not None and num > rule.max_track_number:
        return 1

    preferred_min = rule.preferred_min_track_number
    preferred_max = rule.preferred_max_track_number
    if preferred_min is not None and preferred_max is not None:
        return 0 if preferred_min <= num <= preferred_max else 1

    return 0


def _is_track_excluded(
    norm_name: str,
    num: Optional[int],
    suffix: str,
    rule: CategoryRuleConfig,
    planned_num: Optional[int],
    planned_suffix: str,
) -> bool:
    if norm_name == "SSE AMB.":
        return True

    if planned_num is not None and num == planned_num and suffix == planned_suffix:
        return True

    if suffix == "BIS" and not rule.allow_bis:
        return True

    if isinstance(num, int):
        if rule.min_track_number is not None and num < rule.min_track_number:
            return True
        if rule.max_track_number is not None and num > rule.max_track_number:
            return True
        if num in rule.deny_track_numbers:
            return True

    if norm_name in rule.deny_track_names:
        return True

    if any(pattern and pattern in norm_name for pattern in rule.deny_track_patterns):
        return True

    return False


def _meets_length_requirements(
    len_compl: int,
    cap_fun: int,
    train_length: int,
    rule: CategoryRuleConfig,
) -> bool:
    if not rule.allow_no_platform and len_compl <= 0:
        return False

    if rule.allow_no_platform:
        if cap_fun > 0:
            return cap_fun >= train_length
        if len_compl > 0:
            return len_compl >= train_length
        return True

    return len_compl >= train_length


def _build_candidate_record(
    norm_name: str,
    meta: TrackMetadata,
    planned_num: Optional[int],
    planned_suffix: str,
    planned_info: Optional[Dict[str, Any]],
    tracks: TrackDataset,
    rule: CategoryRuleConfig,
    priority: PriorityConfig,
) -> CandidateRecord:
    proximity = _proximity_rank(meta.num, meta.suffix, planned_num, planned_suffix)
    cand_info = tracks.get(norm_name, {})
    similarity = _track_similarity_score(cand_info, planned_info)
    planned_len = (
        int(planned_info.get("marciapiede_complessivo_m") or 0)
        if planned_info
        else 0
    )
    len_delta = abs((planned_len or meta.len_compl) - meta.len_compl)
    priority_class = _priority_class(meta.num, rule)
    sort_num = float(meta.num) if isinstance(meta.num, int) else math.inf
    suffix_flag = 1 if meta.suffix else 0
    same_number_bonus = 0.0
    if planned_num is not None and meta.num == planned_num and meta.suffix != planned_suffix:
        same_number_bonus = priority.same_number_bonus

    return CandidateRecord(
        name=norm_name,
        priority_class=priority_class,
        proximity=proximity,
        similarity_score=similarity,
        same_number_bonus=same_number_bonus,
        len_delta=len_delta,
        sort_num=sort_num,
        suffix_flag=suffix_flag,
        len_compl=meta.len_compl,
        cap_fun=meta.cap_fun,
        num=meta.num,
        suffix=meta.suffix,
    )


def _criterion_value(
    key: str,
    record: CandidateRecord,
    priority: PriorityConfig,
) -> float:
    if key == "priority_class":
        return record.priority_class
    if key == "proximity":
        return record.proximity
    if key == "similarity":
        return -record.similarity_score
    if key == "same_number":
        return record.same_number_bonus
    if key == "length_delta":
        return record.len_delta
    if key == "track_number":
        return record.sort_num
    if key == "suffix_flag":
        return record.suffix_flag
    if key == "no_platform_first":
        return 0.0 if record.len_compl == 0 else 1.0
    if key == "bis_preference":
        return 0.0 if record.suffix == "BIS" else 1.0
    return 0.0


def _build_reason(
    record: CandidateRecord,
    train_type: str,
    train_length_m: int,
    planned_num: Optional[int],
    planned_suffix: str,
    planned_info: Optional[Dict[str, Any]],
    tracks: TrackDataset,
    rule: CategoryRuleConfig,
) -> str:
    parts: List[str] = []
    info = tracks.get(record.name, {})

    if rule.allow_no_platform and record.len_compl == 0:
        parts.append("Nessun marciapiede disponibile: consentito per questa categoria.")
    else:
        parts.append(
            f"Marciapiede da {record.len_compl} m >= lunghezza treno {train_length_m} m."
        )

    if record.cap_fun > 0:
        parts.append(
            f"Capacita funzionale {record.cap_fun} m sufficiente per il treno da {train_length_m} m."
        )

    if rule.allow_bis and record.suffix == "BIS":
        parts.append("Binario BIS ammesso dalle regole della categoria.")

    if rule.preferred_min_track_number is not None and rule.preferred_max_track_number is not None:
        if record.priority_class == 0:
            parts.append(
                f"Binario nella fascia prioritaria ({rule.preferred_min_track_number}-{rule.preferred_max_track_number})."
            )
        else:
            parts.append(
                f"Binario di supporto rispetto alla fascia preferita ({rule.preferred_min_track_number}-{rule.preferred_max_track_number})."
            )

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

    if record.similarity_score >= 2:
        parts.append("Marciapiede identico al previsto.")
    elif record.similarity_score == 1:
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
    category_rule: Optional[CategoryRuleConfig] = None,
    priority_config: Optional[PriorityConfig] = None,
) -> List[Dict[str, str]]:
    if train_length_m <= 0:
        raise ValueError("Train length must be greater than zero.")

    if category_rule is None or priority_config is None:
        raise ValueError("Configuration objects are required.")

    train_type = (train_category or "").upper().strip()

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
            category_rule,
            planned_num,
            planned_suffix,
        ):
            continue

        if not _meets_length_requirements(
            meta.len_compl,
            meta.cap_fun,
            train_length_m,
            category_rule,
        ):
            continue

        record = _build_candidate_record(
            norm_name,
            meta,
            planned_num,
            planned_suffix,
            planned_info,
            tracks,
            category_rule,
            priority_config,
        )
        candidates.append(record)

    criteria = priority_config.criteria or [{"key": "track_number"}]

    def sort_key(record: CandidateRecord) -> Tuple[float, ...]:
        values: List[float] = []
        for criterion in criteria:
            key = criterion.get("key")
            if not key:
                continue
            weight = float(criterion.get("weight", 1.0))
            direction = float(criterion.get("direction", 1.0))
            values.append(_criterion_value(key, record, priority_config) * weight * direction)
        return tuple(values)

    candidates.sort(key=sort_key)

    suggestions: List[Dict[str, str]] = []
    for candidate in candidates[:7]:
        reason = _build_reason(
            candidate,
            train_type,
            train_length_m,
            planned_num,
            planned_suffix,
            planned_info,
            tracks,
            category_rule,
        )
        suggestions.append({"track": candidate.name, "reason": reason})

    return suggestions
