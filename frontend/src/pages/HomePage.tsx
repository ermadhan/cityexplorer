import { useState } from 'react';
import { Compass, Loader2, AlertCircle } from 'lucide-react';
import CitySearch from '../components/CitySearch';
import CategoryCard from '../components/CategoryCard';
import { exploreCity } from '../api/cityExplorer';
import CompareCitiesPage from './CompareCitiesPage';
import LeaderboardPage from './LeaderboardPage';
import type { CitySearchResult, CitySnapshot, ExploreStatus } from '../types';

export default function HomePage() {
  const [screen, setScreen] = useState<'explore' | 'compare' | 'leaderboard'>('explore');
  const [selected, setSelected] = useState<CitySearchResult | null>(null);
  const [result, setResult] = useState<CitySnapshot | null>(null);
  const [status, setStatus] = useState<ExploreStatus>('idle');
  const [error, setError] = useState<string | null>(null);

  async function handleExplore() {
    if (!selected) return;
    setStatus('loading');
    setResult(null);
    setError(null);
    try {
      const data = await exploreCity(
        selected.city_name,
        selected.country ?? undefined,
        selected.subtype,
      );
      setResult(data);
      setStatus('success');
    } catch (e: unknown) {
      setError(e instanceof Error ? e.message : 'Something went wrong.');
      setStatus('error');
    }
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-indigo-50 via-white to-cyan-50">
      {/* ── Header ── */}
      <header className="bg-white/70 backdrop-blur border-b border-slate-200 sticky top-0 z-10">
        <div className="max-w-5xl mx-auto px-6 py-4 flex items-center gap-3">
          <Compass className="text-indigo-500" size={28} />
          <h1 className="text-xl font-bold text-slate-800 tracking-tight">City Explorer</h1>
          <nav className="ml-auto flex items-center gap-2" aria-label="Main navigation">
            <button
              type="button"
              onClick={() => setScreen('explore')}
              aria-current={screen === 'explore' ? 'page' : undefined}
              className={`rounded-lg px-3 py-2 text-sm font-medium ${screen === 'explore' ? 'bg-indigo-50 text-indigo-700' : 'text-slate-500 hover:bg-slate-50'}`}
            >
              Explore
            </button>
            <button
              type="button"
              onClick={() => setScreen('compare')}
              aria-current={screen === 'compare' ? 'page' : undefined}
              className={`rounded-lg px-3 py-2 text-sm font-medium ${screen === 'compare' ? 'bg-indigo-50 text-indigo-700' : 'text-slate-500 hover:bg-slate-50'}`}
            >
              Compare cities
            </button>
            <button
              type="button"
              onClick={() => setScreen('leaderboard')}
              aria-current={screen === 'leaderboard' ? 'page' : undefined}
              className={`rounded-lg px-3 py-2 text-sm font-medium ${screen === 'leaderboard' ? 'bg-indigo-50 text-indigo-700' : 'text-slate-500 hover:bg-slate-50'}`}
            >
              Leaderboard
            </button>
          </nav>
        </div>
      </header>

      {screen === 'leaderboard' ? <LeaderboardPage /> : screen === 'compare' ? <CompareCitiesPage /> : (
      <>
      {/* ── Hero Search ── */}
      <section className="max-w-5xl mx-auto px-6 pt-16 pb-10 text-center flex flex-col items-center gap-6">
        <h2 className="text-4xl font-extrabold text-slate-800 leading-tight">
          Understand any city's<br />
          <span className="text-indigo-500">man-made structures</span>
        </h2>
        <p className="text-slate-500 max-w-lg">
          Pick a city and instantly see a breakdown of buildings, roads, water bodies,
          infrastructure and land use — all from public Overture Maps data.
        </p>

        <CitySearch onSelect={setSelected} disabled={status === 'loading'} />

        <button
          onClick={handleExplore}
          disabled={!selected || status === 'loading'}
          className="mt-2 px-8 py-3 bg-indigo-500 hover:bg-indigo-600 disabled:opacity-40
                     disabled:cursor-not-allowed text-white font-semibold rounded-2xl
                     shadow-md transition-all flex items-center gap-2"
        >
          {status === 'loading'
            ? <><Loader2 size={18} className="animate-spin" /> Querying Overture Maps…</>
            : <><Compass size={18} /> Explore City</>
          }
        </button>

        {status === 'loading' && (
          <p className="text-sm text-slate-400 animate-pulse">
            This may take 30–90 seconds for large cities. Hang tight! ☕
          </p>
        )}
      </section>

      {/* ── Error ── */}
      {status === 'error' && error && (
        <div className="max-w-5xl mx-auto px-6 pb-6">
          <div className="bg-red-50 border border-red-200 rounded-2xl p-4 flex items-start gap-3 text-red-700">
            <AlertCircle size={20} className="shrink-0 mt-0.5" />
            <p>{error}</p>
          </div>
        </div>
      )}

      {/* ── Results ── */}
      {result && (
        <section className="max-w-5xl mx-auto px-6 pb-16 flex flex-col gap-6">
          {/* City summary banner */}
          <div className="bg-indigo-500 text-white rounded-2xl px-6 py-4 flex flex-wrap gap-4 items-center shadow-lg">
            <div>
              <p className="text-indigo-200 text-sm uppercase tracking-widest font-medium">Greater Metro Area</p>
              <h3 className="text-2xl font-bold">{result.city.city_name}</h3>
              <p className="text-indigo-200 text-sm">
                {result.city.country} · {result.city.subtype} ·
                bbox {result.city.bbox.xmin.toFixed(3)}° → {result.city.bbox.xmax.toFixed(3)}°
              </p>
              <p className="mt-1 text-sm text-indigo-100">
                Snapshot #{result.snapshot_id} saved · Overture release {result.overture_release}
              </p>
            </div>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <CategoryCard emoji="🏗️" title="Buildings"       data={result.buildings}       colorOffset={0} />
            <CategoryCard emoji="🛣️" title="Roads & Transport" data={result.transportation} colorOffset={2} />
            <CategoryCard emoji="💧" title="Water Bodies"    data={result.water}            colorOffset={4} />
            <CategoryCard emoji="🏭" title="Infrastructure"  data={result.infrastructure}   colorOffset={6} />
            <CategoryCard emoji="🌳" title="Land Use Zones"  data={result.land_use}         colorOffset={8} />
            <CategoryCard emoji="📍" title="Places & POIs"   data={result.places}           colorOffset={1} />
          </div>
        </section>
      )}
      </>
      )}
    </div>
  );
}
