import { useEffect, useState } from 'react';
import { getLeaderboard } from '../api/cityExplorer';
import type { LeaderboardEntry } from '../types';

type ScoreKey = 'score' | 'population_score' | 'area_score';
type RateKey = 'per_10000_people' | 'per_sq_km';

function Leaderboard({
  title,
  description,
  entries,
  scoreKey,
  rateKey,
  rateLabel,
}: {
  title: string;
  description: string;
  entries: LeaderboardEntry[];
  scoreKey: ScoreKey;
  rateKey?: RateKey;
  rateLabel?: string;
}) {
  const ranked = entries
    .filter((entry) => entry[scoreKey] !== null)
    .sort((a, b) => (b[scoreKey] ?? 0) - (a[scoreKey] ?? 0) || a.city_name.localeCompare(b.city_name));
  const unranked = entries.filter((entry) => entry[scoreKey] === null);
  let rank = 0;
  let previous: number | null = null;

  return (
    <section className="overflow-hidden rounded-2xl border border-slate-200 bg-white shadow-sm">
      <div className="border-b border-slate-100 px-5 py-4">
        <h3 className="text-lg font-semibold text-slate-800">{title}</h3>
        <p className="mt-1 text-sm text-slate-500">{description}</p>
      </div>
      {ranked.length === 0 && (
        <p className="px-5 py-3 text-sm text-slate-500">
          At least two cities with the required data are needed for a relative ranking.
        </p>
      )}
      <div className="overflow-x-auto">
        <table className="w-full min-w-max text-left text-sm">
          <thead className="bg-slate-50 text-slate-500">
            <tr>
              <th className="px-5 py-3">Rank</th>
              <th className="px-5 py-3">City</th>
              <th className="px-5 py-3">Score / 100</th>
              {rateKey && <th className="px-5 py-3">{rateLabel}</th>}
              <th className="px-5 py-3">Snapshot</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {[...ranked, ...unranked].map((entry, index) => {
              const score = entry[scoreKey];
              if (score !== null && score !== previous) rank = index + 1;
              if (score !== null) previous = score;
              const rate = rateKey ? entry[rateKey] : null;
              return (
                <tr key={entry.division_id}>
                  <td className="px-5 py-3">{score === null ? '—' : rank}</td>
                  <th className="px-5 py-3 font-medium text-slate-800">
                    {entry.city_name} · {entry.country ?? 'Unknown'} · {entry.subtype}
                  </th>
                  <td className="px-5 py-3">{score === null ? 'Unavailable' : score.toLocaleString(undefined, { maximumFractionDigits: 2 })}</td>
                  {rateKey && <td className="px-5 py-3">{rate === null ? 'Unavailable' : rate.toLocaleString(undefined, { maximumFractionDigits: 2 })}</td>}
                  <td className="px-5 py-3 text-slate-500">
                    {new Date(entry.captured_at).toLocaleDateString()} · {entry.overture_release}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}

export default function LeaderboardPage() {
  const [entries, setEntries] = useState<LeaderboardEntry[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let active = true;
    getLeaderboard().then(
      (data) => { if (active) setEntries(data); },
      (reason: unknown) => {
        if (active) setError(reason instanceof Error ? reason.message : 'Could not load the leaderboard.');
      },
    );
    return () => { active = false; };
  }, [attempt]);

  return (
    <main className="mx-auto max-w-6xl px-6 py-12">
      <h2 className="text-center text-3xl font-extrabold text-slate-800">Places &amp; POIs leaderboard</h2>
      <p className="mx-auto mt-3 max-w-3xl text-center text-slate-500">
        Latest saved snapshot for every city. Each place inside the city polygon counts equally.
        Rankings are relative to the saved cities with the required data, not a quality-of-life score.
      </p>
      {error && (
        <p role="alert" className="mt-6 rounded-xl bg-red-50 p-4 text-red-700">
          {error}{' '}
          <button type="button" className="underline" onClick={() => {
            setError(null);
            setAttempt((value) => value + 1);
          }}>Try again</button>
        </p>
      )}
      {!entries && !error && (
        <p role="status" className="mt-6 text-center text-slate-500">
          Loading ratings. Calculating uncached historical data may take several minutes.
        </p>
      )}
      {entries && entries.length === 0 && (
        <p className="mt-6 text-center text-slate-500">No saved cities yet. Explore cities to add them to the leaderboard.</p>
      )}
      {entries && entries.length > 0 && (
        <div className="mt-8 flex flex-col gap-5">
          <Leaderboard
            title="Combined score"
            description="Equal average of the two rates scaled against the best cities with both population and area. At least two complete cities are required."
            entries={entries}
            scoreKey="score"
          />
          <Leaderboard
            title="Places per population"
            description="POIs per 10,000 residents, scaled against all cities with population data."
            entries={entries}
            scoreKey="population_score"
            rateKey="per_10000_people"
            rateLabel="POIs / 10,000 people"
          />
          <Leaderboard
            title="Places per area"
            description="POIs per km², scaled against all cities with polygon area data."
            entries={entries}
            scoreKey="area_score"
            rateKey="per_sq_km"
            rateLabel="POIs / km²"
          />
          <p className="text-sm text-slate-500">
            Missing or zero population or area is unavailable, not zero. Each leaderboard needs at least two eligible cities;
            the eligible cities used for combined and individual scores may differ. Ties share the same rank.
            Snapshot releases and population reference years can differ, and map coverage is incomplete.
          </p>
        </div>
      )}
    </main>
  );
}
