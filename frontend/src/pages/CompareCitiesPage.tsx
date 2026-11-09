import { useState } from 'react';
import { AlertCircle, GitCompareArrows, Loader2, X } from 'lucide-react';
import { compareLatestSnapshots } from '../api/cityExplorer';
import SavedCitySearch from '../components/SavedCitySearch';
import CityRatings from '../components/CityRatings';
import type { CategoryCount, SavedCity, CitySnapshot, ExploreResult } from '../types';

const categories: {
  key: keyof Pick<
    ExploreResult,
    'buildings' | 'transportation' | 'water' | 'infrastructure' | 'land_use' | 'places'
  >;
  title: string;
  emoji: string;
}[] = [
  { key: 'buildings', title: 'Buildings', emoji: '🏗️' },
  { key: 'transportation', title: 'Roads & Transport', emoji: '🛣️' },
  { key: 'water', title: 'Water Bodies', emoji: '💧' },
  { key: 'infrastructure', title: 'Infrastructure', emoji: '🏭' },
  { key: 'land_use', title: 'Land Use Zones', emoji: '🌳' },
  { key: 'places', title: 'Places & POIs', emoji: '📍' },
];

function categoryCounts(
  snapshot: CitySnapshot,
  category: (typeof categories)[number]['key'],
): CategoryCount[] {
  return snapshot[category];
}

