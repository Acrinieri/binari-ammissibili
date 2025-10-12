from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional

from sqlalchemy.orm import Session

from .constants import LH_CATEGORIES
from .models import CategoryPriorityConfig, CategoryRule


@dataclass(frozen=True)
class CategoryRuleConfig:
    allow_bis: bool
    allow_no_platform: bool
    min_track_number: Optional[int]
    max_track_number: Optional[int]
    preferred_min_track_number: Optional[int]
    preferred_max_track_number: Optional[int]
    deny_track_names: set[str]
    deny_track_patterns: List[str]
    deny_track_numbers: set[int]


@dataclass(frozen=True)
class PriorityConfig:
    criteria: List[Dict[str, Any]]
    same_number_bonus: float


DEFAULT_CATEGORY_RULES: Dict[str, CategoryRuleConfig] = {
    "default": CategoryRuleConfig(
        allow_bis=False,
        allow_no_platform=False,
        min_track_number=None,
        max_track_number=None,
        preferred_min_track_number=None,
        preferred_max_track_number=None,
        deny_track_names=set(),
        deny_track_patterns=[],
        deny_track_numbers=set(),
    ),
    "INV": CategoryRuleConfig(
        allow_bis=True,
        allow_no_platform=True,
        min_track_number=None,
        max_track_number=None,
        preferred_min_track_number=None,
        preferred_max_track_number=None,
        deny_track_names=set(),
        deny_track_patterns=[],
        deny_track_numbers=set(),
    ),
    "PRM": CategoryRuleConfig(
        allow_bis=False,
        allow_no_platform=False,
        min_track_number=None,
        max_track_number=None,
        preferred_min_track_number=None,
        preferred_max_track_number=None,
        deny_track_names={"I NORD"},
        deny_track_patterns=[" NORD"],
        deny_track_numbers=set(),
    ),
    "ES*": CategoryRuleConfig(
        allow_bis=False,
        allow_no_platform=False,
        min_track_number=None,
        max_track_number=None,
        preferred_min_track_number=None,
        preferred_max_track_number=None,
        deny_track_names=set(),
        deny_track_patterns=[],
        deny_track_numbers={15},
    ),
    "LH": CategoryRuleConfig(
        allow_bis=False,
        allow_no_platform=False,
        min_track_number=1,
        max_track_number=14,
        preferred_min_track_number=2,
        preferred_max_track_number=13,
        deny_track_names=set(),
        deny_track_patterns=[],
        deny_track_numbers=set(),
    ),
}


def _normalize_category_key(category: Optional[str]) -> str:
    cat = (category or "").upper().strip()
    if cat in DEFAULT_CATEGORY_RULES:
        return cat
    if cat in LH_CATEGORIES:
        return "LH"
    if cat.startswith("ES"):
        return "ES*"
    if cat == "PRM":
        return "PRM"
    if cat == "INV":
        return "INV"
    return "default"


DEFAULT_PRIORITY_CONFIGS: Dict[str, PriorityConfig] = {
    "default": PriorityConfig(
        criteria=[
            {"key": "priority_class"},
            {"key": "proximity"},
            {"key": "similarity"},
            {"key": "same_number"},
            {"key": "length_delta"},
            {"key": "track_number"},
            {"key": "suffix_flag"},
        ],
        same_number_bonus=-1.0,
    ),
    "INV": PriorityConfig(
        criteria=[
            {"key": "no_platform_first"},
            {"key": "bis_preference"},
            {"key": "priority_class"},
            {"key": "proximity"},
            {"key": "similarity"},
            {"key": "same_number"},
            {"key": "length_delta"},
            {"key": "track_number"},
            {"key": "suffix_flag"},
        ],
        same_number_bonus=-1.0,
    ),
}


def _load_rule_from_row(row: CategoryRule, fallback: CategoryRuleConfig) -> CategoryRuleConfig:
    if not row:
        return fallback
    return CategoryRuleConfig(
        allow_bis=row.allow_bis,
        allow_no_platform=row.allow_no_platform,
        min_track_number=row.min_track_number,
        max_track_number=row.max_track_number,
        preferred_min_track_number=row.preferred_min_track_number,
        preferred_max_track_number=row.preferred_max_track_number,
        deny_track_names=set(row.deny_track_names or []),
        deny_track_patterns=list(row.deny_track_patterns or []),
        deny_track_numbers=set(row.deny_track_numbers or []),
    )


def _load_priority_from_row(row: CategoryPriorityConfig, fallback: PriorityConfig) -> PriorityConfig:
    if not row:
        return fallback
    criteria = row.criteria or []
    return PriorityConfig(
        criteria=list(criteria),
        same_number_bonus=row.same_number_bonus,
    )


