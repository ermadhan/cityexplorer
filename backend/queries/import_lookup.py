"""Exact country, region, and city lookups for the CSV importer."""

from functools import lru_cache

from queries import get_db, get_overture_base
from queries.city_boundary import METRO_SUBTYPES


def load_country_names() -> dict[str, set[str]]:
    base = get_overture_base()
    con = get_db()
    try:
        rows = con.execute(
            """SELECT country, names.primary, names.common
               FROM read_parquet(?, hive_partitioning = 1)
               WHERE subtype = 'country' AND country IS NOT NULL""",
            [f"{base}/theme=divisions/type=division/*.parquet"],
        ).fetchall()
    finally:
        con.close()

    names: dict[str, set[str]] = {}
    for code, primary, common in rows:
        for name in [code, primary, *(common or {}).values()]:
            if name:
                names.setdefault(name.strip().casefold(), set()).add(code)
    return names


@lru_cache(maxsize=None)
def load_region_names(country_code: str) -> dict[str, set[str]]:
    base = get_overture_base()
    con = get_db()
    try:
        rows = con.execute(
            """SELECT region, names.primary, names.common
               FROM read_parquet(?, hive_partitioning = 1)
               WHERE subtype = 'region' AND country = ? AND region IS NOT NULL""",
            [f"{base}/theme=divisions/type=division/*.parquet", country_code],
        ).fetchall()
    finally:
        con.close()

    names: dict[str, set[str]] = {}
    for code, primary, common in rows:
        for name in [code, primary, *(common or {}).values()]:
            if name:
                names.setdefault(name.strip().casefold(), set()).add(code)
    return names


def find_city_boundaries(
    city_name: str, country_code: str, region_code: str | None = None,
) -> list[dict]:
    base = get_overture_base()
    con = get_db()
    try:
        placeholders = ", ".join("?" for _ in METRO_SUBTYPES)
        region_filter = "AND d.region = ?" if region_code else ""
        params = [
            f"{base}/theme=divisions/type=division/*.parquet",
            f"{base}/theme=divisions/type=division_area/*.parquet",
            city_name, country_code, *METRO_SUBTYPES,
        ]
        if region_code:
            params.append(region_code)
        rows = con.execute(
            f"""
            SELECT d.id, d.names.primary, d.country, d.subtype,
                   a.bbox.xmin, a.bbox.ymin, a.bbox.xmax, a.bbox.ymax
            FROM read_parquet(?, hive_partitioning = 1) d
            JOIN read_parquet(?, hive_partitioning = 1) a ON d.id = a.division_id
            WHERE lower(d.names.primary) = lower(?)
              AND d.country = ? AND d.subtype IN ({placeholders})
              {region_filter}
            QUALIFY ROW_NUMBER() OVER (
                PARTITION BY d.id
                ORDER BY (a.bbox.xmax - a.bbox.xmin) * (a.bbox.ymax - a.bbox.ymin) DESC
            ) = 1
            ORDER BY d.id
            """,
            params,
        ).fetchall()
    finally:
        con.close()

    return [
        {
            "division_id": row[0],
            "city_name": row[1],
            "country": row[2],
            "subtype": row[3],
            "bbox": {"xmin": row[4], "ymin": row[5], "xmax": row[6], "ymax": row[7]},
        }
        for row in rows
    ]
