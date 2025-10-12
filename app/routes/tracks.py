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
    """Compute admissible tracks for the requested train."""
    try:
        dataset = (
            _to_plain_dataset(payload.tracks_override)
            if payload.tracks_override
            else load_tracks_dataset(db)
        )
    except (DatasetError, TypeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    train_category = "PRM" if payload.is_prm else payload.train_category

    try:
        category_rule = get_category_rule(db, train_category)
        priority_config = get_priority_config(db, train_category)
        alternatives = select_tracks(
            payload.train_code,
            payload.train_length_m,
            train_category,
            dataset,
            payload.planned_track,
            category_rule=category_rule,
            priority_config=priority_config,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return SuggestionResponse(alternatives=alternatives)
