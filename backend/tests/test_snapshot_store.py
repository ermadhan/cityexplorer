import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import snapshot_store


def sample_result():
    return {
        "captured_at": "2026-11-09T12:00:00+00:00",
        "city": {
            "division_id": "division-1",
            "city_name": "Example City",
            "country": "EX",
            "subtype": "locality",
            "bbox": {"xmin": 1, "ymin": 2, "xmax": 3, "ymax": 4},
        },
        "buildings": [{"label": "residential", "count": 10}],
        "transportation": [{"label": "primary", "count": 5}],
        "water": [],
        "infrastructure": [],
        "land_use": [],
        "places": [{"label": "food", "count": 8}],
    }


class SnapshotStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.database_path = Path(self.temp_dir.name) / "snapshots.sqlite3"
        self.path_patcher = patch.object(snapshot_store, "DATABASE_PATH", self.database_path)
        self.path_patcher.start()
        snapshot_store.initialize_snapshot_db()

    def tearDown(self):
        self.path_patcher.stop()
        self.temp_dir.cleanup()

    def test_saves_and_retrieves_complete_snapshot_history(self):
        first_id = snapshot_store.save_snapshot(sample_result(), "2026-10-21.0")
        second = sample_result()
        second["captured_at"] = "2026-11-10T12:00:00+00:00"
        second_id = snapshot_store.save_snapshot(second, "2026-11-04.0")

        self.assertEqual(snapshot_store.get_snapshot(first_id)["places"][0]["count"], 8)
        self.assertEqual(
            snapshot_store.get_latest_snapshot("division-1")["snapshot_id"],
            second_id,
        )
        self.assertEqual(
            [row["snapshot_id"] for row in snapshot_store.get_city_snapshots("division-1")],
            [second_id, first_id],
        )
        self.assertEqual(
            [row["snapshot_id"] for row in snapshot_store.get_latest_snapshots(["division-1"])],
            [second_id],
        )

    def test_failed_count_insert_rolls_back_snapshot(self):
        invalid_result = sample_result()
        invalid_result["places"] = [{"label": "food"}]

        with self.assertRaises(KeyError):
            snapshot_store.save_snapshot(invalid_result, "2026-10-21.0")

        self.assertEqual(snapshot_store.get_city_snapshots("division-1"), [])

    def test_list_saved_cities_returns_latest_metadata_per_division(self):
        self.assertEqual(snapshot_store.list_saved_cities(), [])

        older = sample_result()
        snapshot_store.save_snapshot(older, "2026-10-21.0")
        latest = sample_result()
        latest["city"]["city_name"] = "Renamed City"
        latest["city"]["subtype"] = "municipality"
        latest["captured_at"] = "2026-11-10T12:00:00+00:00"
        snapshot_store.save_snapshot(latest, "2026-10-21.0")
        same_time = sample_result()
        same_time["city"]["city_name"] = "Newest Name"
        same_time["captured_at"] = latest["captured_at"]
        snapshot_store.save_snapshot(same_time, "2026-10-21.0")

        other = sample_result()
        other["city"]["division_id"] = "division-2"
        other["city"]["city_name"] = "Another City"
        other["city"]["country"] = None
        snapshot_store.save_snapshot(other, "2026-10-21.0")

        cities = snapshot_store.list_saved_cities()
        self.assertEqual([city["division_id"] for city in cities], ["division-2", "division-1"])
        self.assertEqual(cities[0]["country"], None)
        self.assertEqual(cities[1], {
            "division_id": "division-1",
            "city_name": "Newest Name",
            "country": "EX",
            "subtype": "locality",
            "captured_at": "2026-11-10T12:00:00+00:00",
        })

    def test_historical_rating_backfill_does_not_modify_snapshots(self):
        result = sample_result()
        snapshot_id = snapshot_store.save_snapshot(result, "2026-10-21.0")
        self.assertEqual(snapshot_store.list_missing_rating_inputs(), [("division-1", "2026-10-21.0")])
        inputs = {"population": None, "area_sq_km": 20.5, "poi_count": 42}
        snapshot_store.save_rating_inputs("division-1", "2026-10-21.0", inputs)
        self.assertEqual(snapshot_store.get_rating_inputs("division-1", "2026-10-21.0"), inputs)
        self.assertEqual(snapshot_store.list_missing_rating_inputs(), [])
        self.assertEqual(snapshot_store.get_snapshot(snapshot_id)["places"], result["places"])


if __name__ == "__main__":
    unittest.main()
