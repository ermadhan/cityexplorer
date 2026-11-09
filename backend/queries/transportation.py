"""
Count road/transport segments by subclass within a city bbox.
Source: Overture Maps — theme=transportation / type=segment
"""

from queries import get_db, get_overture_base


def count_transportation(bbox: dict) -> list[dict]:
    """
    Returns [{"label": "primary", "count": 1234}, ...]
    Groups by subclass (road class). Excludes connectors (junction nodes).
    """
    overture_base = get_overture_base()
    con = get_db()

    sql = f"""
        SELECT
            COALESCE(subtype, class, 'unknown') AS label,
            COUNT(*)                             AS count
        FROM
            read_parquet('{overture_base}/theme=transportation/type=segment/*.parquet',
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
