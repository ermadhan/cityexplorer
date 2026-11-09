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

export type ExploreStatus = 'idle' | 'loading' | 'success' | 'error';
