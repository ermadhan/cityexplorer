"""Recount POIs and measure division geometry from a specific Overture release."""

import re
from typing import TypedDict

from queries import get_db


class RatingInputs(TypedDict):
    population: int | None
    area_sq_km: float | None
    poi_count: int | None


def fetch_rating_inputs(division_id: str, release: str) -> RatingInputs:
    if not re.fullmatch(r"\d{4}-\d{2}-\d{2}\.\d+", release):
        raise ValueError(f"Invalid Overture release: {release!r}")

    base = f"s3://overturemaps-us-west-2/release/{release}"
    con = get_db()
    try:
        # DuckDB 2.x requires an explicit axis-order setting for spheroidal area.
        xy_setting = con.execute(
            "SELECT value FROM duckdb_settings() WHERE name = 'geometry_always_xy'"
        ).fetchone()
        if xy_setting:
            con.execute("SET geometry_always_xy = true")

        division = con.execute(
            """
            SELECT population FROM read_parquet(?, hive_partitioning = 1)
            WHERE id = ?
            """,
            [f"{base}/theme=divisions/type=division/*.parquet", division_id],
        ).fetchone()
        if division is None:
            raise ValueError(f"Division {division_id} was not found in release {release}.")

        con.execute(
            """
            CREATE TEMP TABLE rating_geometry AS
            SELECT ST_Union_Agg(geometry) AS geom,
                   MIN(bbox.xmin) AS xmin, MIN(bbox.ymin) AS ymin,
                   MAX(bbox.xmax) AS xmax, MAX(bbox.ymax) AS ymax
            FROM read_parquet(?, hive_partitioning = 1)
            WHERE division_id = ?
            """,
            [f"{base}/theme=divisions/type=division_area/*.parquet", division_id],
        )
        area_expr = "geom" if xy_setting else "ST_FlipCoordinates(geom)"
        area, xmin, ymin, xmax, ymax = con.execute(
            f"SELECT ST_Area_Spheroid({area_expr}) / 1000000, xmin, ymin, xmax, ymax "
            "FROM rating_geometry"
        ).fetchone()
        if area is None:
            return {"population": division[0], "area_sq_km": None, "poi_count": None}

        poi_count = con.execute(
            """
            SELECT COUNT(*)
            FROM read_parquet(?, hive_partitioning = 1) p, rating_geometry g
            WHERE p.bbox.xmin >= ? AND p.bbox.ymin >= ?
              AND p.bbox.xmax <= ? AND p.bbox.ymax <= ?
              AND ST_Covers(g.geom, p.geometry)
            """,
            [f"{base}/theme=places/type=place/*.parquet", xmin, ymin, xmax, ymax],
        ).fetchone()[0]
        return {"population": division[0], "area_sq_km": area, "poi_count": poi_count}
    finally:
        con.close()
