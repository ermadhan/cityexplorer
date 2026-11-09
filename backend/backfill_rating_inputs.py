"""Populate historical rating inputs without modifying existing snapshots."""

import logging

from ratings import load_rating_inputs
from snapshot_store import initialize_snapshot_db, list_missing_rating_inputs


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    initialize_snapshot_db()
    pending = list_missing_rating_inputs()
    logging.info("Backfilling %d division/release pairs", len(pending))
    for division_id, release in pending:
        logging.info("Reading division %s from release %s", division_id, release)
        inputs = load_rating_inputs(division_id, release)
        logging.info("Saved inputs for %s: %s", division_id, inputs)


if __name__ == "__main__":
    main()
