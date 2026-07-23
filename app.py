"""
ParkSafe API (Python / FastAPI)
-------------------------------
The main backend for the ParkSafe frontend (index.html). Owns spot storage
(SQLite via SQLAlchemy) and orchestrates the two other language components:

  - engine-cpp/safety_engine   -> deterministic safety scoring + geo ranking
  - service-java/ChallanService -> municipal tow-zone registry + challans

Run:
    pip install -r requirements.txt --break-system-packages
    uvicorn app:app --reload --port 8000

Then point the frontend's "Local API" data source (see index.html) at
http://localhost:8000, or just call the endpoints directly / read the
interactive docs at http://localhost:8000/docs
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import time
from typing import List, Optional

from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

import db
import engine_bridge
import java_bridge
from schemas import (
    SpotIn, SpotOut, ReviewIn, ReviewOut, LoginIn, LoginOut, ChallanIn, TowZoneIn,
)

app = FastAPI(title="ParkSafe API", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # demo only — lock this down before any real deployment
    allow_methods=["*"],
    allow_headers=["*"],
)

db.init_db()

# Demo auth — mirrors the frontend's demo login table. NOT production auth:
# there's no password hashing/salting/rotation here, just enough to show the
# Driver vs Municipal Admin role split end-to-end.
DEMO_USERS = {
    "driver@parksafe.app": {"password": "park123", "role": "driver", "name": "Demo Driver"},
    "admin@parksafe.app": {"password": "admin123", "role": "admin", "name": "Demo Admin"},
}
_SECRET = b"parksafe-demo-secret-not-for-production"


def _sign_token(email: str) -> str:
    payload = f"{email}:{int(time.time())}"
    sig = hmac.new(_SECRET, payload.encode(), hashlib.sha256).hexdigest()[:16]
    return base64.urlsafe_b64encode(f"{payload}:{sig}".encode()).decode()


# ---------------------------------------------------------------- health --

@app.get("/api/health")
def health():
    return {"status": "ok", "service": "parksafe-python-api"}


# ---------------------------------------------------------------- auth ----

@app.post("/api/auth/login", response_model=LoginOut)
def login(body: LoginIn):
    user = DEMO_USERS.get(body.email.lower())
    if not user or user["password"] != body.password:
        raise HTTPException(status_code=401, detail="Invalid email or password")
    return LoginOut(token=_sign_token(body.email), role=user["role"], name=user["name"])


# --------------------------------------------------------------- spots ----

def _spot_dict(row: db.Spot) -> dict:
    return {
        "id": row.id, "name": row.name, "area": row.area, "lat": row.lat, "lng": row.lng,
        "price": row.price, "spots_left": row.spots_left, "total": row.total,
        "legal_status": row.legal_status, "cctv": row.cctv, "lighting": row.lighting,
        "patrolled": row.patrolled, "tow_zone": row.tow_zone, "theft_reports": row.theft_reports,
        "community_rating": row.community_rating, "reviews_count": row.reviews_count,
        "reported_by": row.reported_by,
    }


@app.get("/api/spots", response_model=List[SpotOut])
def list_spots(
    lat: float = Query(28.6139, description="Requesting user's latitude (defaults to central Delhi)"),
    lng: float = Query(77.2090, description="Requesting user's longitude"),
    engine: str = Query("cpp", pattern="^(cpp|ml)$", description="Scoring engine: cpp (rule engine) or ml"),
    session: Session = Depends(db.get_session),
):
    rows = session.query(db.Spot).all()
    if not rows:
        return []

    spot_dicts = [_spot_dict(r) for r in rows]

    if engine == "ml":
        import ml_engine
        scored = ml_engine.predict_scores(spot_dicts, lat, lng)
    else:
        scored = engine_bridge.compute_scores(spot_dicts, lat, lng)

    scored_by_id = {s["id"]: s for s in scored}
    out = []
    for r in rows:
        s = scored_by_id.get(r.id, {})
        d = _spot_dict(r)
        d["safety_score"] = s.get("safety_score", r.safety_score)
        d["theft_risk"] = s.get("theft_risk", r.theft_risk)
        d["distance_km"] = s.get("distance_km")
        out.append(d)
    out.sort(key=lambda x: (-x["safety_score"], x["distance_km"] or 0))
    return out


@app.post("/api/spots", response_model=SpotOut, status_code=201)
def create_spot(body: SpotIn, session: Session = Depends(db.get_session)):
    row = db.Spot(
        name=body.name, area=body.area, lat=body.lat, lng=body.lng, price=body.price,
        spots_left=body.spots_left, total=body.total, legal_status=body.legal_status,
        cctv=body.cctv, lighting=body.lighting, patrolled=body.patrolled,
        tow_zone=body.tow_zone, theft_reports=body.theft_reports, reported_by=body.reported_by,
    )
    session.add(row)
    session.commit()
    session.refresh(row)

    scored = engine_bridge.compute_scores([_spot_dict(row)], row.lat, row.lng)
    if scored:
        row.safety_score = scored[0]["safety_score"]
        row.theft_risk = scored[0]["theft_risk"]
        session.commit()

    d = _spot_dict(row)
    d["safety_score"], d["theft_risk"], d["distance_km"] = row.safety_score, row.theft_risk, 0.0
    return d


@app.post("/api/spots/{spot_id}/reviews", response_model=ReviewOut, status_code=201)
def add_review(spot_id: int, body: ReviewIn, session: Session = Depends(db.get_session)):
    spot = session.query(db.Spot).get(spot_id)
    if not spot:
        raise HTTPException(status_code=404, detail="Spot not found")

    review = db.Review(spot_id=spot_id, author=body.author, stars=body.stars, text=body.text)
    session.add(review)
    session.commit()
    session.refresh(review)

    all_reviews = session.query(db.Review).filter(db.Review.spot_id == spot_id).all()
    spot.reviews_count = len(all_reviews)
    spot.community_rating = round(sum(r.stars for r in all_reviews) / len(all_reviews), 1)
    session.commit()

    return review


@app.get("/api/spots/{spot_id}/reviews", response_model=List[ReviewOut])
def get_reviews(spot_id: int, session: Session = Depends(db.get_session)):
    return session.query(db.Review).filter(db.Review.spot_id == spot_id).order_by(db.Review.created_at.desc()).all()


# ------------------------------------------------ municipal (-> Java) -----

@app.get("/api/admin/tow-zones")
def get_tow_zones():
    try:
        return java_bridge.list_tow_zones()
    except java_bridge.JavaServiceUnavailable as e:
        raise HTTPException(status_code=503, detail=f"Municipal service (Java) unavailable: {e}")


@app.post("/api/admin/tow-zones", status_code=201)
def post_tow_zone(body: TowZoneIn):
    try:
        return java_bridge.report_tow_zone(body.area, body.lat, body.lng, body.radius_m, body.reason)
    except java_bridge.JavaServiceUnavailable as e:
        raise HTTPException(status_code=503, detail=f"Municipal service (Java) unavailable: {e}")


@app.get("/api/admin/challans")
def get_challans(plate: Optional[str] = None):
    try:
        return java_bridge.list_challans(plate)
    except java_bridge.JavaServiceUnavailable as e:
        raise HTTPException(status_code=503, detail=f"Municipal service (Java) unavailable: {e}")


@app.post("/api/admin/challans", status_code=201)
def post_challan(body: ChallanIn, session: Session = Depends(db.get_session)):
    spot = session.query(db.Spot).get(body.spot_id)
    area = spot.area if spot else "Unknown area"
    try:
        return java_bridge.issue_challan(body.spot_id, area, body.plate, body.amount, body.reason)
    except java_bridge.JavaServiceUnavailable as e:
        raise HTTPException(status_code=503, detail=f"Municipal service (Java) unavailable: {e}")
