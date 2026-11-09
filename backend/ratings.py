"""Compute comparison-relative POI scores from cached historical inputs."""

import math
from typing import Any

from queries.rating_inputs import fetch_rating_inputs
from snapshot_store import get_rating_inputs, save_rating_inputs


def load_rating_inputs(division_id: str, release: str) -> dict[str, Any]:
    inputs = get_rating_inputs(division_id, release)
    if inputs is None:
        inputs = fetch_rating_inputs(division_id, release)
        save_rating_inputs(division_id, release, inputs)
    return inputs


def calculate_ratings(snapshots: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ratings = []
    for snapshot in snapshots:
        city = snapshot["city"]
        inputs = load_rating_inputs(city["division_id"], snapshot["overture_release"])
        population = inputs["population"]
        area = inputs["area_sq_km"]
        poi_count = inputs["poi_count"]
        population_ok = population is not None and population > 0
        area_ok = area is not None and math.isfinite(area) and area > 0
        count_ok = poi_count is not None and poi_count >= 0
        ratings.append({
            "division_id": city["division_id"],
            "overture_release": snapshot["overture_release"],
            "population": population,
            "area_sq_km": area if area_ok else None,
            "poi_count": poi_count,
            "per_10000_people": poi_count * 10000 / population if count_ok and population_ok else None,
            "per_sq_km": poi_count / area if count_ok and area_ok else None,
            "score": None,
        })

    eligible = [
        rating for rating in ratings
        if rating["per_10000_people"] is not None and rating["per_sq_km"] is not None
    ]
    if len(eligible) >= 2:
        max_population = max(rating["per_10000_people"] for rating in eligible)
        max_area = max(rating["per_sq_km"] for rating in eligible)
        for rating in eligible:
            population_score = 100 * rating["per_10000_people"] / max_population if max_population else 0
            area_score = 100 * rating["per_sq_km"] / max_area if max_area else 0
            rating["score"] = (population_score + area_score) / 2
    return ratings


def calculate_leaderboard(snapshots: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ratings = calculate_ratings(snapshots)
    for metric, score_name in (
        ("per_10000_people", "population_score"),
        ("per_sq_km", "area_score"),
    ):
        eligible = [rating for rating in ratings if rating[metric] is not None]
        maximum = max((rating[metric] for rating in eligible), default=0)
        for rating in ratings:
            rate = rating[metric]
            rating[score_name] = (
                (100 * rate / maximum if maximum else 0)
                if rate is not None and len(eligible) >= 2 else None
            )

    return [
        {
            **rating,
            "city_name": snapshot["city"]["city_name"],
            "country": snapshot["city"]["country"],
            "subtype": snapshot["city"]["subtype"],
            "snapshot_id": snapshot["snapshot_id"],
            "captured_at": snapshot["captured_at"],
        }
        for snapshot, rating in zip(snapshots, ratings)
    ]
