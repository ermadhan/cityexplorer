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
- Rank all saved cities by combined, per-population, and per-area POI scores.

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

The Places & POIs rating recounts places inside the Overture division polygon
from each snapshot's recorded release. It averages two equally weighted scores:
places per 10,000 people and places per km², each scaled to the highest eligible
city in the current comparison. At least two cities need valid population and
polygon areas; scores are relative to the selected cities, not quality-of-life
ratings. Overture population can be missing or lack a reference year. The
polygon-based POI count differs from the bounding-box feature tables.

The **Leaderboard** uses the latest snapshot of every saved city. It shows
separate combined, per-population, and per-area rankings. Each individual
score is relative to all saved cities with that metric; the combined score uses
only cities with both metrics. At least two eligible cities are needed for a
ranking, and cities missing one metric remain eligible for the other. Scores
and ranks can change when saved cities are added or updated.

Rating inputs are cached separately from existing snapshots. They are fetched
when a comparison is first rated; to backfill all historical snapshots, run
`python backfill_rating_inputs.py` from `backend`. The command reports errors
if a recorded release cannot be accessed, and can be rerun. Missing population
is reported as unavailable; it is not replaced with current data.

### Batch import cities

The standalone importer populates the same SQLite database used by the app.
Create a UTF-8 CSV with `city` and `country` headers and optional `state` and
`reload` columns:

```csv
city,country,state,reload
Chennai,India,Tamil Nadu,false
Coimbatore,IN,IN-TN,true
```

From `backend`, run `python import_cities.py path\to\cities.csv`. Country values
may be two-letter codes or exact country names published by Overture. City names
must exactly match an Overture primary name, ignoring case. If provided, `state`
must match a region's Overture primary or common name, or its full region code,
ignoring case, within the given country. The importer only considers city
divisions whose Overture region code matches; a city with a missing region code
will not match a state-filtered row. Leave `state` empty or omit the column to
search the whole country as before. When multiple divisions match, the importer
selects the locality if there is exactly one. Multiple localities, or multiple
matches with no locality, are logged as ambiguous rather than guessed. A single
non-locality match remains eligible. Unknown or ambiguous states, missing boundaries, and
unknown countries are also logged. Names or aliases absent from Overture cannot
be resolved.

Each successful new import runs all six exploration queries, loads polygon-based
POI rating inputs, and saves a timestamped snapshot. Existing cities are skipped
by default, while missing rating inputs are filled using their snapshot's
recorded release. Set `reload` to `true`, `yes`, or `1` for a new snapshot;
`false`, `no`, `0`, or empty skips an existing snapshot. Missing population
remains unavailable.

Each run creates a timestamped failure CSV under `backend/import_logs` (or
`--log-dir`), including the requested state and rows that cannot be found, are ambiguous, are invalid,
or fail processing. Processing continues after row failures. Exit status is
`0` for success, `1` if any row failed, and `2` for invalid input or setup
errors. An unrecoverable CSV syntax error is logged and ends the run because
the remaining rows cannot be parsed reliably. The first run may take
considerable time because it queries Overture.

The backend stores successful snapshots in `backend/city_snapshots.sqlite3`.
This local database is ignored by Git. Snapshot APIs:

- `GET /api/snapshots/{snapshot_id}` — one complete snapshot
- `GET /api/cities/saved` — saved cities and their latest snapshot dates
- `GET /api/snapshots/latest/{division_id}` — latest snapshot for a city
- `GET /api/cities/{division_id}/snapshots` — city snapshot history
- `GET /api/snapshots/compare?division_id=...&division_id=...` — latest
  snapshots for 2–4 cities
- `GET /api/ratings/compare?snapshot_id=...&snapshot_id=...` — relative POI
  ratings for 2–4 exact snapshots
- `GET /api/ratings/leaderboard` — scores for the latest snapshot of each saved city

---

## Data Source

All data comes from [Overture Maps](https://overturemaps.org) — a free, public, monthly-updated global map dataset.

- S3 bucket: `s3://overturemaps-us-west-2/release/<latest-release>/`
- Latest release is resolved from the [Overture STAC catalog](https://stac.overturemaps.org/catalog.json).
- No API key or account required.
- Updated monthly.
