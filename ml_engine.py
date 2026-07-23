"""
Loads the scikit-learn model trained by scripts/train_model.py and exposes
a predict_scores() function with the same shape as engine_bridge.compute_scores(),
so the API can swap between the C++ rule engine and this ML engine via a
query parameter (?engine=ml vs ?engine=cpp).
"""
from __future__ import annotations

import math
import os
from typing import Iterable, List, Dict, Any

_HERE = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.normpath(os.path.join(_HERE, "..", "models", "safety_model.joblib"))

_LEGAL_CODE = {"Legal": 0, "Restricted": 1, "Illegal": 2}
_bundle = None


def _load():
    global _bundle
    if _bundle is None:
        import joblib
        if not os.path.isfile(MODEL_PATH):
            raise FileNotFoundError(
                f"No trained model at {MODEL_PATH}. Run `python3 scripts/train_model.py` first."
            )
        _bundle = joblib.load(MODEL_PATH)
    return _bundle


def is_available() -> bool:
    return os.path.isfile(MODEL_PATH)


def _haversine(lat1, lng1, lat2, lng2):
    r = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlng / 2) ** 2
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def predict_scores(spots: Iterable[Dict[str, Any]], user_lat: float = 28.6139, user_lng: float = 77.2090):
    import pandas as pd

    bundle = _load()
    model, feature_cols = bundle["model"], bundle["features"]

    spots = list(spots)
    if not spots:
        return []

    rows = []
    for s in spots:
        rows.append({
            "legal_code": _LEGAL_CODE.get(s.get("legal_status", "Legal"), 0),
            "cctv": int(bool(s.get("cctv"))),
            "lighting": int(bool(s.get("lighting"))),
            "patrolled": int(bool(s.get("patrolled"))),
            "tow_zone": int(bool(s.get("tow_zone"))),
            "theft_reports": int(s.get("theft_reports", 0)),
        })
    df = pd.DataFrame(rows)[feature_cols]
    preds = model.predict(df)

    results = []
    for s, score in zip(spots, preds):
        score = int(round(max(0, min(100, score))))
        theft = s.get("theft_reports", 0)
        risk = "High" if (theft >= 8 or score < 45) else ("Medium" if (theft >= 2 or score < 75) else "Low")
        dist = round(_haversine(user_lat, user_lng, s["lat"], s["lng"]), 3)
        results.append({"id": s["id"], "safety_score": score, "theft_risk": risk, "distance_km": dist})

    results.sort(key=lambda r: (-r["safety_score"], r["distance_km"]))
    return results
