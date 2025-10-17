from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ..constants import DEFAULT_SIGNAL_CODE
from ..database import get_db
from ..models import Track
from ..schemas import TrackCreate, TrackDetail, TrackUpdate
from ..services.track_signals import resolve_signal_code

router = APIRouter(prefix="/admin/tracks", tags=["admin"])


def _track_to_detail(track: Track) -> TrackDetail:
    return TrackDetail.from_orm(track)


@router.get("", response_model=list[TrackDetail])
def list_tracks(db: Session = Depends(get_db)) -> list[TrackDetail]:
    tracks = db.query(Track).order_by(Track.name).all()
    return [_track_to_detail(track) for track in tracks]


@router.post("", response_model=TrackDetail, status_code=status.HTTP_201_CREATED)
def create_track(payload: TrackCreate, db: Session = Depends(get_db)) -> TrackDetail:
    raw_signal = (payload.signal_code or "").strip()
    signal_code = raw_signal or resolve_signal_code(payload.name)
    if not signal_code:
        signal_code = DEFAULT_SIGNAL_CODE

    track = Track(
        name=payload.name.strip(),
        signal_code=signal_code,
        marciapiede_complessivo_m=payload.marciapiede_complessivo_m,
        marciapiede_alto_m=payload.marciapiede_alto_m,
        marciapiede_basso_m=payload.marciapiede_basso_m,
        capacita_funzionale_m=payload.capacita_funzionale_m,
    )
    db.add(track)
    try:
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A track with this name already exists.",
        ) from None
    db.refresh(track)
    return _track_to_detail(track)


def _get_track_or_404(db: Session, track_id: int) -> Track:
    track = db.query(Track).filter(Track.id == track_id).first()
    if not track:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Track not found.")
    return track


@router.put("/{track_id}", response_model=TrackDetail)
def update_track(
    track_id: int, payload: TrackUpdate, db: Session = Depends(get_db)
) -> TrackDetail:
    track = _get_track_or_404(db, track_id)

    name_updated = False
    if payload.name is not None:
        new_name = payload.name.strip()
        if new_name != track.name:
            if db.query(Track).filter(Track.name == new_name).first():
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="A track with this name already exists.",
                )
            track.name = new_name
            name_updated = True

    for field in (
        "marciapiede_complessivo_m",
        "marciapiede_alto_m",
        "marciapiede_basso_m",
        "capacita_funzionale_m",
    ):
        value = getattr(payload, field)
        if value is not None:
            setattr(track, field, value)

    if payload.signal_code is not None:
        raw_signal = payload.signal_code.strip() if payload.signal_code else ""
        track.signal_code = raw_signal or resolve_signal_code(track.name)
    elif name_updated:
        track.signal_code = resolve_signal_code(track.name)
        if not track.signal_code:
            track.signal_code = DEFAULT_SIGNAL_CODE

    db.commit()
    db.refresh(track)
    return _track_to_detail(track)


@router.delete(
    "/{track_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    response_class=Response,
)
def delete_track(track_id: int, db: Session = Depends(get_db)) -> None:
    track = _get_track_or_404(db, track_id)
    db.delete(track)
    db.commit()
