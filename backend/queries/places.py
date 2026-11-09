"""
Count Places (POIs) by top-level taxonomy category within a city bbox.
Source: Overture Maps — theme=places / type=place
"""

from queries import get_db, get_overture_base


def count_places(bbox: dict) -> list[dict]:
    """
    Returns [{"label": "food_and_drink", "count": 3200}, ...]
    Groups by the top-level (L0) taxonomy category.

    Overture taxonomy.hierarchy is an array; the first element is the
    broadest category (e.g. "food_and_drink", "health_and_medicine", etc.)
    """
    overture_base = get_overture_base()
    con = get_db()

    sql = f"""
        SELECT
            COALESCE(
                taxonomy.hierarchy[1],   -- first (broadest) hierarchy level
                taxonomy.primary,        -- fallback when no hierarchy is assigned
                'unknown'
            )                            AS label,
            COUNT(*)                     AS count
        FROM
            read_parquet('{overture_base}/theme=places/type=place/*.parquet',
                         hive_partitioning = 1)
        WHERE
            bbox.xmin >= ?
            AND bbox.ymin >= ?
            AND bbox.xmax <= ?
            AND bbox.ymax <= ?
        GROUP BY label
        ORDER BY count DESC
    """

    rows = con.execute(sql, [
        bbox["xmin"], bbox["ymin"], bbox["xmax"], bbox["ymax"]
    ]).fetchall()
    con.close()

    return [{"label": row[0], "count": row[1]} for row in rows]
