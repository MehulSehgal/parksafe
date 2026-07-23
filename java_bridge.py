"""
Bridge between the Python API and the Java municipal microservice
(service-java/ChallanService.java), reached over plain HTTP/JSON.

This is the "admin" half of ParkSafe: tow-zone registry + issued challans.
Kept as a separate JVM process (rather than folded into Python) to show a
real polyglot boundary — in a production system this is exactly the kind of
service a municipal IT department might already run on the JVM.
"""
from __future__ import annotations

import os
import requests

JAVA_SERVICE_URL = os.environ.get("PARKSAFE_JAVA_URL", "http://localhost:8081")
TIMEOUT = 3


class JavaServiceUnavailable(Exception):
    pass


def _get(path, **kwargs):
    try:
        r = requests.get(f"{JAVA_SERVICE_URL}{path}", timeout=TIMEOUT, **kwargs)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        raise JavaServiceUnavailable(str(e)) from e


def _post(path, payload):
    try:
        r = requests.post(f"{JAVA_SERVICE_URL}{path}", json=payload, timeout=TIMEOUT)
        r.raise_for_status()
        return r.json()
    except requests.RequestException as e:
        raise JavaServiceUnavailable(str(e)) from e


def list_tow_zones():
    return _get("/tow-zones")


def report_tow_zone(area: str, lat: float, lng: float, radius_m: float, reason: str):
    return _post("/tow-zones", {"area": area, "lat": lat, "lng": lng, "radiusM": radius_m, "reason": reason})


def list_challans(plate: str | None = None):
    params = {"plate": plate} if plate else {}
    return _get("/challans", params=params)


def issue_challan(spot_id: int, area: str, plate: str, amount: float, reason: str):
    return _post("/challans", {
        "spotId": spot_id, "area": area, "plate": plate, "amount": amount, "reason": reason,
    })
