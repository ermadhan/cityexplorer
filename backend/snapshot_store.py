"""SQLite persistence for successful city exploration snapshots."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

DATABASE_PATH = Path(__file__).resolve().parent / "city_snapshots.sqlite3"
SNAPSHOT_SCHEMA_VERSION = 1
CATEGORIES = (
    "buildings",
    "transportation",
    "water",
    "infrastructure",
    "land_use",
    "places",
)


@contextmanager
def _connect() -> Iterator[sqlite3.Connection]:
    DATABASE_PATH.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(DATABASE_PATH, timeout=30)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def initialize_snapshot_db() -> None:
    with _connect() as connection:
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                division_id TEXT NOT NULL,
                city_name TEXT NOT NULL,
                country TEXT,
                subtype TEXT NOT NULL,
                bbox_xmin REAL NOT NULL,
                bbox_ymin REAL NOT NULL,
                bbox_xmax REAL NOT NULL,
                bbox_ymax REAL NOT NULL,
                overture_release TEXT NOT NULL,
                schema_version INTEGER NOT NULL,
                captured_at TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS snapshots_by_division
            ON snapshots (division_id, captured_at DESC, id DESC);

            CREATE TABLE IF NOT EXISTS category_counts (
                snapshot_id INTEGER NOT NULL
                    REFERENCES snapshots (id) ON DELETE CASCADE,
                category TEXT NOT NULL,
                label TEXT NOT NULL,
                count INTEGER NOT NULL CHECK (count >= 0),
                PRIMARY KEY (snapshot_id, category, label)
            );
            """
        )


def save_snapshot(explore_result: dict[str, Any], overture_release: str) -> int:
    city = explore_result["city"]
    bbox = city["bbox"]
    with _connect() as connection:
        cursor = connection.execute(
            """
            INSERT INTO snapshots (
                division_id, city_name, country, subtype,
                bbox_xmin, bbox_ymin, bbox_xmax, bbox_ymax,
                overture_release, schema_version, captured_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                city["division_id"],
                city["city_name"],
                city["country"],
                city["subtype"],
                bbox["xmin"],
                bbox["ymin"],
                bbox["xmax"],
                bbox["ymax"],
                overture_release,
                SNAPSHOT_SCHEMA_VERSION,
                explore_result["captured_at"],
            ),
        )
        snapshot_id = cursor.lastrowid
        connection.executemany(
            """
            INSERT INTO category_counts (snapshot_id, category, label, count)
            VALUES (?, ?, ?, ?)
            """,
            (
                (snapshot_id, category, item["label"], item["count"])
                for category in CATEGORIES
                for item in explore_result[category]
            ),
        )
    return snapshot_id


def _snapshot_from_row(
    connection: sqlite3.Connection, row: sqlite3.Row
) -> dict[str, Any]:
    snapshot: dict[str, Any] = {
        "snapshot_id": row["id"],
        "captured_at": row["captured_at"],
        "overture_release": row["overture_release"],
        "schema_version": row["schema_version"],
        "city": {
            "division_id": row["division_id"],
            "city_name": row["city_name"],
            "country": row["country"],
            "subtype": row["subtype"],
            "bbox": {
                "xmin": row["bbox_xmin"],
                "ymin": row["bbox_ymin"],
                "xmax": row["bbox_xmax"],
                "ymax": row["bbox_ymax"],
            },
        },
    }
    snapshot.update({category: [] for category in CATEGORIES})

    counts = connection.execute(
        """
        SELECT category, label, count
        FROM category_counts
        WHERE snapshot_id = ?
        ORDER BY category, count DESC, label
        """,
        (row["id"],),
    )
    for count in counts:
        snapshot[count["category"]].append(
            {"label": count["label"], "count": count["count"]}
        )
    return snapshot


def get_snapshot(snapshot_id: int) -> dict[str, Any] | None:
    with _connect() as connection:
        row = connection.execute(
            "SELECT * FROM snapshots WHERE id = ?", (snapshot_id,)
        ).fetchone()
        return _snapshot_from_row(connection, row) if row else None


def get_latest_snapshot(division_id: str) -> dict[str, Any] | None:
    with _connect() as connection:
        row = connection.execute(
            """
            SELECT * FROM snapshots
            WHERE division_id = ?
            ORDER BY captured_at DESC, id DESC
            LIMIT 1
            """,
            (division_id,),
        ).fetchone()
        return _snapshot_from_row(connection, row) if row else None


def get_city_snapshots(division_id: str) -> list[dict[str, Any]]:
    with _connect() as connection:
        rows = connection.execute(
            """
            SELECT * FROM snapshots
            WHERE division_id = ?
            ORDER BY captured_at DESC, id DESC
            """,
            (division_id,),
        ).fetchall()
        return [_snapshot_from_row(connection, row) for row in rows]


def list_saved_cities() -> list[dict[str, Any]]:
    with _connect() as connection:
        rows = connection.execute(
            """
            SELECT division_id, city_name, country, subtype, captured_at
            FROM (
                SELECT division_id, city_name, country, subtype, captured_at,
                    ROW_NUMBER() OVER (
                        PARTITION BY division_id
                        ORDER BY captured_at DESC, id DESC
                    ) AS position
                FROM snapshots
            )
            WHERE position = 1
            ORDER BY city_name COLLATE NOCASE, country COLLATE NOCASE, division_id
            """
        ).fetchall()
        return [dict(row) for row in rows]


def get_latest_snapshots(division_ids: list[str]) -> list[dict[str, Any] | None]:
    return [get_latest_snapshot(division_id) for division_id in division_ids]
