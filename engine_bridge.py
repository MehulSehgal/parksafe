"""
Bridge between the Python API and the compiled C++ `safety_engine` binary.

Why shell out instead of a Python port? The scoring + haversine ranking is
the one CPU-bound, easily-parallelisable piece of ParkSafe, and this keeps
the interop dead simple (stdin/stdout CSV) with zero binding/build tooling
(no pybind11/cffi needed) — handy for a hackathon-grade polyglot demo.

Falls back to a pure-Python implementation automatically if the binary
hasn't been compiled yet, so the API still works out of the box.
"""
from __future__ import annotations

import math
import os
import subprocess
from typing import Iterable, List, Dict, Any

_HERE = os.path.dirname(os.path.abspath(__file__))
ENGINE_BINARY = os.path.normpath(os.path.join(_HERE, "..", "engine-cpp", "safety_engine"))

_LEGAL_CODE = {"Legal": 0, "Restricted": 1, "Illegal": 2}


def _spot_to_line(spot: Dict[str, Any]) -> str:
    return ",".join(str(x) for x in [
        "SPOT",
        spot["id"],
        spot["lat"],
        spot["lng"],
        _LEGAL_CODE.get(spot.get("legal_status", "Legal"), 0),
        int(bool(spot.get("cctv"))),
        int(bool(spot.get("lighting"))),
        int(bool(spot.get("patrolled"))),
        int(spot.get("theft_reports", 0)),
        int(bool(spot.get("tow_zone"))),
    ])


def _pure_python_fallback(spots: List[Dict[str, Any]], user_lat: float, user_lng: float):
    """Pure-Python re-implementation used only if the C++ binary is missing."""
    def haversine(lat1, lng1, lat2, lng2):
        r = 6371.0088
        p1, p2 = math.radians(lat1), math.radians(lat2)
        dlat = math.radians(lat2 - lat1)
        dlng = math.radians(lng2 - lng1)
        a = math.sin(dlat / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlng / 2) ** 2
        return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))

    out = []
    for s in spots:
        score = 50.0
        score += {"Legal": 30, "Restricted": 5, "Illegal": -25}.get(s.get("legal_status", "Legal"), 0)
        if s.get("cctv"): score += 15
        if s.get("lighting"): score += 8
        if s.get("patrolled"): score += 10
        if s.get("tow_zone"): score -= 20
        theft = s.get("theft_reports", 0)
        score -= 18.0 * (1 - math.exp(-0.35 * theft))
        score = max(0, min(100, round(score)))
        risk = "High" if (theft >= 8 or score < 45) else ("Medium" if (theft >= 2 or score < 75) else "Low")
        dist = haversine(user_lat, user_lng, s["lat"], s["lng"])
        out.append({"id": s["id"], "safety_score": int(score), "theft_risk": risk, "distance_km": round(dist, 3)})
    out.sort(key=lambda r: (-r["safety_score"], r["distance_km"]))
    return out


def compute_scores(spots: Iterable[Dict[str, Any]], user_lat: float = 28.6139, user_lng: float = 77.2090):
    """
    Given a list of spot dicts (as produced by SQLAlchemy rows via .__dict__
    or SpotOut.model_dump()), return a list of
    {id, safety_score, theft_risk, distance_km} ranked best-first.
    """
    spots = list(spots)
    if not spots:
        return []

    if not os.path.isfile(ENGINE_BINARY) or not os.access(ENGINE_BINARY, os.X_OK):
        return _pure_python_fallback(spots, user_lat, user_lng)

    lines = [_spot_to_line(s) for s in spots]
    lines.append(f"QUERY,{user_lat},{user_lng}")
    payload = "\n".join(lines) + "\n"

    try:
        proc = subprocess.run(
            [ENGINE_BINARY], input=payload, capture_output=True, text=True, timeout=5
        )
    except (OSError, subprocess.SubprocessError):
        return _pure_python_fallback(spots, user_lat, user_lng)

    if proc.returncode != 0:
        return _pure_python_fallback(spots, user_lat, user_lng)

    results = []
    for line in proc.stdout.strip().splitlines():
        parts = line.split(",")
        if len(parts) != 4:
            continue
        sid, score, risk, dist = parts
        results.append({
            "id": int(sid),
            "safety_score": int(score),
            "theft_risk": risk,
            "distance_km": float(dist),
        })
    return results
