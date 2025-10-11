from __future__ import annotations

from sqlalchemy import Column, Integer, String

from .database import Base


class Track(Base):
    __tablename__ = "tracks"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(64), unique=True, nullable=False)
    marciapiede_complessivo_m = Column(Integer, nullable=False, default=0)
    marciapiede_alto_m = Column(Integer, nullable=False, default=0)
    marciapiede_basso_m = Column(Integer, nullable=False, default=0)
    capacita_funzionale_m = Column(Integer, nullable=True)
