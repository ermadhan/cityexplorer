import unittest
from unittest.mock import patch

from fastapi import HTTPException

import main
from ratings import calculate_leaderboard, calculate_ratings, load_rating_inputs


def snapshot(division_id):
    return {"city": {"division_id": division_id}, "overture_release": "2026-10-21.0"}


class RatingTests(unittest.TestCase):
    def test_equal_weight_relative_score(self):
        inputs = {
            "a": {"population": 1000, "area_sq_km": 100.0, "poi_count": 100},
            "b": {"population": 1000, "area_sq_km": 25.0, "poi_count": 50},
            "missing": {"population": None, "area_sq_km": 20.0, "poi_count": 20},
        }
        with patch("ratings.load_rating_inputs", side_effect=lambda city, release: inputs[city]):
            result = calculate_ratings([snapshot("a"), snapshot("b"), snapshot("missing")])
        self.assertEqual(result[0]["per_10000_people"], 1000)
        self.assertEqual(result[0]["per_sq_km"], 1)
        self.assertEqual(result[0]["score"], 75)
        self.assertEqual(result[1]["score"], 75)
        self.assertIsNone(result[2]["score"])
        self.assertEqual(result[2]["per_sq_km"], 1)

    def test_fewer_than_two_eligible_and_zero_denominators(self):
        inputs = [
            {"population": 100, "area_sq_km": 10, "poi_count": 5},
            {"population": 0, "area_sq_km": 0, "poi_count": 5},
        ]
        with patch("ratings.load_rating_inputs", side_effect=inputs):
            result = calculate_ratings([snapshot("a"), snapshot("b")])
        self.assertIsNone(result[0]["score"])
        self.assertIsNone(result[1]["score"])
        self.assertIsNone(result[1]["per_10000_people"])
        self.assertIsNone(result[1]["per_sq_km"])

    def test_zero_poi_counts_have_zero_scores(self):
        inputs = {"population": 100, "area_sq_km": 10, "poi_count": 0}
        with patch("ratings.load_rating_inputs", return_value=inputs):
            result = calculate_ratings([snapshot("a"), snapshot("b")])
        self.assertEqual([item["score"] for item in result], [0, 0])

    def test_cache_uses_snapshot_release_and_does_not_cache_failures(self):
        with patch("ratings.get_rating_inputs", return_value=None), \
             patch("ratings.fetch_rating_inputs", side_effect=RuntimeError("unavailable")) as fetch, \
             patch("ratings.save_rating_inputs") as save:
            with self.assertRaises(RuntimeError):
                load_rating_inputs("a", "2026-10-21.0")
            fetch.assert_called_once_with("a", "2026-10-21.0")
            save.assert_not_called()

    def test_api_scores_exact_snapshot_ids_and_rejects_duplicate_city(self):
        snapshots = [snapshot("a"), snapshot("b")]
        with patch.object(main, "get_snapshot", side_effect=snapshots), \
             patch.object(main, "calculate_ratings", return_value=[]) as calculate:
            self.assertEqual(main.api_compare_ratings([10, 20]), [])
            calculate.assert_called_once_with(snapshots)
        with patch.object(main, "get_snapshot", side_effect=[snapshot("a"), snapshot("a")]):
            with self.assertRaises(HTTPException) as error:
                main.api_compare_ratings([10, 11])
            self.assertEqual(error.exception.status_code, 400)

    def test_api_rejects_missing_snapshot(self):
        with patch.object(main, "get_snapshot", side_effect=[snapshot("a"), None]):
            with self.assertRaises(HTTPException) as error:
                main.api_compare_ratings([10, 20])
            self.assertEqual(error.exception.status_code, 404)

    def test_leaderboard_uses_each_metric_eligible_population(self):
        snapshots = []
        for index, city in enumerate(("a", "b", "c"), 1):
            snapshots.append({
                "city": {"division_id": city, "city_name": city, "country": None, "subtype": "locality"},
                "overture_release": "2026-10-21.0",
                "captured_at": "2026-11-09T12:00:00+00:00",
                "snapshot_id": index,
            })
        inputs = {
            "a": {"population": 1000, "area_sq_km": 100.0, "poi_count": 100},
            "b": {"population": 1000, "area_sq_km": 25.0, "poi_count": 50},
            "c": {"population": None, "area_sq_km": 1.0, "poi_count": 100},
        }
        with patch("ratings.load_rating_inputs", side_effect=lambda city, release: inputs[city]):
            result = calculate_leaderboard(snapshots)
        self.assertEqual([item["score"] for item in result], [75, 75, None])
        self.assertEqual([item["population_score"] for item in result], [100, 50, None])
        self.assertEqual([item["area_score"] for item in result], [1, 2, 100])
        self.assertEqual([item["snapshot_id"] for item in result], [1, 2, 3])

    def test_individual_scores_require_two_eligible_cities(self):
        snapshots = [{
            **snapshot("a"),
            "city": {"division_id": "a", "city_name": "A", "country": None, "subtype": "locality"},
            "captured_at": "2026-11-09T12:00:00+00:00",
            "snapshot_id": 1,
        }]
        with patch("ratings.load_rating_inputs", return_value={"population": 100, "area_sq_km": 10, "poi_count": 0}):
            entry = calculate_leaderboard(snapshots)[0]
        self.assertIsNone(entry["score"])
        self.assertIsNone(entry["area_score"])
        self.assertIsNone(entry["population_score"])
        self.assertEqual(entry["per_sq_km"], 0)
        self.assertEqual(calculate_leaderboard([]), [])

    def test_leaderboard_api_uses_latest_for_every_saved_city(self):
        saved = [{"division_id": "a"}, {"division_id": "b"}]
        snapshots = [snapshot("a"), snapshot("b")]
        with patch.object(main, "list_saved_cities", return_value=saved), \
             patch.object(main, "get_latest_snapshot", side_effect=snapshots) as latest, \
             patch.object(main, "calculate_leaderboard", return_value=[]) as calculate:
            self.assertEqual(main.api_leaderboard(), [])
            self.assertEqual(latest.call_count, 2)
            calculate.assert_called_once_with(snapshots)


if __name__ == "__main__":
    unittest.main()
