import type { CitySearchResult, ExploreResult } from '../types';

const BASE = '/api';

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
): Promise<ExploreResult> {
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
