import type { CityRating, CitySearchResult, CitySnapshot, LeaderboardEntry, SavedCity } from '../types';

const BASE = '/api';

export async function getLeaderboard(): Promise<LeaderboardEntry[]> {
  const res = await fetch(`${BASE}/ratings/leaderboard`);
  if (!res.ok) {
    throw new Error(`Could not load the leaderboard (${res.status}). An Overture release may be unavailable.`);
  }
  return res.json();
}

/** List cities with a saved snapshot, using the latest metadata for each. */
export async function listSavedCities(): Promise<SavedCity[]> {
  const res = await fetch(`${BASE}/cities/saved`);
  if (!res.ok) throw new Error(`Could not load saved cities (${res.status})`);
  return res.json();
}

/** Search cities for autocomplete (GET /api/search?q=...) */
export async function searchCities(
  q: string,
  country?: string
): Promise<CitySearchResult[]> {
  const params = new URLSearchParams({ q, limit: '8' });
  if (country) params.set('country', country);
  const res = await fetch(`${BASE}/search?${params}`);
  if (!res.ok) throw new Error('Search failed');
  return res.json();
}

/** Full city exploration (POST /api/explore) */
export async function exploreCity(
  cityName: string,
  countryCode?: string,
  subtype?: string
): Promise<CitySnapshot> {
  const res = await fetch(`${BASE}/explore`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      city_name: cityName,
      country_code: countryCode ?? null,
      subtype: subtype ?? null,
    }),
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? `Explore failed (${res.status})`);
  }
  return res.json();
}

/** Fetch the latest saved snapshot for each selected division. */
export async function compareLatestSnapshots(
  divisionIds: string[]
): Promise<CitySnapshot[]> {
  const params = new URLSearchParams();
  divisionIds.forEach((divisionId) => params.append('division_id', divisionId));
  const res = await fetch(`${BASE}/snapshots/compare?${params}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? `Comparison failed (${res.status})`);
  }
  return res.json();
}

/** Rate the exact snapshots shown in a comparison. */
export async function compareRatings(snapshotIds: number[]): Promise<CityRating[]> {
  const params = new URLSearchParams();
  snapshotIds.forEach((id) => params.append('snapshot_id', String(id)));
  const res = await fetch(`${BASE}/ratings/compare?${params}`);
  if (!res.ok) throw new Error(`Could not calculate ratings (${res.status}). The recorded Overture release may be unavailable.`);
  return res.json();
}

/** List saved snapshots for one Overture division. */
export async function getCitySnapshotHistory(
  divisionId: string
): Promise<CitySnapshot[]> {
  const res = await fetch(`${BASE}/cities/${encodeURIComponent(divisionId)}/snapshots`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? `Snapshot history failed (${res.status})`);
  }
  return res.json();
}

/** Fetch one saved snapshot by its database ID. */
export async function getSnapshot(snapshotId: number): Promise<CitySnapshot> {
  const res = await fetch(`${BASE}/snapshots/${snapshotId}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? `Snapshot lookup failed (${res.status})`);
  }
  return res.json();
}
