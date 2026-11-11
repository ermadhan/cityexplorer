import csv
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import duckdb

import import_cities
import main
import snapshot_store
from queries import import_lookup


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

    def test_state_name_is_resolved_and_passed_to_city_lookup(self):
        with patch.object(import_cities, "load_region_names", return_value={
            "bihar": {"IN-BR"}, "in-br": {"IN-BR"},
        }), patch.object(import_cities, "find_city_boundaries", return_value=[]) as find_city:
            with self.assertRaisesRegex(ValueError, "city not found"):
                import_cities.import_row(
                    {"city": "Example", "country": "India", "state": " Bihar "},
                    COUNTRIES,
                )
        find_city.assert_called_once_with("Example", "IN", "IN-BR")

    def test_state_code_unknown_and_ambiguous_states(self):
        regions = {
            "in-br": {"IN-BR"},
            "shared": {"IN-BR", "IN-KA"},
        }
        with patch.object(import_cities, "load_region_names", return_value=regions) as load_regions, \
             patch.object(import_cities, "find_city_boundaries", return_value=[]) as find_city:
            with self.assertRaisesRegex(ValueError, "city not found"):
                import_cities.import_row(
                    {"city": "Example", "country": "India", "state": "in-br"}, COUNTRIES,
                )
            find_city.assert_called_once_with("Example", "IN", "IN-BR")
            with self.assertRaisesRegex(ValueError, "state not found: Unknown, IN"):
                import_cities.import_row(
                    {"city": "Example", "country": "India", "state": "Unknown"}, COUNTRIES,
                )
            with self.assertRaisesRegex(ValueError, "ambiguous state: shared, IN"):
                import_cities.import_row(
                    {"city": "Example", "country": "India", "state": "shared"}, COUNTRIES,
                )
            self.assertEqual(find_city.call_count, 1)
            load_regions.assert_called_with("IN")

    def test_state_failure_is_logged_and_processing_continues(self):
        input_path = self.root / "cities.csv"
        input_path.write_text(
            "city,country,state,reload\nMissing,India,Bihar,\nExample,India,,\n",
            encoding="utf-8",
        )
        with patch.object(import_cities, "load_country_names", return_value=COUNTRIES), \
             patch.object(import_cities, "load_region_names", return_value={"bihar": {"IN-BR"}}), \
             patch.object(import_cities, "find_city_boundaries", side_effect=[[], [BOUNDARY]]), \
             patch.object(import_cities, "get_overture_base", return_value="s3://bucket/release/2026-10-21.0"), \
             patch.object(import_cities, "explore_boundary", return_value=exploration()), \
             patch.object(import_cities, "load_rating_inputs"):
            self.assertEqual(import_cities.run_import(input_path, self.root / "logs"), 1)
        log_path = next((self.root / "logs").glob("*.csv"))
        with log_path.open(encoding="utf-8", newline="") as log:
            rows = list(csv.DictReader(log))
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["state"], "Bihar")
        self.assertIn("Missing, Bihar, IN", rows[0]["reason"])
        self.assertEqual(len(snapshot_store.get_city_snapshots("city-1")), 1)

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


class LookupQueryTests(unittest.TestCase):
   def setUp(self):
       self.temp = tempfile.TemporaryDirectory()
       self.addCleanup(self.temp.cleanup)
       root = Path(self.temp.name)
       divisions = root / "theme=divisions" / "type=division"
       areas = root / "theme=divisions" / "type=division_area"
       divisions.mkdir(parents=True)
       areas.mkdir(parents=True)
       con = duckdb.connect()
       try:
           con.execute("""
               CREATE TABLE divisions AS
               SELECT * FROM (VALUES
                   ('r1', 'Bihar', MAP {'en': 'Bihar State'}, 'IN', 'region', 'IN-BR'),
                   ('r2', 'Karnataka', MAP {'en': 'Karnataka'}, 'IN', 'region', 'IN-KA'),
                   ('r3', 'Bihar', MAP {'en': 'Bihar'}, 'XX', 'region', 'XX-BR'),
                   ('c1', 'Example', MAP {'en': 'Example'}, 'IN', 'locality', 'IN-BR'),
                   ('c2', 'Example', MAP {'en': 'Example'}, 'IN', 'locality', 'IN-KA'),
                   ('c3', 'Example', MAP {'en': 'Example'}, 'IN', 'locality', NULL),
                   ('c4', 'Example', MAP {'en': 'Example'}, 'IN', 'locality', 'IN-BR')
               ) AS d(id, primary_name, common_names, country, subtype, region)
           """)
           con.execute("""
               COPY (SELECT id, {'primary': primary_name, 'common': common_names} AS names,
                            country, subtype, region FROM divisions)
               TO ? (FORMAT PARQUET)
           """, [str(divisions / "part.parquet")])
           con.execute("""
               COPY (SELECT id AS division_id,
                            {'xmin': 1.0, 'ymin': 2.0, 'xmax': 3.0, 'ymax': 4.0} AS bbox
                     FROM divisions WHERE id IN ('c1', 'c2', 'c3'))
               TO ? (FORMAT PARQUET)
           """, [str(areas / "part.parquet")])
       finally:
           con.close()
       self.base = patch.object(import_lookup, "get_overture_base", return_value=str(root))
       self.db = patch.object(import_lookup, "get_db", side_effect=duckdb.connect)
       self.base.start()
       self.db.start()
       import_lookup.load_region_names.cache_clear()
       self.addCleanup(import_lookup.load_region_names.cache_clear)
       self.addCleanup(self.base.stop)
       self.addCleanup(self.db.stop)

   def test_region_names_are_country_scoped(self):
       names = import_lookup.load_region_names("IN")
       self.assertEqual(names["bihar"], {"IN-BR"})
       self.assertEqual(names["bihar state"], {"IN-BR"})
       self.assertEqual(names["in-ka"], {"IN-KA"})
       self.assertNotIn("xx-br", names)

   def test_city_lookup_filters_region_and_requires_area(self):
       all_candidates = import_lookup.find_city_boundaries("example", "IN")
       self.assertEqual({candidate["division_id"] for candidate in all_candidates}, {"c1", "c2", "c3"})
       bihar = import_lookup.find_city_boundaries("Example", "IN", "IN-BR")
       self.assertEqual([candidate["division_id"] for candidate in bihar], ["c1"])
       self.assertEqual(import_lookup.find_city_boundaries("Example", "IN", "IN-XX"), [])


if __name__ == "__main__":
    unittest.main()
