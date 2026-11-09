// Shared TypeScript types mirroring the FastAPI Pydantic models

export interface CategoryCount {
  label: string;
  count: number;
}

export interface CityBoundary {
  division_id: string;
  city_name: string;
  country: string | null;
  subtype: string;
  bbox: { xmin: number; ymin: number; xmax: number; ymax: number };
  bbox_area_deg2?: number;
}

export interface ExploreResult {
  city: CityBoundary;
  buildings: CategoryCount[];
  transportation: CategoryCount[];
  water: CategoryCount[];
  infrastructure: CategoryCount[];
  land_use: CategoryCount[];
  places: CategoryCount[];
}

export interface CitySnapshot extends ExploreResult {
  snapshot_id: number;
  captured_at: string;
  overture_release: string;
  schema_version: number;
}

export interface CitySearchResult {
  division_id: string;
  city_name: string;
  country: string | null;
  subtype: string;
  bbox_area_deg2: number;
}

export interface SavedCity {
  division_id: string;
  city_name: string;
  country: string | null;
  subtype: string;
  captured_at: string;
}

export interface CityRating {
  division_id: string;
  overture_release: string;
  population: number | null;
  area_sq_km: number | null;
  poi_count: number | null;
  per_10000_people: number | null;
  per_sq_km: number | null;
  score: number | null;
}

export interface LeaderboardEntry extends CityRating {
  city_name: string;
  country: string | null;
  subtype: string;
  snapshot_id: number;
  captured_at: string;
  population_score: number | null;
  area_score: number | null;
}

export type ExploreStatus = 'idle' | 'loading' | 'success' | 'error';
