"""
Count buildings by class within a city bbox.
Source: Overture Maps — theme=buildings / type=building
"""

from queries import get_db, get_overture_base


def count_buildings(bbox: dict) -> list[dict]:
    """
    Returns [{"label": "residential", "count": 123456}, ...]
    sorted by count descending.
    """
    overture_base = get_overture_base()
    con = get_db()

    sql = f"""
        SELECT
            COALESCE(class, 'unknown') AS label,
            COUNT(*)                   AS count
        FROM
            read_parquet('{overture_base}/theme=buildings/type=building/*.parquet',
                         hive_partitioning = 1)
        WHERE
            bbox.xmin >= ?
            AND bbox.ymin >= ?
            AND bbox.xmax <= ?
            AND bbox.ymax <= ?
        GROUP BY class
        ORDER BY count DESC
    """

    rows = con.execute(sql, [
        bbox["xmin"], bbox["ymin"], bbox["xmax"], bbox["ymax"]
    ]).fetchall()
    con.close()

    return [{"label": row[0], "count": row[1]} for row in rows]
