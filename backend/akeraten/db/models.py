"""SQLAlchemy ORM models (SQLite by default, PostgreSQL compatible)."""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import JSON, Boolean, DateTime, Float, Integer, String, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


class Base(DeclarativeBase):
    pass


class Match(Base):
    __tablename__ = "matches"
    id: Mapped[str] = mapped_column(String(80), primary_key=True)
    sport: Mapped[str] = mapped_column(String(20), index=True)
    player_a: Mapped[str] = mapped_column(String(120))
    player_b: Mapped[str] = mapped_column(String(120))
    tournament: Mapped[str | None] = mapped_column(String(160), nullable=True)
    category: Mapped[str | None] = mapped_column(String(40), nullable=True)
    surface: Mapped[str | None] = mapped_column(String(20), nullable=True)
    status: Mapped[str] = mapped_column(String(20), index=True)
    start_time: Mapped[str | None] = mapped_column(String(40), nullable=True)
    best_of: Mapped[int | None] = mapped_column(Integer, nullable=True)
    score: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    winner: Mapped[str | None] = mapped_column(String(1), nullable=True)
    source: Mapped[str | None] = mapped_column(String(40), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, onupdate=utcnow)


class OddsSnapshot(Base):
    __tablename__ = "odds_snapshots"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    match_id: Mapped[str] = mapped_column(String(80), index=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    odds_a: Mapped[float] = mapped_column(Float)
    odds_b: Mapped[float] = mapped_column(Float)
    bookmaker: Mapped[str | None] = mapped_column(String(60), nullable=True)
    status: Mapped[str | None] = mapped_column(String(20), nullable=True)
    is_closing: Mapped[bool] = mapped_column(Boolean, default=False)


class Prediction(Base):
    __tablename__ = "predictions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    match_id: Mapped[str] = mapped_column(String(80), index=True)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    prob_a: Mapped[float] = mapped_column(Float)
    elo: Mapped[float | None] = mapped_column(Float, nullable=True)
    ml: Mapped[float | None] = mapped_column(Float, nullable=True)
    monte_carlo: Mapped[float | None] = mapped_column(Float, nullable=True)
    experts: Mapped[float | None] = mapped_column(Float, nullable=True)
    status: Mapped[str | None] = mapped_column(String(20), nullable=True)


class ExpertPrediction(Base):
    __tablename__ = "expert_predictions"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    expert: Mapped[str] = mapped_column(String(120), index=True)
    match_id: Mapped[str] = mapped_column(String(80), index=True)
    match: Mapped[str | None] = mapped_column(String(260), nullable=True)
    sport: Mapped[str | None] = mapped_column(String(20), nullable=True)
    predicted_winner: Mapped[str] = mapped_column(String(120))
    side: Mapped[str | None] = mapped_column(String(1), nullable=True)
    confidence: Mapped[float] = mapped_column(Float)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    odds: Mapped[float | None] = mapped_column(Float, nullable=True)
    closing_odds: Mapped[float | None] = mapped_column(Float, nullable=True)
    result: Mapped[str] = mapped_column(String(10), default="pending")
    source: Mapped[str] = mapped_column(String(20), default="live")
    text: Mapped[str | None] = mapped_column(Text, nullable=True)


class ValueBet(Base):
    __tablename__ = "value_bets"
    id: Mapped[str] = mapped_column(String(120), primary_key=True)
    match_id: Mapped[str] = mapped_column(String(80), index=True)
    sport: Mapped[str] = mapped_column(String(20), index=True)
    tournament: Mapped[str | None] = mapped_column(String(160), nullable=True)
    category: Mapped[str | None] = mapped_column(String(40), nullable=True)
    player_a: Mapped[str] = mapped_column(String(120))
    player_b: Mapped[str] = mapped_column(String(120))
    market: Mapped[str] = mapped_column(String(60), default="Ganador del partido")
    selection: Mapped[str] = mapped_column(String(120))
    selection_side: Mapped[str] = mapped_column(String(1))
    odds: Mapped[float] = mapped_column(Float)
    bookmaker: Mapped[str | None] = mapped_column(String(60), nullable=True)
    model_prob: Mapped[float] = mapped_column(Float)
    implied_prob: Mapped[float] = mapped_column(Float)
    fair_prob: Mapped[float | None] = mapped_column(Float, nullable=True)
    edge: Mapped[float] = mapped_column(Float, index=True)
    kelly_full: Mapped[float] = mapped_column(Float)
    kelly_fraction: Mapped[float] = mapped_column(Float)
    stake: Mapped[float] = mapped_column(Float)
    confidence: Mapped[str] = mapped_column(String(10))
    confidence_score: Mapped[float] = mapped_column(Float)
    suspicious: Mapped[bool] = mapped_column(Boolean, default=False)
    in_play: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow, index=True)
    closing_odds: Mapped[float | None] = mapped_column(Float, nullable=True)
    clv: Mapped[float | None] = mapped_column(Float, nullable=True)
    result: Mapped[str] = mapped_column(String(10), default="pending")
    profit: Mapped[float | None] = mapped_column(Float, nullable=True)
    settled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    source: Mapped[str] = mapped_column(String(20), default="live")
    models: Mapped[dict | None] = mapped_column(JSON, nullable=True)


class Setting(Base):
    __tablename__ = "settings"
    key: Mapped[str] = mapped_column(String(60), primary_key=True)
    value: Mapped[dict | list | str | float | None] = mapped_column(JSON, nullable=True)
