"""
ParkSafe ML training script (Python / scikit-learn).

Trains a small gradient-boosted regressor that predicts a spot's safety
score (0-100) from its features, as an ML-driven alternative to the
deterministic C++ rule engine. This is intentionally a lightweight,
explainable model — the point is to demonstrate a second, data-driven
scoring path the API can call via `?engine=ml`, not to build a production
risk model from one city's demo data.

Usage:
    python3 scripts/train_model.py

Produces:
    models/safety_model.joblib
"""
from __future__ import annotations

import os
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error
import joblib

RNG = np.random.default_rng(42)
HERE = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.normpath(os.path.join(HERE, "..", "models", "safety_model.joblib"))

FEATURES = ["legal_code", "cctv", "lighting", "patrolled", "tow_zone", "theft_reports"]


def synthesize_training_data(n=4000) -> pd.DataFrame:
    """
    Generates synthetic-but-realistic training examples using the same
    weighted formula as the C++ rule engine, plus noise — standing in for
    real historical community-report + incident data a live deployment
    would train on.
    """
    legal_code = RNG.integers(0, 3, n)                 # 0 Legal, 1 Restricted, 2 Illegal
    cctv = RNG.integers(0, 2, n)
    lighting = RNG.integers(0, 2, n)
    patrolled = RNG.integers(0, 2, n)
    tow_zone = RNG.integers(0, 2, n)
    theft_reports = RNG.poisson(2.0, n)

    legal_bonus = np.select([legal_code == 0, legal_code == 1, legal_code == 2], [30, 5, -25])
    score = (
        50
        + legal_bonus
        + cctv * 15
        + lighting * 8
        + patrolled * 10
        - tow_zone * 20
        - 18 * (1 - np.exp(-0.35 * theft_reports))
        + RNG.normal(0, 4, n)  # measurement / reporting noise
    )
    score = np.clip(score, 0, 100)

    return pd.DataFrame({
        "legal_code": legal_code,
        "cctv": cctv,
        "lighting": lighting,
        "patrolled": patrolled,
        "tow_zone": tow_zone,
        "theft_reports": theft_reports,
        "safety_score": score,
    })


def main():
    df = synthesize_training_data()
    X, y = df[FEATURES], df["safety_score"]
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    model = GradientBoostingRegressor(n_estimators=150, max_depth=3, learning_rate=0.08, random_state=42)
    model.fit(X_train, y_train)

    mae = mean_absolute_error(y_test, model.predict(X_test))
    print(f"Validation MAE: {mae:.2f} safety-score points")

    os.makedirs(os.path.dirname(MODEL_PATH), exist_ok=True)
    joblib.dump({"model": model, "features": FEATURES}, MODEL_PATH)
    print(f"Saved model -> {MODEL_PATH}")


if __name__ == "__main__":
    main()
