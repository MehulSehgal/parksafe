# 🅿️ ParkSafe — Smart Safe Parking Navigator

**Find legal, safety-rated, CCTV-covered parking spots near you. Avoid tow zones, challans & theft — powered by community reports and real-time data.**

Built by **Brahmastra Coders**.

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

## Tech Stack

- Vanilla HTML / CSS / JavaScript — no build step required
- [Leaflet.js](https://leafletjs.com/) for the map
- [Neo4j JavaScript Driver](https://github.com/neo4j/neo4j-javascript-driver) (browser bundle) for optional AuraDB integration
- Google Fonts: Space Grotesk, Inter, JetBrains Mono

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

## Project Structure

```
parksafe/
├── index.html   # Entire app: markup, styles, and logic
├── README.md
└── LICENSE
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
