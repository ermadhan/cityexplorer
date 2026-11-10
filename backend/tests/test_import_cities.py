import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import import_cities
import main
import snapshot_store


BOUNDARY = {
    "division_id": "city-1",
    "city_name": "Example",
    "country": "IN",
    "subtype": "locality",
    "bbox": {"xmin": 1, "ymin": 2, "xmax": 3, "ymax": 4},
}
COUNTRIES = {"india": {"IN"}, "in": {"IN"}}


def exploration():
    return main.ExploreResult(
        city=BOUNDARY,
        buildings=[{"label": "building", "count": 1}],
        transportation=[],
        water=[],
        infrastructure=[],
        land_use=[],
        places=[{"label": "food", "count": 2}],
    )


class ImportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.db = patch.object(snapshot_store, "DATABASE_PATH", self.root / "test.sqlite3")
        self.db.start()
        snapshot_store.initialize_snapshot_db()
        self.addCleanup(self.temp.cleanup)
        self.addCleanup(self.db.stop)

    def test_import_skip_reload_and_rating_backfill(self):
        with patch.object(import_cities, "find_city_boundaries", return_value=[BOUNDARY]), \
             patch.object(import_cities, "get_overture_base", return_value="s3://bucket/release/2026-10-21.0"), \
             patch.object(import_cities, "explore_boundary", return_value=exploration()) as explore, \
             patch.object(import_cities, "load_rating_inputs") as ratings:
            row = {"city": "Example", "country": "India"}
            self.assertEqual(import_cities.import_row(row, COUNTRIES), "imported")
            self.assertEqual(import_cities.import_row(row, COUNTRIES), "skipped")
            self.assertEqual(import_cities.import_row({**row, "reload": "YES"}, COUNTRIES), "imported")
            self.assertEqual(explore.call_count, 2)
            self.assertEqual(len(snapshot_store.get_city_snapshots("city-1")), 2)
            self.assertEqual(ratings.call_count, 3)
            ratings.assert_called_with("city-1", "2026-10-21.0")

    def test_failed_rating_never_creates_snapshot(self):
        with patch.object(import_cities, "find_city_boundaries", return_value=[BOUNDARY]), \
             patch.object(import_cities, "get_overture_base", return_value="s3://bucket/release/2026-10-21.0"), \
             patch.object(import_cities, "explore_boundary", return_value=exploration()), \
             patch.object(import_cities, "load_rating_inputs", side_effect=RuntimeError("network failure")):
            with self.assertRaises(RuntimeError):
                import_cities.import_row({"city": "Example", "country": "IN"}, COUNTRIES)
        self.assertEqual(snapshot_store.get_city_snapshots("city-1"), [])

    def test_log_invalid_missing_ambiguous_and_processing_failures_and_continue(self):
        input_path = self.root / "cities.csv"
        input_path.write_text(
            "city,country,reload\nMissing,India,\nAmbiguous,India,\nBad,India,maybe\nFail,India,\nExample,IN,\n",
            encoding="utf-8",
        )

        def find_city(city, country):
            if city == "Missing":
                return []
            if city == "Ambiguous":
                return [BOUNDARY, {**BOUNDARY, "division_id": "city-2"}]
            if city == "Fail":
                raise RuntimeError("network down")
            return [BOUNDARY]

        with patch.object(import_cities, "load_country_names", return_value=COUNTRIES), \
             patch.object(import_cities, "find_city_boundaries", side_effect=find_city), \
             patch.object(import_cities, "get_overture_base", return_value="s3://bucket/release/2026-10-21.0"), \
             patch.object(import_cities, "explore_boundary", return_value=exploration()), \
             patch.object(import_cities, "load_rating_inputs"):
            self.assertEqual(import_cities.run_import(input_path, self.root / "logs"), 1)

        logs = list((self.root / "logs").glob("city_import_failures_*.csv"))
        self.assertEqual(len(logs), 1)
        with logs[0].open(encoding="utf-8", newline="") as log:
            rows = list(csv.DictReader(log))
        self.assertEqual([row["city"] for row in rows], ["Missing", "Ambiguous", "Bad", "Fail"])
        self.assertTrue(all(row["run_timestamp_utc"] for row in rows))
        self.assertIn("ambiguous city", rows[1]["reason"])
        self.assertIn("network down", rows[3]["reason"])
        self.assertEqual(len(snapshot_store.get_city_snapshots("city-1")), 1)

    def test_invalid_country_and_flags(self):
        with self.assertRaisesRegex(ValueError, "country not found"):
            import_cities.import_row({"city": "Example", "country": "Nowhere"}, COUNTRIES)
        with self.assertRaisesRegex(ValueError, "ambiguous country"):
            import_cities.import_row({"city": "Example", "country": "Congo"}, {"congo": {"CG", "CD"}})
        for value in ("false", "NO", "0", ""):
            self.assertFalse(import_cities.parse_reload(value))
        for value in ("true", "YES", "1"):
            self.assertTrue(import_cities.parse_reload(value))
        with self.assertRaises(ValueError):
            import_cities.parse_reload("sometimes")

    def test_country_code_takes_priority_over_name_collision(self):
        with patch.object(import_cities, "find_city_boundaries", return_value=[]) as find_city:
            with self.assertRaisesRegex(ValueError, "city not found"):
                import_cities.import_row({"city": "Example", "country": "in"}, {"in": {"IN", "XX"}})
        find_city.assert_called_once_with("Example", "IN")

    def test_country_lookup_failure_logged_for_each_row(self):
        input_path = self.root / "cities.csv"
        input_path.write_text("city,country\nA,India\nB,India\n", encoding="utf-8")
        with patch.object(import_cities, "load_country_names", side_effect=RuntimeError("country data unavailable")):
            self.assertEqual(import_cities.run_import(input_path, self.root / "logs"), 1)
        log_path = next((self.root / "logs").glob("*.csv"))
        with log_path.open(encoding="utf-8", newline="") as log:
            rows = list(csv.DictReader(log))
        self.assertEqual([row["city"] for row in rows], ["A", "B"])
        self.assertTrue(all("country data unavailable" in row["reason"] for row in rows))

    def test_malformed_csv_is_logged_and_returns_failure(self):
        input_path = self.root / "cities.csv"
        input_path.write_text('city,country\n"unclosed,India\n', encoding="utf-8")
        with patch.object(import_cities, "load_country_names", return_value=COUNTRIES):
            self.assertEqual(import_cities.run_import(input_path, self.root / "logs"), 1)
        log_path = next((self.root / "logs").glob("*.csv"))
        with log_path.open(encoding="utf-8", newline="") as log:
            rows = list(csv.DictReader(log))
        self.assertEqual(len(rows), 1)
        self.assertIn("CSV parsing error", rows[0]["reason"])
        self.assertEqual(rows[0]["line"], "2")


if __name__ == "__main__":
    unittest.main()