def get_category_rule(session: Session, category: Optional[str]) -> CategoryRuleConfig:
    raw_category = (category or "").upper().strip()
    key = _normalize_category_key(raw_category)
    fallback = DEFAULT_CATEGORY_RULES[key]
    row = session.get(CategoryRule, raw_category)
    if not row and key != raw_category:
        row = session.get(CategoryRule, key)
    return _load_rule_from_row(row, fallback)


def get_priority_config(session: Session, category: Optional[str]) -> PriorityConfig:
    raw_category = (category or "").upper().strip()
    key = _normalize_category_key(raw_category)
    fallback = DEFAULT_PRIORITY_CONFIGS.get(key, DEFAULT_PRIORITY_CONFIGS["default"])
    row = session.get(CategoryPriorityConfig, raw_category)
    if not row and key != raw_category:
        row = session.get(CategoryPriorityConfig, key)
    return _load_priority_from_row(row, fallback)


def iter_known_categories(session: Session) -> Iterable[str]:
    db_categories = {c[0] for c in session.query(CategoryRule.category).all()}
    db_categories.update(c[0] for c in session.query(CategoryPriorityConfig.category).all())
    defaults = set(DEFAULT_CATEGORY_RULES.keys()) | set(DEFAULT_PRIORITY_CONFIGS.keys())
    return sorted(db_categories | defaults)

def list_category_rule_entries(session: Session) -> List[dict]:
    entries: List[dict] = []
    for category in iter_known_categories(session):
        norm = (category or "").upper().strip()
        rule = get_category_rule(session, norm)
        row = session.get(CategoryRule, norm)
        entries.append(
            {
                "category": norm,
                "rule": rule,
                "is_custom": row is not None,
            }
        )
    return entries


def upsert_category_rule(
    session: Session,
    category: str,
    payload: Dict[str, Any],
) -> CategoryRuleConfig:
    norm = (category or "").upper().strip()
    row = session.get(CategoryRule, norm)
    if not row:
        row = CategoryRule(category=norm)
        session.add(row)

    row.allow_bis = bool(payload.get("allow_bis", row.allow_bis))
    row.allow_no_platform = bool(payload.get("allow_no_platform", row.allow_no_platform))
    row.min_track_number = payload.get("min_track_number")
    row.max_track_number = payload.get("max_track_number")
    row.preferred_min_track_number = payload.get("preferred_min_track_number")
    row.preferred_max_track_number = payload.get("preferred_max_track_number")
    row.deny_track_names = list(dict.fromkeys(payload.get("deny_track_names", []) or []))
    row.deny_track_patterns = list(dict.fromkeys(payload.get("deny_track_patterns", []) or []))
    row.deny_track_numbers = list(dict.fromkeys(payload.get("deny_track_numbers", []) or []))

    session.commit()
    session.refresh(row)
    return _load_rule_from_row(row, DEFAULT_CATEGORY_RULES[_normalize_category_key(norm)])


def delete_category_rule(session: Session, category: str) -> None:
    norm = (category or "").upper().strip()
    row = session.get(CategoryRule, norm)
    if row:
        session.delete(row)
        session.commit()


def list_priority_entries(session: Session) -> List[dict]:
    entries: List[dict] = []
    for category in iter_known_categories(session):
        norm = (category or "").upper().strip()
        priority = get_priority_config(session, norm)
        row = session.get(CategoryPriorityConfig, norm)
        entries.append(
            {
                "category": norm,
                "config": priority,
                "is_custom": row is not None,
            }
        )
    return entries


def upsert_priority_config(
    session: Session,
    category: str,
    criteria: List[Dict[str, Any]],
    same_number_bonus: float,
) -> PriorityConfig:
    norm = (category or "").upper().strip()
    row = session.get(CategoryPriorityConfig, norm)
    if not row:
        row = CategoryPriorityConfig(category=norm, criteria=[], same_number_bonus=-1.0)
        session.add(row)

    row.criteria = criteria
    row.same_number_bonus = same_number_bonus
    session.commit()
    session.refresh(row)
    return _load_priority_from_row(row, DEFAULT_PRIORITY_CONFIGS.get(_normalize_category_key(norm), DEFAULT_PRIORITY_CONFIGS["default"]))


def delete_priority_config(session: Session, category: str) -> None:
    norm = (category or "").upper().strip()
    row = session.get(CategoryPriorityConfig, norm)
    if row:
        session.delete(row)
        session.commit()




