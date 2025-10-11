from __future__ import annotations

from typing import Dict, Optional

from pydantic import BaseModel, Field, PositiveInt


class TrackBase(BaseModel):
    marciapiede_complessivo_m: int = Field(
        ..., ge=0, description="Total usable platform length in metres."
    )
    marciapiede_alto_m: int = Field(
        0, ge=0, description="High platform length in metres (if available)."
    )
    marciapiede_basso_m: int = Field(
        0, ge=0, description="Low platform length in metres (if available)."
    )
    capacita_funzionale_m: Optional[int] = Field(
        None,
        description=(
            "Functional capacity length (metres). "
            "If missing, the total platform length is used for INV trains."
        ),
    )


class TrackData(TrackBase):
    pass


class TrackDataset(BaseModel):
    tracks: Dict[str, TrackData]


class TrackCreate(TrackBase):
    name: str = Field(..., min_length=1, max_length=64)


class TrackUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=64)
    marciapiede_complessivo_m: Optional[int] = Field(None, ge=0)
    marciapiede_alto_m: Optional[int] = Field(None, ge=0)
    marciapiede_basso_m: Optional[int] = Field(None, ge=0)
    capacita_funzionale_m: Optional[int] = Field(
        None,
        description="Functional capacity length (metres).",
    )


from pydantic import ConfigDict


class TrackDetail(TrackBase):
    id: int
    name: str

    model_config = ConfigDict(from_attributes=True)


class SuggestionRequest(BaseModel):
    train_code: str = Field(..., description="Train number or code.")
    train_length_m: PositiveInt = Field(..., description="Train length in metres.")
    train_category: str = Field(
        ..., description="Operational category (REG, IC, ES*, INV...)."
    )
    is_prm: bool = Field(
        False, description="Flag if the train requires PRM-compliant facilities."
    )
    planned_track: Optional[str] = Field(
        None, description="Planned track name (optional)."
    )
    tracks_override: Optional[Dict[str, TrackData]] = Field(
        None,
        description=(
            "Optional dataset that replaces the default one when provided."
        ),
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "train_code": "61234",
                    "train_length_m": 250,
                    "train_category": "IC",
                    "is_prm": False,
                    "planned_track": "IV",
                    "tracks_override": None,
                },
                {
                    "train_code": "98765",
                    "train_length_m": 320,
                    "train_category": "INV",
                    "is_prm": False,
                    "planned_track": None,
                    "tracks_override": {
                        "V": {
                            "marciapiede_complessivo_m": 310,
                            "marciapiede_alto_m": 150,
                            "marciapiede_basso_m": 160,
                            "capacita_funzionale_m": 280,
                        },
                        "XIV": {
                            "marciapiede_complessivo_m": 246,
                            "marciapiede_alto_m": 0,
                            "marciapiede_basso_m": 246,
                            "capacita_funzionale_m": 246,
                        },
                    },
                },
            ]
        }
    )


class SuggestedTrack(BaseModel):
    track: str
    reason: str


class SuggestionResponse(BaseModel):
    alternatives: list[SuggestedTrack]
