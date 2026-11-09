import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import main
import snapshot_store


class SnapshotApiTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.path_patcher = patch.object(
            snapshot_store,
            "DATABASE_PATH",
            Path(self.temp_dir.name) / "snapshots.sqlite3",
        )
        self.path_patcher.start()
        snapshot_store.initialize_snapshot_db()

        self.boundary_patcher = patch.object(
            main,
            "get_city_boundary",
            return_value={
                "division_id": "division-1",
                "city_name": "Example City",
                "country": "EX",
                "subtype": "locality",
                "bbox": {"xmin": 1, "ymin": 2, "xmax": 3, "ymax": 4},
            },
        )
        self.boundary_patcher.start()
        self.release_patcher = patch.object(
            main,
            "get_overture_base",
            return_value="s3://overturemaps-us-west-2/release/2026-10-21.0",
        )
        self.release_patcher.start()
        for query_name in (
            "count_buildings",
            "count_transportation",
            "count_water",
            "count_infrastructure",
            "count_land_use",
            "count_places",
        ):
            patcher = patch.object(main, query_name, return_value=[{"label": "example", "count": 3}])
            patcher.start()
            self.addCleanup(patcher.stop)

    def tearDown(self):
        self.boundary_patcher.stop()
        self.release_patcher.stop()
        self.path_patcher.stop()
        self.temp_dir.cleanup()

    def test_explore_saves_snapshot_for_detail_latest_history_and_comparison(self):
        result = main.api_explore(main.ExploreRequest(city_name="Example City"))
        self.assertEqual(result.overture_release, "2026-10-21.0")
        self.assertEqual(result.buildings[0].count, 3)

        detail = main.api_snapshot(result.snapshot_id)
        latest = main.api_latest_snapshot("division-1")
        history = main.api_city_snapshots("division-1")
        self.assertEqual(detail["snapshot_id"], result.snapshot_id)
        self.assertEqual(latest["snapshot_id"], result.snapshot_id)
        self.assertEqual(len(history), 1)

        other = result.model_dump()
        other["city"]["division_id"] = "division-2"
        other["city"]["city_name"] = "Other City"
        other["captured_at"] = result.captured_at
        other_id = snapshot_store.save_snapshot(other, result.overture_release)
        comparison = main.api_compare_snapshots(["division-1", "division-2"])
        self.assertEqual(
            [snapshot["snapshot_id"] for snapshot in comparison],
            [result.snapshot_id, other_id],
        )

    def test_failed_explore_does_not_save_snapshot(self):
        with patch.object(main, "count_places", side_effect=RuntimeError("query failed")):
            with self.assertRaises(RuntimeError):
                main.api_explore(main.ExploreRequest(city_name="Example City"))

        self.assertEqual(main.api_city_snapshots("division-1"), [])
        self.assertEqual(main.api_saved_cities(), [])

    def test_saved_city_listing_uses_sqlite_not_overture_search(self):
        result = main.api_explore(main.ExploreRequest(city_name="Example City"))
        with patch.object(main, "search_cities", side_effect=AssertionError("unexpected Overture search")):
            cities = main.api_saved_cities()
        self.assertEqual(cities, [{
            "division_id": "division-1",
            "city_name": "Example City",
            "country": "EX",
            "subtype": "locality",
            "captured_at": result.captured_at,
        }])


if __name__ == "__main__":
    unittest.main()
