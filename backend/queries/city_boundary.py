"""
Query Overture Maps divisions theme to get a city's greater metropolitan boundary.

Strategy: search across multiple division subtypes (county → municipality → locality)
and pick the LARGEST matching polygon by bbox area. This reliably captures the full
metro area rather than just the city centre.
"""

from typing import Optional
from queries import get_db, get_overture_base

# Subtypes searched in order — county/region-level first to prefer metro boundaries
METRO_SUBTYPES = ["county", "municipality", "locality", "region"]


def get_city_boundary(
    city_name: str,
    country_code: Optional[str] = None,
    subtype: Optional[str] = None,   # if None → auto-pick largest metro boundary
) -> Optional[dict]:
    """
    Returns:
        {
          division_id, city_name, country, subtype,
          bbox: {xmin, ymin, xmax, ymax},
          bbox_area_deg2: float   (bbox area in square degrees, for reference)
        }
    or None if not found.

    When subtype is None (default), searches across all metro-relevant subtypes
    and returns the candidate with the largest bounding-box area, which
    corresponds to the greater metropolitan area.
    """
    overture_base = get_overture_base()
    con = get_db()

    params: list = [city_name]

    # Build the subtype filter
    if subtype:
        subtype_filter = "AND d.subtype = ?"
        params.append(subtype)
    else:
        placeholders = ", ".join("?" for _ in METRO_SUBTYPES)
        subtype_filter = f"AND d.subtype IN ({placeholders})"
        params.extend(METRO_SUBTYPES)
    country_filter = ""
    if country_code:
        country_filter = "AND d.country = ?"
        params.append(country_code.upper())

    sql = f"""
        SELECT
            d.id               AS division_id,
            d.names.primary    AS city_name,
            d.country          AS country,
            d.subtype          AS subtype,
            a.bbox.xmin        AS xmin,
            a.bbox.ymin        AS ymin,
            a.bbox.xmax        AS xmax,
            a.bbox.ymax        AS ymax,
            -- bbox area in square degrees (larger = more metro-like)
            (a.bbox.xmax - a.bbox.xmin) * (a.bbox.ymax - a.bbox.ymin) AS bbox_area
        FROM
            read_parquet('{overture_base}/theme=divisions/type=division/*.parquet',
                         hive_partitioning = 1) d
        JOIN
            read_parquet('{overture_base}/theme=divisions/type=division_area/*.parquet',
                         hive_partitioning = 1) a
            ON d.id = a.division_id
        WHERE
            d.names.primary ILIKE ?
            {subtype_filter}
            {country_filter}
        ORDER BY bbox_area DESC   -- largest bbox = greatest metro coverage
        LIMIT 1
    """

    result = con.execute(sql, params).fetchone()
    con.close()

    if result is None:
        return None

    division_id, name, country, subtype_val, xmin, ymin, xmax, ymax, area = result
    return {
        "division_id": division_id,
        "city_name": name,
        "country": country,
        "subtype": subtype_val,
        "bbox": {"xmin": xmin, "ymin": ymin, "xmax": xmax, "ymax": ymax},
        "bbox_area_deg2": round(area, 6),
    }


def search_cities(
    city_name: str,
    country_code: Optional[str] = None,
    limit: int = 10,
) -> list[dict]:
    """
    Return up to `limit` matching cities, prioritizing closer name matches.
    """
    overture_base = get_overture_base()
    con = get_db()

    country_filter = ""
    params: list = [f"%{city_name}%"]

    placeholders = ", ".join("?" for _ in METRO_SUBTYPES)
    params.extend(METRO_SUBTYPES)
    if country_code:
        country_filter = "AND d.country = ?"
        params.append(country_code.upper())
    params.extend([city_name, f"{city_name}%"])
    params.append(limit)

    sql = f"""
        SELECT
            d.id               AS division_id,
            d.names.primary    AS city_name,
            d.country          AS country,
            d.subtype          AS subtype,
            (a.bbox.xmax - a.bbox.xmin) * (a.bbox.ymax - a.bbox.ymin) AS bbox_area
        FROM
            read_parquet('{overture_base}/theme=divisions/type=division/*.parquet',
                         hive_partitioning = 1) d
        JOIN
            read_parquet('{overture_base}/theme=divisions/type=division_area/*.parquet',
                         hive_partitioning = 1) a
            ON d.id = a.division_id
        WHERE
            d.names.primary ILIKE ?
            AND d.subtype IN ({placeholders})
            {country_filter}
        QUALIFY ROW_NUMBER() OVER (PARTITION BY d.id ORDER BY bbox_area DESC) = 1
        ORDER BY
            CASE
                WHEN lower(d.names.primary) = lower(?) THEN 0
                WHEN lower(d.names.primary) LIKE lower(?) THEN 1
                ELSE 2
            END,
            bbox_area DESC
        LIMIT ?
    """

    rows = con.execute(sql, params).fetchall()
    con.close()

    return [
        {
            "division_id": row[0],
            "city_name": row[1],
            "country": row[2],
            "subtype": row[3],
            "bbox_area_deg2": round(row[4], 6),
        }
        for row in rows
    ]