function CategoryComparison({
  title,
  emoji,
  category,
  snapshots,
}: {
  title: string;
  emoji: string;
  category: (typeof categories)[number]['key'];
  snapshots: CitySnapshot[];
}) {
  const counts = snapshots.map((snapshot) => new Map(
    categoryCounts(snapshot, category).map(({ label, count }) => [label, count]),
  ));
  const labels = Array.from(
    new Set(counts.flatMap((cityCounts) => Array.from(cityCounts.keys()))),
  ).sort((left, right) => {
    const leftMax = Math.max(...counts.map((cityCounts) => cityCounts.get(left) ?? 0));
    const rightMax = Math.max(...counts.map((cityCounts) => cityCounts.get(right) ?? 0));
    return rightMax - leftMax || left.localeCompare(right);
  });

  return (
    <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="border-b border-slate-100 px-5 py-4">
        <h3 className="font-semibold text-slate-800">{emoji} {title}</h3>
      </div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-max text-left text-sm">
          <thead className="bg-slate-50 text-slate-500">
            <tr>
              <th className="px-5 py-3 font-medium">Feature</th>
              {snapshots.map((snapshot) => (
                <th key={snapshot.snapshot_id} className="px-5 py-3 text-right font-medium">
                  {snapshot.city.city_name}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {labels.map((label) => (
              <tr key={label}>
                <th className="px-5 py-3 font-medium text-slate-700">{label}</th>
                {counts.map((cityCounts, index) => (
                  <td key={snapshots[index].snapshot_id} className="px-5 py-3 text-right tabular-nums text-slate-600">
                    {(cityCounts.get(label) ?? 0).toLocaleString()}
                  </td>
                ))}
              </tr>
            ))}
            {labels.length === 0 && (
              <tr>
                <td colSpan={snapshots.length + 1} className="px-5 py-6 text-center text-slate-400">
                  No category counts are available.
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}

export default function CompareCitiesPage() {
  const [cities, setCities] = useState<SavedCity[]>([]);
  const [snapshots, setSnapshots] = useState<CitySnapshot[] | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function addCity(city: SavedCity) {
    if (cities.some((selected) => selected.division_id === city.division_id)) {
      setError(`${city.city_name} is already in this comparison.`);
      return;
    }
    setCities((selected) => [...selected, city]);
    setSnapshots(null);
    setError(null);
  }

  function removeCity(divisionId: string) {
    setCities((selected) => selected.filter((city) => city.division_id !== divisionId));
    setSnapshots(null);
    setError(null);
  }

  async function handleCompare() {
    if (cities.length < 2 || cities.length > 4) return;
    setLoading(true);
    setSnapshots(null);
    setError(null);
    try {
      const data = await compareLatestSnapshots(cities.map((city) => city.division_id));
      setSnapshots(data);
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Could not load saved city snapshots.');
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="mx-auto max-w-6xl px-6 py-12">
      <section className="mb-8 text-center">
        <h2 className="text-3xl font-extrabold text-slate-800">Compare cities</h2>
        <p className="mx-auto mt-3 max-w-2xl text-slate-500">
          Compare feature counts from each city&apos;s latest saved Explore snapshot.
          Only cities saved in the local database are listed.
        </p>
      </section>

      <section className="mx-auto mb-8 max-w-3xl rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
        <div className="flex flex-col gap-3 sm:flex-row">
          <SavedCitySearch
            onSelect={addCity}
            selectedIds={cities.map((city) => city.division_id)}
            disabled={cities.length >= 4 || loading}
          />
          <button
            type="button"
            onClick={handleCompare}
            disabled={cities.length < 2 || loading}
            className="shrink-0 rounded-xl bg-indigo-500 px-5 py-3 font-semibold text-white shadow-sm transition-colors hover:bg-indigo-600 disabled:cursor-not-allowed disabled:opacity-40"
          >
            {loading
              ? <span className="flex items-center gap-2"><Loader2 size={18} className="animate-spin" /> Comparing…</span>
              : <span className="flex items-center gap-2"><GitCompareArrows size={18} /> Compare {cities.length > 0 ? `(${cities.length})` : ''}</span>}
          </button>
        </div>
        <p className="mt-2 text-sm text-slate-400">Choose 2–4 cities. Feature tables show raw bounding-box counts.</p>

        {cities.length > 0 && (
          <ul className="mt-4 flex flex-wrap gap-2">
            {cities.map((city) => (
              <li key={city.division_id} className="flex items-center gap-2 rounded-full bg-indigo-50 py-1.5 pl-3 pr-1.5 text-sm text-indigo-800">
                <span>{city.city_name}{city.country ? ` · ${city.country}` : ''}</span>
                <button
                  type="button"
                  aria-label={`Remove ${city.city_name}`}
                  onClick={() => removeCity(city.division_id)}
                  disabled={loading}
                  className="rounded-full p-1 hover:bg-indigo-100 disabled:opacity-50"
                >
                  <X size={14} />
                </button>
              </li>
            ))}
          </ul>
        )}
      </section>

      {error && (
        <div role="alert" className="mx-auto mb-6 flex max-w-3xl items-start gap-3 rounded-2xl border border-red-200 bg-red-50 p-4 text-red-700">
          <AlertCircle size={20} className="mt-0.5 shrink-0" />
          <p>{error}</p>
        </div>
      )}

      {snapshots && (
        <section className="flex flex-col gap-5">
          <CityRatings snapshots={snapshots} />
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {snapshots.map((snapshot) => (
              <article key={snapshot.snapshot_id} className="rounded-2xl border border-indigo-100 bg-indigo-50/70 p-4">
                <h3 className="font-semibold text-indigo-950">{snapshot.city.city_name}</h3>
                <p className="mt-1 text-sm text-indigo-800">
                  {snapshot.city.country ?? 'Country unknown'} · {snapshot.city.subtype}
                </p>
                <p className="mt-2 text-xs text-indigo-700">
                  Saved {new Date(snapshot.captured_at).toLocaleString()}
                </p>
                <p className="mt-1 text-xs text-indigo-700">Overture release {snapshot.overture_release}</p>
              </article>
            ))}
          </div>
          {categories.map((category) => (
            <CategoryComparison
              key={category.key}
              title={category.title}
              emoji={category.emoji}
              category={category.key}
              snapshots={snapshots}
            />
          ))}
        </section>
      )}
    </main>
  );
}
