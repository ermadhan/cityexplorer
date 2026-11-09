"""
Count land use zones by subtype within a city bbox.
Source: Overture Maps — theme=base / type=land_use
"""

from queries import get_db, get_overture_base


def count_land_use(bbox: dict) -> list[dict]:
    """
    Returns [{"label": "residential", "count": 8400}, ...]
    Groups by subtype (residential, education, park, military, industrial, etc.)
    """
    overture_base = get_overture_base()
    con = get_db()

    sql = f"""
        SELECT
            COALESCE(subtype, class, 'unknown') AS label,
            COUNT(*)                             AS count
        FROM
            read_parquet('{overture_base}/theme=base/type=land_use/*.parquet',
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
