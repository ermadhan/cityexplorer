import { useEffect, useState } from 'react';
import { compareRatings } from '../api/cityExplorer';
import type { CityRating, CitySnapshot } from '../types';

function formatNumber(value: number | null, digits = 0): string {
  return value === null ? 'Unavailable' : value.toLocaleString(undefined, {
    maximumFractionDigits: digits,
  });
}

export default function CityRatings({ snapshots }: { snapshots: CitySnapshot[] }) {
  const [ratings, setRatings] = useState<CityRating[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let active = true;
    compareRatings(snapshots.map((snapshot) => snapshot.snapshot_id)).then(
      (data) => { if (active) setRatings(data); },
      (reason: unknown) => {
        if (active) setError(reason instanceof Error ? reason.message : 'Could not calculate ratings.');
      },
    );
    return () => { active = false; };
  }, [snapshots, attempt]);

  return (
    <section className="rounded-2xl border border-slate-200 bg-white p-5 shadow-sm">
      <h3 className="font-semibold text-slate-800">Places &amp; POIs rating</h3>
      <p className="mt-2 text-sm text-slate-500">
        Each place inside the city polygon counts equally. The score averages places per
        10,000 residents and places per km², each scaled against the highest eligible
        city in this comparison. Scores depend on the cities selected, not an absolute standard.
        At least two cities need population and area data.
      </p>
      {error && (
        <p role="alert" className="mt-4 text-sm text-red-700">
          {error}{' '}
          <button type="button" className="underline" onClick={() => {
            setError(null);
            setAttempt((value) => value + 1);
          }}>Try again</button>
        </p>
      )}
      {!ratings && !error && (
        <p role="status" className="mt-4 text-sm text-slate-500">
          Calculating historical polygon and places data; the first calculation may take several minutes.
        </p>
      )}
      {ratings && (
        <div className="mt-4 overflow-x-auto">
          <table className="w-full min-w-max text-left text-sm">
            <thead className="bg-slate-50 text-slate-500">
              <tr>
                <th className="px-3 py-2">City</th>
                <th className="px-3 py-2">POIs inside polygon</th>
                <th className="px-3 py-2">Population</th>
                <th className="px-3 py-2">Area (km²)</th>
                <th className="px-3 py-2">POIs / 10,000 people</th>
                <th className="px-3 py-2">POIs / km²</th>
                <th className="px-3 py-2">Relative score / 100</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {snapshots.map((snapshot) => {
                const rating = ratings.find((item) => item.division_id === snapshot.city.division_id);
                if (!rating) return null;
                return (
                  <tr key={snapshot.snapshot_id}>
                    <th className="px-3 py-3">{snapshot.city.city_name} · {snapshot.city.country ?? 'Unknown'}</th>
                    <td className="px-3 py-3">{formatNumber(rating.poi_count)}</td>
                    <td className="px-3 py-3">{formatNumber(rating.population)}</td>
                    <td className="px-3 py-3">{formatNumber(rating.area_sq_km, 2)}</td>
                    <td className="px-3 py-3">{formatNumber(rating.per_10000_people, 2)}</td>
                    <td className="px-3 py-3">{formatNumber(rating.per_sq_km, 2)}</td>
                    <td className="px-3 py-3">{formatNumber(rating.score, 1)}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          <p className="mt-3 text-xs text-slate-500">
            Unavailable population or polygon data prevents scoring. Population and geometry
            come from each snapshot&apos;s Overture release; Overture does not necessarily provide
            a population reference year. POI counts here are polygon-based and may differ from
            the bounding-box category counts below.
          </p>
        </div>
      )}
    </section>
  );
}
