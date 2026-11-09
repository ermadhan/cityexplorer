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

All data is queried live from Overture Maps parquet files on AWS S3 — no data download needed.

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

---

## Data Source

All data comes from [Overture Maps](https://overturemaps.org) — a free, public, monthly-updated global map dataset.

- S3 bucket: `s3://overturemaps-us-west-2/release/current/`
- No API key or account required.
- Updated monthly.
