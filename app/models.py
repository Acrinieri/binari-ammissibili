from __future__ import annotations

from sqlalchemy import Boolean, Column, Float, Integer, String
from sqlalchemy.dialects.sqlite import JSON

from .database import Base


class Track(Base):
    __tablename__ = "tracks"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(64), unique=True, nullable=False)
    marciapiede_complessivo_m = Column(Integer, nullable=False, default=0)
    marciapiede_alto_m = Column(Integer, nullable=False, default=0)
    marciapiede_basso_m = Column(Integer, nullable=False, default=0)
    capacita_funzionale_m = Column(Integer, nullable=True)


class CategoryRule(Base):
    __tablename__ = "category_rules"

    category = Column(String(32), primary_key=True)
    allow_bis = Column(Boolean, nullable=False, default=False)
    allow_no_platform = Column(Boolean, nullable=False, default=False)
    min_track_number = Column(Integer, nullable=True)
    max_track_number = Column(Integer, nullable=True)
    preferred_min_track_number = Column(Integer, nullable=True)
    preferred_max_track_number = Column(Integer, nullable=True)
    deny_track_names = Column(JSON, nullable=False, default=list)
    deny_track_patterns = Column(JSON, nullable=False, default=list)
    deny_track_numbers = Column(JSON, nullable=False, default=list)


class CategoryPriorityConfig(Base):
    __tablename__ = "category_priority_configs"

    category = Column(String(32), primary_key=True)
    criteria = Column(JSON, nullable=False)
    same_number_bonus = Column(Float, nullable=False, default=-1.0)
