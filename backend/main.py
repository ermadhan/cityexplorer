"""
City Explorer — FastAPI Backend
Queries Overture Maps parquet files on AWS S3 via DuckDB.
"""

from datetime import datetime, timezone
from typing import Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from queries import get_overture_base
from queries.city_boundary import get_city_boundary, search_cities
from queries.buildings import count_buildings
from queries.transportation import count_transportation
from queries.water import count_water
from queries.infrastructure import count_infrastructure
from queries.land_use import count_land_use
from queries.places import count_places
from snapshot_store import (
    SNAPSHOT_SCHEMA_VERSION,
    get_city_snapshots,
    get_latest_snapshot,
    get_latest_snapshots,
    get_snapshot,
    initialize_snapshot_db,
    list_saved_cities,
    save_snapshot,
)

app = FastAPI(
    title="City Explorer API",
    description="Queries Overture Maps data to analyse man-made structures in any city.",
    version="0.1.0",
)

# Allow requests from the React dev server
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class ExploreRequest(BaseModel):
    city_name: str
    country_code: Optional[str] = None   # e.g. "IN", "US" — optional disambiguation
    subtype: Optional[str] = None        # Overture division subtype


class CityBoundaryResult(BaseModel):
    division_id: str
    city_name: str
    country: Optional[str]
    subtype: str
    bbox: dict   # {xmin, ymin, xmax, ymax}


class CategoryCount(BaseModel):
    label: str
    count: int


class ExploreResult(BaseModel):
    city: CityBoundaryResult
    buildings: list[CategoryCount]
    transportation: list[CategoryCount]
    water: list[CategoryCount]
    infrastructure: list[CategoryCount]
    land_use: list[CategoryCount]
    places: list[CategoryCount]


class CitySnapshot(ExploreResult):
    snapshot_id: int
    captured_at: str
    overture_release: str
    schema_version: int


class SavedCity(BaseModel):
    division_id: str
    city_name: str
    country: Optional[str]
    subtype: str
    captured_at: str


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------

@app.on_event("startup")
def startup():
    initialize_snapshot_db()


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/api/search")
def api_search(q: str, country: Optional[str] = None, limit: int = 10):
    """
    Autocomplete city search. Returns metro-area candidates sorted by size.
    Example: GET /api/search?q=bang&country=IN
    """
    if len(q) < 2:
        return []
    return search_cities(q, country, limit)


@app.post("/api/boundary", response_model=CityBoundaryResult)
def api_boundary(req: ExploreRequest):
    """
    Look up the city boundary from Overture Maps divisions theme.
    Returns the bbox used to filter all subsequent queries.
    """
    result = get_city_boundary(req.city_name, req.country_code, req.subtype)
    if result is None:
        raise HTTPException(
            status_code=404,
            detail=f"City '{req.city_name}' not found in Overture Maps divisions."
        )
    return result


@app.post("/api/explore", response_model=CitySnapshot)
def api_explore(req: ExploreRequest):
    """
    Full city exploration: returns structure counts across all Overture themes.
    Runs queries in sequence (sequential to avoid DuckDB thread issues).
    """
    # Step 1 — get city boundary
    boundary = get_city_boundary(req.city_name, req.country_code, req.subtype)
    if boundary is None:
        raise HTTPException(
            status_code=404,
            detail=f"City '{req.city_name}' not found in Overture Maps divisions."
        )

    bbox = boundary["bbox"]

    # Step 2 — run all theme queries using the bbox
    result = ExploreResult(
        city=boundary,
        buildings=count_buildings(bbox),
        transportation=count_transportation(bbox),
        water=count_water(bbox),
        infrastructure=count_infrastructure(bbox),
        land_use=count_land_use(bbox),
        places=count_places(bbox),
    )
    captured_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
    release = get_overture_base().rsplit("/", 1)[-1]
    snapshot_id = save_snapshot(
        {**result.model_dump(), "captured_at": captured_at},
        release,
    )
    return CitySnapshot(
        **result.model_dump(),
        snapshot_id=snapshot_id,
        captured_at=captured_at,
        overture_release=release,
        schema_version=SNAPSHOT_SCHEMA_VERSION,
    )


@app.get("/api/cities/saved", response_model=list[SavedCity])
def api_saved_cities():
    return list_saved_cities()


@app.get("/api/cities/{division_id}/snapshots", response_model=list[CitySnapshot])
def api_city_snapshots(division_id: str):
    return get_city_snapshots(division_id)


@app.get("/api/snapshots/compare", response_model=list[CitySnapshot])
def api_compare_snapshots(
    division_id: list[str] = Query(..., min_length=2, max_length=4),
):
    if len(set(division_id)) != len(division_id):
        raise HTTPException(status_code=400, detail="City selections must be unique.")

    snapshots = get_latest_snapshots(division_id)
    missing = [
        city_id
        for city_id, snapshot in zip(division_id, snapshots)
        if snapshot is None
    ]
    if missing:
        raise HTTPException(
            status_code=404,
            detail=(
                "No saved exploration for division ID(s): "
                f"{', '.join(missing)}. Explore each city before comparing."
            ),
        )
    return snapshots


@app.get("/api/snapshots/latest/{division_id}", response_model=CitySnapshot)
def api_latest_snapshot(division_id: str):
    snapshot = get_latest_snapshot(division_id)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="No saved snapshot for this city.")
    return snapshot


@app.get("/api/snapshots/{snapshot_id}", response_model=CitySnapshot)
def api_snapshot(snapshot_id: int):
    snapshot = get_snapshot(snapshot_id)
    if snapshot is None:
        raise HTTPException(status_code=404, detail="Snapshot not found.")
    return snapshot
