# 🅿️ ParkSafe — Smart Safe Parking Navigator

**Find legal, safety-rated, CCTV-covered parking spots near you. Avoid tow zones, challans & theft — powered by community reports and real-time data.**

Built by **Brahmastra Coders**.

---

## ⚡ Quick start (one click)

Want the full stack (Python + C++ + Java) running with no manual setup?

- **Mac:** double-click `start_parksafe.command` (first time: right-click → Open, to bypass the Gatekeeper warning)
- **Windows:** double-click `start_parksafe.bat`
- **Linux:** run `./start_parksafe.sh`

Requires Python 3.10+, a C++ compiler (`g++`), and a JDK (17+) on your
machine — the script tells you clearly if any are missing and skips the
parts it can't run. It builds the C++ engine, compiles & starts the Java
service, seeds the demo DB, trains the ML model, starts the Python API, and
opens the app in your browser — all in one go. See [Architecture](#architecture)
for what's actually happening under the hood.

If you'd rather just see the static demo with zero backend, skip straight
to [Getting Started](#getting-started) below and open `index.html` directly.

---

## Overview

ParkSafe is a single-page web app that helps drivers in Delhi find parking spots that are legal, safe, and unlikely to get them towed or ticketed. Every spot on the map carries a **Safety Score**, **legal status**, tow-zone risk, CCTV/lighting info, and community reviews, so drivers can make an informed call before they park — not after they get a challan.

The app also ships with a lightweight **Municipal Admin** view for monitoring reported spots, challans, and activity across the city.

> This is a frontend demo/prototype: parking data, reviews, and availability history are seeded with realistic sample data for the Connaught Place / Central Delhi area. It's built to be wired up to a real backend (see [Data Sources](#data-sources) below).

## Features

- 🗺️ **Interactive map** (Leaflet + Google Maps / Mappls tiles) with color-coded pins for safety level
- 🛡️ **Safety Score ring** per spot, blending legal status, CCTV, lighting, patrols, and theft risk
- 🟢 **Green Zone** badge for spots that are both legal and highly safe
- 🚫 **Tow-zone & challan alerts**, surfaced as dismissible banners
- 📅 **Event-aware suggestions** (e.g. surge parking demand near a stadium/event)
- 🔍 **Search, filters, and sorting** — nearest, safest, shortest walk, top-rated, cheapest
- ⭐ **Community reviews & ratings**, availability history by time of day
- ⏱️ **Live parking timer** for an active booking
- 🔐 **Role-based auth** — Driver vs Municipal Admin, with an admin dashboard for oversight
- 🔌 **Optional Neo4j AuraDB connection** to swap seeded demo data for a live graph database
- 🧭 **Optional Mappls (MapmyIndia) tile layer**, falling back to Google Maps tiles by default
- 🧩 **NEW: Polyglot backend** — a Python (FastAPI) API backed by a C++ safety-scoring engine, a Java municipal microservice, and an optional scikit-learn ML scoring model. See [Architecture](#architecture) and [`ARCHITECTURE.md`](ARCHITECTURE.md).

## Tech Stack

**Frontend (unchanged, zero-build):**
- Vanilla HTML / CSS / JavaScript
- [Leaflet.js](https://leafletjs.com/) for the map
- [Neo4j JavaScript Driver](https://github.com/neo4j/neo4j-javascript-driver) (browser bundle) for optional AuraDB integration
- Google Fonts: Space Grotesk, Inter, JetBrains Mono

**Backend (new, optional — see [Architecture](#architecture)):**
- **Python** — FastAPI, SQLAlchemy/SQLite, scikit-learn, pandas
- **C++17** — dependency-free safety-scoring & geospatial engine
- **Java (JDK 17+)** — dependency-free municipal microservice (tow-zones, challans)

## Getting Started

No installation or build tools needed — it's a single static HTML file.

```bash
git clone https://github.com/<your-username>/parksafe.git
cd parksafe
```

Then either:

- **Open directly:** double-click `index.html` (works fully offline / from `file://`, aside from the CDN-hosted fonts, map tiles, and libraries).
- **Or serve locally** (recommended, avoids browser file-access restrictions in some environments):

  ```bash
  python3 -m http.server 8000
  # then visit http://localhost:8000
  ```

### Demo login

| Role   | Email                | Password  |
|--------|-----------------------|-----------|
| Driver | `driver@parksafe.app` | `park123` |
| Admin  | `admin@parksafe.app`  | `admin123`|

You can also use the **"Demo — Driver"** / **"Demo — Municipal admin"** buttons on the login screen to skip typing credentials.

### Connecting a live Neo4j AuraDB instance (optional)

Click the gear icon next to your profile after logging in to open the **Aura** connection modal, and enter your AuraDB connection URI, username, and password. If you skip this, the app runs entirely on seeded demo data (`dataSource = "demo"`).

### Using Mappls (MapmyIndia) tiles (optional)

By default the map uses inverted Google Maps tiles for the dark theme. To use Mappls tiles instead, set an API key in `localStorage`:

```js
localStorage.setItem('mappls_key', 'YOUR_MAPPLS_API_KEY');
```

## Architecture

ParkSafe now ships with an optional polyglot backend: a **Python** (FastAPI)
API that calls out to a **C++** safety-scoring engine and a **Java**
municipal microservice, plus an optional **scikit-learn** ML scoring model.
Full diagram and request-flow walkthrough: [`ARCHITECTURE.md`](ARCHITECTURE.md).

The frontend still works exactly as before with **zero setup** (just open
`index.html`) — the backend is an additional, opt-in data source you switch
to from the same gear-icon modal used for AuraDB.

### Running the backend locally

You'll need `g++` (C++17), a JDK 17+ (`javac`/`java`), and Python 3.10+.

**1. Build the C++ safety engine**
```bash
cd engine-cpp
make
cd ..
```

**2. Compile & start the Java municipal service** (port 8081)
```bash
cd service-java
javac ChallanService.java
java ChallanService 8081
```

**3. Set up & start the Python API** (port 8000), in a new terminal
```bash
cd backend-python
pip install -r requirements.txt --break-system-packages   # or use a venv
cd ..
python3 scripts/seed_db.py          # seeds the same 7 demo spots as the frontend
python3 scripts/train_model.py      # optional: trains the ML scoring model
cd backend-python
uvicorn app:app --reload --port 8000
```

Interactive API docs: http://localhost:8000/docs

**4. Point the frontend at it**

Open `index.html`, click the gear icon next to your profile → **"Use
ParkSafe API (localhost:8000)"**. The map switches to live data served by
the Python/C++/Java stack. (If you're serving `index.html` from somewhere
other than `http://localhost:8000`, set `localStorage.setItem('parksafe_api_base', 'http://your-host:8000')` before connecting.)

**5. (Optional) Generate a municipal analytics report**
```bash
python3 scripts/generate_report.py
# -> reports/parking_report.html
```

### Key backend endpoints

| Method | Path                         | Description                                  |
|--------|------------------------------|-----------------------------------------------|
| GET    | `/api/spots`                 | List spots, scored & ranked (`?engine=cpp\|ml`) |
| POST   | `/api/spots`                 | Report a new community spot                   |
| POST   | `/api/spots/{id}/reviews`    | Add a review, recomputes community rating     |
| POST   | `/api/auth/login`            | Demo login (driver/admin)                     |
| GET/POST | `/api/admin/tow-zones`     | Municipal tow-zone registry (proxies to Java)  |
| GET/POST | `/api/admin/challans`     | Issue / list challans (proxies to Java)        |



```
parksafe/
├── index.html            # Frontend: markup, styles, and logic (unchanged demo mode + new API toggle)
├── README.md
├── ARCHITECTURE.md       # Polyglot backend architecture & request flows
├── LICENSE
├── backend-python/       # FastAPI API: SQLite persistence, auth, orchestration
│   ├── app.py
│   ├── db.py
│   ├── schemas.py
│   ├── engine_bridge.py  # calls the compiled C++ engine
│   ├── ml_engine.py      # calls the trained scikit-learn model
│   ├── java_bridge.py    # calls the Java municipal service over HTTP
│   └── requirements.txt
├── engine-cpp/           # C++17 safety-scoring & geo-ranking engine (stdlib only)
│   ├── safety_engine.cpp
│   └── Makefile
├── service-java/         # Java municipal microservice (JDK HttpServer only, no deps)
│   └── ChallanService.java
├── scripts/              # Python utility scripts
│   ├── seed_db.py        # seeds SQLite with the same demo spots as the frontend
│   ├── train_model.py    # trains the scikit-learn safety model
│   └── generate_report.py# pandas-based municipal analytics report
├── models/                # trained ML model artifact (safety_model.joblib)
└── reports/               # generated HTML analytics reports
```

## Data Sources

All parking spots, reviews, and availability history are currently **hardcoded sample data** inside `index.html` (see the `spots`, `DEMO_REVIEWS`, and `AVAIL_HISTORY` objects) so the app is fully functional out of the box with no backend. To go live, swap these for calls to your own API or the optional Neo4j AuraDB integration.

## Roadmap Ideas

- [ ] Real-time spot availability via a backend/API instead of static demo data
- [ ] User-submitted reviews and spot reports persisted to a database
- [ ] Push/SMS alerts for tow-zone risk near a saved vehicle location
- [ ] Expand coverage beyond Central Delhi

## License

Released under the [MIT License](LICENSE).

## Credits

Made with 🅿️ by **Brahmastra Coders**.
