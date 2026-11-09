import { useEffect, useState } from 'react';
import { Loader2, Search } from 'lucide-react';
import { listSavedCities } from '../api/cityExplorer';
import type { SavedCity } from '../types';

interface Props {
  onSelect: (city: SavedCity) => void;
  selectedIds: string[];
  disabled?: boolean;
}

export default function SavedCitySearch({ onSelect, selectedIds, disabled }: Props) {
  const [cities, setCities] = useState<SavedCity[]>([]);
  const [query, setQuery] = useState('');
  const [status, setStatus] = useState<'loading' | 'ready' | 'error'>('loading');
  const [attempt, setAttempt] = useState(0);

  useEffect(() => {
    let active = true;
    listSavedCities().then(
      (savedCities) => {
        if (active) {
          setCities(savedCities);
          setStatus('ready');
        }
      },
      () => {
        if (active) setStatus('error');
      },
    );
    return () => { active = false; };
  }, [attempt]);

  const term = query.trim().toLocaleLowerCase();
  const matches = cities.filter((city) =>
    !selectedIds.includes(city.division_id) &&
    [city.city_name, city.country ?? '', city.subtype].some((value) =>
      value.toLocaleLowerCase().includes(term),
    ),
  );

  return (
    <div className="w-full">
      <label className="flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-4 py-3">
        {status === 'loading'
          ? <Loader2 className="shrink-0 animate-spin text-slate-400" size={20} />
          : <Search className="shrink-0 text-slate-400" size={20} />}
        <span className="sr-only">Search saved cities</span>
        <input
          type="search"
          placeholder="Search saved cities"
          className="min-w-0 flex-1 outline-none text-slate-800"
          value={query}
          onChange={(event) => setQuery(event.target.value)}
          disabled={disabled || status !== 'ready'}
        />
      </label>

      {status === 'error' && (
        <div role="alert" className="mt-3 text-sm text-red-700">
          Could not load saved cities.{' '}
          <button type="button" className="underline" onClick={() => {
            setStatus('loading');
            setAttempt((value) => value + 1);
          }}>Try again</button>
        </div>
      )}
      {status === 'ready' && cities.length === 0 && (
        <p className="mt-3 text-sm text-slate-500">
          No saved cities yet. Explore a city first to save its snapshot.
        </p>
      )}
      {status === 'ready' && cities.length > 0 && matches.length === 0 && !disabled && (
        <p className="mt-3 text-sm text-slate-500">
          {term ? 'No matching saved cities. Explore the city first to save a snapshot.' : 'All saved cities are selected.'}
        </p>
      )}
      {status === 'ready' && matches.length > 0 && !disabled && (
        <ul aria-label="Saved cities" className="mt-3 max-h-64 overflow-y-auto rounded-xl border border-slate-200">
          {matches.map((city) => (
            <li key={city.division_id}>
              <button
                type="button"
                onClick={() => { onSelect(city); setQuery(''); }}
                className="w-full border-b border-slate-100 px-4 py-3 text-left hover:bg-indigo-50 focus-visible:bg-indigo-50 last:border-b-0"
              >
                <span className="font-medium text-slate-800">{city.city_name}</span>
                <span className="ml-2 text-sm text-slate-500">
                  {city.country ?? 'Country unknown'} · {city.subtype}
                </span>
                <span className="block text-xs text-slate-500">
                  Latest snapshot: {new Date(city.captured_at).toLocaleString()}
                </span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
