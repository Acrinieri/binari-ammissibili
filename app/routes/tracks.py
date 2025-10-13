from __future__ import annotations

from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..config_service import get_category_rule, get_priority_config
from ..data_loader import DatasetError, load_tracks_dataset
from ..database import get_db
from ..schemas import (
    SuggestionRequest,
    SuggestionResponse,
    SuggestionResult,
    TrackData,
    TrackDataset,
)
from ..services.track_selector import select_tracks

router = APIRouter(prefix="/tracks", tags=["tracks"])


def _to_plain_dataset(dataset: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """Convert TrackData objects to plain dictionaries."""
    plain: Dict[str, Dict[str, Any]] = {}
    for name, data in dataset.items():
        if isinstance(data, TrackData):
            plain[name] = data.dict()
        elif isinstance(data, dict):
            plain[name] = data
        else:
            raise TypeError(f"Unsupported track data type for '{name}': {type(data)}")
    return plain


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
        dataset = (
            _to_plain_dataset(payload.tracks_override)
            if payload.tracks_override
            else load_tracks_dataset(db)
        )
    except (DatasetError, TypeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    category_rule_cache: Dict[str, Any] = {}
    priority_cache: Dict[str, Any] = {}
    results: list[SuggestionResult] = []

    for train in payload.trains:
        train_category = "PRM" if train.is_prm else train.train_category

        if train_category not in category_rule_cache:
            category_rule_cache[train_category] = get_category_rule(db, train_category)
            priority_cache[train_category] = get_priority_config(db, train_category)

        try:
            alternatives = select_tracks(
                train.train_code,
                train.train_length_m,
                train_category,
                dataset,
                train.planned_track,
                category_rule=category_rule_cache[train_category],
                priority_config=priority_cache[train_category],
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

        results.append(SuggestionResult(train=train, alternatives=alternatives))

    top_level_alternatives = results[0].alternatives if len(results) == 1 else []

    return SuggestionResponse(alternatives=top_level_alternatives, items=results)
