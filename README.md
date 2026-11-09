# 🏙️ City Explorer

Understand man-made structures in any city using public [Overture Maps](https://overturemaps.org) data.

## What it does

Pick any city → get a full count breakdown of:
- 🏗️ Buildings (by class: residential, commercial, industrial…)
- 🛣️ Roads & Transport (motorways, primary roads, railways, paths…)
- 💧 Water Bodies (lakes, rivers, reservoirs, canals…)
- 🏭 Infrastructure (bridges, power towers, transit stops…)
- 🌳 Land Use (parks, education, military, industrial zones…)
- 📍 Places & POIs (food, health, education, retail…)
- Compare the latest saved feature counts for 2–4 cities.

All data is queried live from Overture Maps parquet files on AWS S3 — no data download needed.
Successful explorations are also saved as timestamped snapshots in a local
SQLite database, so they can be compared later.

---

## Project Structure

```
cityexplorer/
├── backend/     ← Python + FastAPI + DuckDB
└── frontend/    ← React + TypeScript + Vite + Tailwind
```

---

## Running Locally

### 1. Start the Backend

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload
# → API available at http://localhost:8000
# → Swagger docs at http://localhost:8000/docs
```

### 2. Start the Frontend

```bash
cd frontend
npm install
npm run dev
# → Open http://localhost:5173
```

> **Note:** The first query for a large city (e.g. Bangalore, Mumbai) may take 30–90 seconds as DuckDB reads parquet files directly from S3.

### Compare Cities

Explore each city once to save its results, then open **Compare cities**, search
or choose 2–4 cities from the local SQLite database, and compare the latest saved snapshot across buildings,
transportation, water, infrastructure, land use, and places. Counts are shown
as returned; they are not adjusted for city size or population.

The backend stores successful snapshots in `backend/city_snapshots.sqlite3`.
This local database is ignored by Git. Snapshot APIs:

- `GET /api/snapshots/{snapshot_id}` — one complete snapshot
- `GET /api/cities/saved` — saved cities and their latest snapshot dates
- `GET /api/snapshots/latest/{division_id}` — latest snapshot for a city
- `GET /api/cities/{division_id}/snapshots` — city snapshot history
- `GET /api/snapshots/compare?division_id=...&division_id=...` — latest
  snapshots for 2–4 cities

---

## Data Source

All data comes from [Overture Maps](https://overturemaps.org) — a free, public, monthly-updated global map dataset.

- S3 bucket: `s3://overturemaps-us-west-2/release/<latest-release>/`
- Latest release is resolved from the [Overture STAC catalog](https://stac.overturemaps.org/catalog.json).
- No API key or account required.
- Updated monthly.
