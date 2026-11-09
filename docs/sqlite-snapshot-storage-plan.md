# SQLite City Snapshot Storage Plan

## Status

Implemented. Successful Explore City requests are recorded in the backend SQLite
database, and the Compare cities screen uses each selected city's latest saved
snapshot.

## Agreed scope

- Store a snapshot only after an Explore City request completes successfully.
- Keep every successful query as a timestamped snapshot; do not overwrite prior
  snapshots. Retain snapshots indefinitely.
- Group snapshots by Overture division ID.
- Use a backend-owned SQLite database file that is local and excluded from
  version control. The initial deployment target is a single backend instance.
- Store normalized category-count rows linked to each snapshot.
- Record the query timestamp, city identity (division ID, city name, country,
  subtype), returned boundary bounding box, Overture Maps release/version, and
  application/query schema version.
- Do not backfill historical data; begin capturing future successful queries.
- Add API support to fetch a complete snapshot, fetch the latest snapshot for a
  city, and list that city's snapshot history.
- Add a comparison API and screen that searches and compares 2–4 cities using
  their latest saved snapshots across all six feature categories.
- Keep calculations out of the initial implementation because their formulas
  are not defined yet. When defined, persist calculated metrics separately;
  the data model retains each city's history for future time-based comparisons.

## Completion criteria

- Successful explorations are persisted atomically with all their category
  counts and metadata.
- Failed or incomplete explorations do not create snapshots.
- Snapshot detail, latest snapshot, city history, and latest-snapshot city
  comparisons can be retrieved through the API.
- Repeated queries for one division preserve all snapshots in timestamp order.
