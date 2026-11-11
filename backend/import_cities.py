"""Import full city snapshots from a CSV file into the app's SQLite database."""

import argparse
import csv
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

from main import explore_boundary
from queries import get_overture_base
from queries.import_lookup import find_city_boundaries, load_country_names, load_region_names
from ratings import load_rating_inputs
from snapshot_store import get_latest_snapshot, initialize_snapshot_db, save_snapshot


def parse_reload(value: str) -> bool:
    value = value.strip().casefold()
    if value in ("", "false", "no", "0"):
        return False
    if value in ("true", "yes", "1"):
        return True
    raise ValueError("reload must be true/false, yes/no, or 1/0")


def import_row(row: dict[str, str], countries: dict[str, set[str]]) -> str:
    city = (row.get("city") or "").strip()
    country = (row.get("country") or "").strip()
    state = (row.get("state") or "").strip()
    if not city or not country:
        raise ValueError("city and country are required")
    reload = parse_reload(row.get("reload") or "")
    country_codes = countries.get(country.casefold(), set())
    if not country_codes:
        raise ValueError(f"country not found: {country}")
    code = country.upper()
    if len(country) == 2 and code in country_codes:
        country_codes = {code}
    if len(country_codes) != 1:
        raise ValueError(f"ambiguous country: {country}; use a two-letter code")
    country_code = next(iter(country_codes))
    location = country_code
    if state:
        region_codes = load_region_names(country_code).get(state.casefold(), set())
        if not region_codes:
            raise ValueError(f"state not found: {state}, {country_code}")
        code = state.upper()
        if code in region_codes:
            region_codes = {code}
        if len(region_codes) != 1:
            raise ValueError(
                f"ambiguous state: {state}, {country_code}; use a region code: "
                f"{', '.join(sorted(region_codes))}"
            )
        region_code = next(iter(region_codes))
        location = f"{state}, {country_code}"
        candidates = find_city_boundaries(city, country_code, region_code)
    else:
        candidates = find_city_boundaries(city, country_code)
    if not candidates:
        raise ValueError(f"city not found: {city}, {location}")
    if len(candidates) != 1:
        localities = [candidate for candidate in candidates if candidate["subtype"] == "locality"]
        if len(localities) == 1:
            candidates = localities
        else:
            details = ", ".join(f"{c['division_id']} ({c['subtype']})" for c in candidates)
            raise ValueError(f"ambiguous city: {city}, {location}; candidates: {details}")

    boundary = candidates[0]
    division_id = boundary["division_id"]
    existing = get_latest_snapshot(division_id)
    if existing is not None and not reload:
        load_rating_inputs(division_id, existing["overture_release"])
        return "skipped"

    release = get_overture_base().rsplit("/", 1)[-1]
    result = explore_boundary(boundary)
    load_rating_inputs(division_id, release)
    captured_at = datetime.now(timezone.utc).isoformat(timespec="microseconds")
    save_snapshot({**result.model_dump(), "captured_at": captured_at}, release)
    return "imported"


def run_import(csv_path: Path, log_dir: Path) -> int:
    run_at = datetime.now(timezone.utc)
    log_dir.mkdir(parents=True, exist_ok=True)
    log_path = log_dir / f"city_import_failures_{run_at:%Y%m%dT%H%M%S_%fZ}.csv"
    counts = {"imported": 0, "skipped": 0, "failed": 0}
    with csv_path.open("r", encoding="utf-8-sig", newline="") as source, \
         log_path.open("x", encoding="utf-8", newline="") as failures:
        reader = csv.DictReader(source, strict=True)
        required = {"city", "country"}
        if not reader.fieldnames or not required.issubset(reader.fieldnames):
            raise ValueError("CSV must have city and country headers; state and reload are optional")
        if len(reader.fieldnames) != len(set(reader.fieldnames)):
            raise ValueError("CSV column headers must be unique")
        writer = csv.DictWriter(failures, fieldnames=[
            "run_timestamp_utc", "line", "city", "country", "state", "reload", "reason",
        ])
        writer.writeheader()
        failures.flush()
        print(f"Failure log: {log_path}")
        initialize_snapshot_db()
        countries = None
        while True:
            try:
                row = next(reader)
            except StopIteration:
                break
            except csv.Error as exc:
                counts["failed"] += 1
                line = reader.reader.line_num
                logging.error("CSV parsing failed on line %s: %s", line, exc)
                writer.writerow({
                    "run_timestamp_utc": run_at.isoformat(),
                    "line": line,
                    "reason": f"CSV parsing error: {exc}",
                })
                failures.flush()
                break
            line = reader.line_num
            try:
                if None in row:
                    raise ValueError("row has more values than CSV headers")
                if countries is None:
                    countries = load_country_names()
                status = import_row(row, countries)
                counts[status] += 1
                print(f"Line {line}: {status}: {row.get('city', '')}, {row.get('country', '')}")
            except Exception as exc:
                counts["failed"] += 1
                if isinstance(exc, ValueError):
                    logging.error("Line %s failed: %s", line, exc)
                else:
                    logging.exception("Line %s failed", line)
                writer.writerow({
                    "run_timestamp_utc": run_at.isoformat(),
                    "line": line,
                    "city": row.get("city", ""),
                    "country": row.get("country", ""),
                    "state": row.get("state", ""),
                    "reload": row.get("reload", ""),
                    "reason": f"{type(exc).__name__}: {exc}",
                })
                failures.flush()
    print(f"Imported: {counts['imported']}; skipped: {counts['skipped']}; failed: {counts['failed']}")
    return 1 if counts["failed"] else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "csv_file", type=Path, help="CSV file with city,country and optional state,reload columns",
    )
    parser.add_argument(
        "--log-dir", type=Path, default=Path(__file__).resolve().parent / "import_logs",
        help="directory for timestamped failure CSV files",
    )
    args = parser.parse_args()
    try:
        return run_import(args.csv_file, args.log_dir)
    except Exception:
        logging.exception("Import aborted")
        return 2


if __name__ == "__main__":
    sys.exit(main())
