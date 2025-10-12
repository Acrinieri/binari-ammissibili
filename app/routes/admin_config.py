from __future__ import annotations

from fastapi import APIRouter, Depends, Response, status
from sqlalchemy.orm import Session

from ..config_service import (
    delete_category_rule,
    delete_priority_config,
    list_category_rule_entries,
    list_priority_entries,
    upsert_category_rule,
    upsert_priority_config,
)
from ..database import get_db
from ..schemas import (
    CategoryRulePayload,
    CategoryRuleResponse,
    PriorityConfigPayload,
    PriorityConfigResponse,
)

router = APIRouter(prefix="/admin/config", tags=["admin-config"])


def _rule_to_response(entry: dict) -> CategoryRuleResponse:
    rule = entry["rule"]
    return CategoryRuleResponse(
        category=entry["category"],
        is_custom=entry["is_custom"],
        allow_bis=rule.allow_bis,
        allow_no_platform=rule.allow_no_platform,
        min_track_number=rule.min_track_number,
        max_track_number=rule.max_track_number,
        preferred_min_track_number=rule.preferred_min_track_number,
        preferred_max_track_number=rule.preferred_max_track_number,
        deny_track_names=sorted(rule.deny_track_names),
        deny_track_patterns=list(rule.deny_track_patterns),
        deny_track_numbers=sorted(rule.deny_track_numbers),
    )


def _priority_to_response(entry: dict) -> PriorityConfigResponse:
    config = entry["config"]
    criteria = [
        {"key": item.get("key"), "weight": float(item.get("weight", 1.0)), "direction": float(item.get("direction", 1.0))}
        for item in config.criteria
        if item.get("key")
    ]
    return PriorityConfigResponse(
        category=entry["category"],
        is_custom=entry["is_custom"],
        criteria=criteria,
        same_number_bonus=config.same_number_bonus,
    )


@router.get("/category-rules", response_model=list[CategoryRuleResponse])
def read_category_rules(db: Session = Depends(get_db)) -> list[CategoryRuleResponse]:
    entries = list_category_rule_entries(db)
    return [_rule_to_response(entry) for entry in entries]


@router.put("/category-rules/{category}", response_model=CategoryRuleResponse)
def update_category_rule(
    category: str,
    payload: CategoryRulePayload,
    db: Session = Depends(get_db),
) -> CategoryRuleResponse:
    rule = upsert_category_rule(db, category, payload.model_dump())
    entry = {
        "category": category.upper().strip(),
        "rule": rule,
        "is_custom": True,
    }
    return _rule_to_response(entry)


@router.delete(
    "/category-rules/{category}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    response_class=Response,
)
def remove_category_rule(category: str, db: Session = Depends(get_db)) -> None:
    delete_category_rule(db, category)


@router.get("/priority-configs", response_model=list[PriorityConfigResponse])
def read_priority_configs(db: Session = Depends(get_db)) -> list[PriorityConfigResponse]:
    entries = list_priority_entries(db)
    return [_priority_to_response(entry) for entry in entries]


@router.put("/priority-configs/{category}", response_model=PriorityConfigResponse)
def update_priority_config(
    category: str,
    payload: PriorityConfigPayload,
    db: Session = Depends(get_db),
) -> PriorityConfigResponse:
    criteria = [
        {"key": item.key, "weight": item.weight, "direction": item.direction}
        for item in payload.criteria
        if item.key
    ]
    config = upsert_priority_config(db, category, criteria, payload.same_number_bonus)
    entry = {
        "category": category.upper().strip(),
        "config": config,
        "is_custom": True,
    }
    return _priority_to_response(entry)


@router.delete(
    "/priority-configs/{category}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_model=None,
    response_class=Response,
)
def remove_priority_config(category: str, db: Session = Depends(get_db)) -> None:
    delete_priority_config(db, category)
