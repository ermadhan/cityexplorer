"""
Shared DuckDB connection factory with S3 + spatial extensions loaded.
"""

import json
import re
from functools import lru_cache
from urllib.request import urlopen

import duckdb

OVERTURE_CATALOG = "https://stac.overturemaps.org/catalog.json"


@lru_cache(maxsize=1)
def get_overture_base() -> str:
    """Resolve and cache the latest Overture Maps release path."""
    with urlopen(OVERTURE_CATALOG, timeout=15) as response:
        catalog = json.load(response)

    release = catalog.get("latest")
    if not isinstance(release, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}\.\d+", release):
        raise ValueError("Overture Maps STAC catalog returned an invalid latest release.")

    return f"s3://overturemaps-us-west-2/release/{release}"


def get_db() -> duckdb.DuckDBPyConnection:
    """
    Return a new in-memory DuckDB connection with httpfs and spatial loaded.
    Each query module creates its own connection to avoid thread conflicts.
    """
    con = duckdb.connect(database=":memory:")
    con.execute("INSTALL httpfs; LOAD httpfs;")
    con.execute("INSTALL spatial; LOAD spatial;")
    con.execute("SET s3_region = 'us-west-2';")
    return con
