"""
Count water features by class within a city bbox.
Source: Overture Maps — theme=base / type=water
"""

from queries import get_db, get_overture_base


def count_water(bbox: dict) -> list[dict]:
    """
    Returns [{"label": "lake", "count": 12}, ...]
    Groups by water class (lake, river, reservoir, canal, pond, etc.)
    """
    overture_base = get_overture_base()
    con = get_db()

    sql = f"""
        SELECT
            COALESCE(class, subtype, 'unknown') AS label,
            COUNT(*)                             AS count
        FROM
            read_parquet('{overture_base}/theme=base/type=water/*.parquet',
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
