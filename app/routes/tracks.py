from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..config_service import get_category_rule, get_priority_config
from ..data_loader import DatasetError, load_tracks_dataset
from ..database import get_db
from ..services.track_signals import (
    build_signal_lookup,
    format_signal_output,
    normalise_signal_string,
    signal_for_track,
)
from ..schemas import (
    SuggestedTrack,
    SuggestionRequest,
    SuggestionResponse,
    SuggestionResult,
    TrackDataset,
)
from ..services.track_selector import select_tracks

router = APIRouter(prefix="/tracks", tags=["tracks"])


@router.get("", response_model=TrackDataset)
def get_tracks(db: Session = Depends(get_db)) -> TrackDataset:
    """Expose the tracks dataset so the UI can inspect it."""
    try:
        tracks = load_tracks_dataset(db)
    except DatasetError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return TrackDataset(tracks=tracks)


@router.post("/suggestions", response_model=SuggestionResponse)
def get_suggestions(
    payload: SuggestionRequest, db: Session = Depends(get_db)
) -> SuggestionResponse:
    """Compute admissible tracks for one or more requested trains."""
    try:
        dataset = load_tracks_dataset(db)
    except DatasetError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    signal_lookup = build_signal_lookup(dataset)

    category_rule_cache: Dict[str, Any] = {}
    priority_cache: Dict[str, Any] = {}
    results: list[SuggestionResult] = []

    for train in payload.trains:
        train_category = "PRM" if train.is_prm else train.train_category

        planned_track_name = None
        append_suffix = False
        if train.planned_signal:
            normalised_signal, has_suffix = normalise_signal_string(train.planned_signal)
            append_suffix = has_suffix
            if normalised_signal:
                planned_track_name = signal_lookup.get(normalised_signal)
                if not planned_track_name:
                    # Fallback to raw track name match
                    for candidate in dataset.keys():
                        if candidate.strip().upper() == normalised_signal:
                            planned_track_name = candidate
                            break

        if train_category not in category_rule_cache:
            category_rule_cache[train_category] = get_category_rule(db, train_category)
            priority_cache[train_category] = get_priority_config(db, train_category)

        try:
            alternatives = select_tracks(
                train.train_code,
                train.train_length_m,
                train_category,
                dataset,
                planned_track_name,
                category_rule=category_rule_cache[train_category],
                priority_config=priority_cache[train_category],
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        formatted_alternatives = []
        for entry in alternatives:
            signal = format_signal_output(
                signal_for_track(dataset, entry["track"]),
                append_suffix,
            )
            formatted_alternatives.append(
                SuggestedTrack(
                    track=signal,
                    track_name=entry["track"],
                    reason=entry["reason"],
                )
            )

        results.append(SuggestionResult(train=train, alternatives=formatted_alternatives))

    top_level_alternatives = results[0].alternatives if len(results) == 1 else []

    return SuggestionResponse(alternatives=top_level_alternatives, items=results)
