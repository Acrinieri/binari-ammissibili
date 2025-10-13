from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, PositiveInt, field_validator, model_validator


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


class TrainRequest(BaseModel):
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

    @field_validator("train_category", mode="before")
    @classmethod
    def _normalise_category(cls, value: Any) -> str:
        if value is None:
            return ""
        return str(value).strip().upper()


class SuggestionRequest(BaseModel):
    trains: List[TrainRequest] = Field(
        ..., min_length=1, description="List of trains to evaluate."
    )

    @model_validator(mode="before")
    @classmethod
    def _coerce_legacy_payload(cls, value: Any) -> Any:
        """Accept legacy single-train payloads or raw lists of trains."""
        if isinstance(value, dict):
            if "trains" in value:
                return value
            legacy_keys = {
                "train_code",
                "train_length_m",
                "train_category",
                "is_prm",
                "planned_track",
            }
            if legacy_keys.intersection(value.keys()):
                train_payload = {
                    key: value.get(key)
                    for key in legacy_keys
                    if key in value
                }
                return {"trains": [train_payload]}
        elif isinstance(value, list):
            return {"trains": value}
        return value

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "trains": [
                        {
                            "train_code": "61234",
                            "train_length_m": 250,
                            "train_category": "IC",
                            "is_prm": False,
                            "planned_track": "IV",
                        },
                        {
                            "train_code": "98765",
                            "train_length_m": 320,
                            "train_category": "REG",
                            "is_prm": True,
                            "planned_track": None,
                        },
                        {
                            "train_code": "99887",
                            "train_length_m": 280,
                            "train_category": "INV",
                            "is_prm": False,
                            "planned_track": None,
                        },
                    ]
                },
                {
                    "trains": [
                        {
                            "train_code": "12345",
                            "train_length_m": 200,
                            "train_category": "REG",
                            "is_prm": False,
                            "planned_track": None,
                        }
                    ]
                },
            ]
        }
    )


class SuggestedTrack(BaseModel):
    track: str
    reason: str


class SuggestionResult(BaseModel):
    train: TrainRequest
    alternatives: List[SuggestedTrack]


class SuggestionResponse(BaseModel):
    alternatives: List[SuggestedTrack] = Field(
        default_factory=list,
        description=(
            "Preserved for backward compatibility: contains the alternatives "
            "for single-train requests."
        ),
    )
    items: List[SuggestionResult] = Field(
        default_factory=list,
        description="Detailed suggestions for each processed train.",
    )


class CategoryRulePayload(BaseModel):
    allow_bis: bool = False
    allow_no_platform: bool = False
    min_track_number: Optional[int] = None
    max_track_number: Optional[int] = None
    preferred_min_track_number: Optional[int] = None
    preferred_max_track_number: Optional[int] = None
    deny_track_names: list[str] = Field(default_factory=list)
    deny_track_patterns: list[str] = Field(default_factory=list)
    deny_track_numbers: list[int] = Field(default_factory=list)


class CategoryRuleResponse(CategoryRulePayload):
    category: str
    is_custom: bool = False


class PriorityCriterionPayload(BaseModel):
    key: str
    weight: float = 1.0
    direction: float = 1.0


class PriorityConfigPayload(BaseModel):
    criteria: list[PriorityCriterionPayload] = Field(default_factory=list)
    same_number_bonus: float = -1.0


class PriorityConfigResponse(PriorityConfigPayload):
    category: str
    is_custom: bool = False
