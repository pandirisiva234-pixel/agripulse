"""SQLAlchemy models. SQLite by default; set DATABASE_URL for PostgreSQL/PostGIS."""
from __future__ import annotations

import os
from datetime import datetime, timezone

from sqlalchemy import JSON, DateTime, Float, ForeignKey, Integer, String, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./agripulse.db")
_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=_args, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def _now():
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class FieldRow(Base):
    __tablename__ = "fields"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120))
    district: Mapped[str] = mapped_column(String(80))
    state: Mapped[str] = mapped_column(String(80))
    crop: Mapped[str] = mapped_column(String(30))
    lat: Mapped[float] = mapped_column(Float)
    lon: Mapped[float] = mapped_column(Float)
    area_ha: Mapped[float] = mapped_column(Float)
    obs: Mapped[dict] = mapped_column(JSON)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, onupdate=_now)


class PredictionLog(Base):
    __tablename__ = "prediction_log"
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    field_id: Mapped[int] = mapped_column(ForeignKey("fields.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    yield_t_ha: Mapped[float] = mapped_column(Float)
    pest_level: Mapped[str] = mapped_column(String(10))
    risk_index: Mapped[float] = mapped_column(Float)


def get_session():
    with SessionLocal() as s:
        yield s


def init_db(seed_rows: list[dict]) -> None:
    Base.metadata.create_all(engine)
    with SessionLocal() as s:
        if s.query(FieldRow).count() == 0:
            s.add_all(FieldRow(**r) for r in seed_rows)
            s.commit()
