# ParkSafe — Architecture

ParkSafe started as a single-file frontend demo (`index.html`) running entirely
on hardcoded sample data. This update adds a real, polyglot backend behind it,
while keeping the original static demo mode fully working with zero setup.

```
                         ┌──────────────────────────┐
                         │        index.html         │
                         │  (Leaflet UI, vanilla JS)  │
                         │                            │
                         │  Data source toggle:       │
                         │   • Demo data (default)    │
                         │   • Neo4j AuraDB (existing) │
                         │   • ParkSafe API  (new)    │
                         └────────────┬───────────────┘
                                      │ fetch() JSON over HTTP
                                      ▼
                    ┌──────────────────────────────────┐
                    │   backend-python/app.py (FastAPI)  │
                    │   • SQLite via SQLAlchemy          │
                    │   • demo auth (driver / admin)     │
                    │   • /api/spots, /api/spots/{id}/... │
                    │   • /api/admin/* (proxies to Java)  │
                    └───────┬───────────────────┬─────────┘
                            │                   │
             subprocess (CSV over stdio)   HTTP (JSON)
                            │                   │
                            ▼                   ▼
        ┌────────────────────────────┐  ┌──────────────────────────────┐
        │ engine-cpp/safety_engine    │  │ service-java/ChallanService    │
        │ (C++, stdlib only)          │  │ (Java, JDK HttpServer only)    │
        │ • weighted safety score     │  │ • tow-zone registry            │
        │ • haversine ranking         │  │ • challan issuance / lookup     │
        └────────────────────────────┘  └──────────────────────────────┘

        backend-python/ml_engine.py  ◄── models/safety_model.joblib
        (scikit-learn GradientBoostingRegressor, trained by
         scripts/train_model.py — an alternative to the C++ rule engine,
         selectable per-request via ?engine=ml)

        scripts/generate_report.py (pandas)
        → reads SQLite spots + calls the Java service for challans
        → writes reports/parking_report.html
```

## Why this split?

- **C++** does the one CPU-bound, easily-optimized piece (scoring +
  geospatial ranking) as a tiny, dependency-free binary. Talking to it over
  stdin/stdout CSV keeps the interop trivial — no pybind11/cffi build step.
- **Java** models the municipal side as its own service, the way a real city
  IT department's existing JVM infrastructure might expose tow-zone and
  challan data. It's intentionally decoupled from the Python API over plain
  HTTP so it could be swapped for a real system without touching the rest.
- **Python** is the integration layer and does the most work — REST API,
  persistence, auth, and the two data-science pieces (scikit-learn scoring
  model, pandas analytics report) — matching the "more Python" ask.
- The **frontend is unchanged** in its default demo mode. The new API is an
  additional, opt-in data source alongside the existing AuraDB option, so
  cloning the repo and opening `index.html` still works exactly as before.

## Request flow: "list spots near me"

1. Frontend calls `GET /api/spots?lat=..&lng=..&engine=cpp`.
2. FastAPI loads all spots from SQLite.
3. It shells out to `engine-cpp/safety_engine`, piping each spot + the
   user's location in as CSV lines, and reads back `id,score,risk,distance`
   sorted best-first.
4. FastAPI merges those computed fields onto the DB rows and returns JSON.
5. Swap `engine=ml` to use the scikit-learn model instead — same response
   shape, different scoring method, useful for comparing a rule-based vs.
   learned approach on the same data.

## Request flow: "issue a challan" (Municipal Admin)

1. Frontend/admin calls `POST /api/admin/challans` on the Python API.
2. FastAPI looks up the spot's area in SQLite, then forwards the request to
   the Java service (`POST /challans`).
3. Java stores it in memory and returns the created challan; FastAPI passes
   that straight back to the frontend.

## Known limitations (this is a prototype, not production)

- Auth is a demo HMAC token, not a real JWT/OAuth flow — no password
  hashing, expiry, or refresh.
- The Java service's data is in-memory only (resets on restart). Swap for a
  real DB (Postgres, etc.) before relying on it.
- CORS is wide open (`allow_origins=["*"]`) for local development only.
- The ML model is trained on synthetic data mirroring the rule engine's
  formula, not real historical incident data — it's a demonstration of the
  integration, not a validated risk model.
