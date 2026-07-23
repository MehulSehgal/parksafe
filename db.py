"""
ParkSafe backend — persistence layer (SQLAlchemy + SQLite).

This replaces the frontend's hardcoded `spots` / DEMO_REVIEWS / AVAIL_HISTORY
objects with a real, queryable database so the polyglot backend has
something to actually serve.
"""
from __future__ import annotations

from datetime import datetime

from sqlalchemy import (
    Column, Integer, String, Float, Boolean, DateTime, ForeignKey, create_engine
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

import os
_DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "parksafe.db")
DB_URL = f"sqlite:///{_DB_PATH}"

engine = create_engine(DB_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


class Spot(Base):
    __tablename__ = "spots"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    area = Column(String, nullable=False)
    lat = Column(Float, nullable=False)
    lng = Column(Float, nullable=False)
    price = Column(Float, default=0)
    spots_left = Column(Integer, default=1)
    total = Column(Integer, default=1)
    legal_status = Column(String, default="Legal")   # Legal | Restricted | Illegal
    cctv = Column(Boolean, default=False)
    lighting = Column(Boolean, default=False)
    patrolled = Column(Boolean, default=False)
    tow_zone = Column(Boolean, default=False)
    theft_reports = Column(Integer, default=0)

    # Cached last-computed values (refreshed by the C++ engine on read)
    safety_score = Column(Integer, default=50)
    theft_risk = Column(String, default="Medium")

    community_rating = Column(Float, default=0.0)
    reviews_count = Column(Integer, default=0)
    reported_by = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    reviews = relationship("Review", back_populates="spot", cascade="all, delete-orphan")


class Review(Base):
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, autoincrement=True)
    spot_id = Column(Integer, ForeignKey("spots.id"), nullable=False)
    author = Column(String, default="Anonymous")
    stars = Column(Integer, nullable=False)
    text = Column(String, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    spot = relationship("Spot", back_populates="reviews")


def init_db():
    Base.metadata.create_all(bind=engine)


def get_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
