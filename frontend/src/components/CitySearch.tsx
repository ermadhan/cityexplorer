import { useState, useEffect, useRef } from 'react';
import { Search, MapPin, Loader2 } from 'lucide-react';
import { searchCities } from '../api/cityExplorer';
import type { CitySearchResult } from '../types';

interface Props {
  onSelect: (city: CitySearchResult) => void;
  disabled?: boolean;
}

export default function CitySearch({ onSelect, disabled }: Props) {
  const [query, setQuery] = useState('');
  const [results, setResults] = useState<CitySearchResult[]>([]);
  const [loading, setLoading] = useState(false);
  const [open, setOpen] = useState(false);
  const [searchError, setSearchError] = useState(false);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const skipSearchRef = useRef(false);

  useEffect(() => {
    const searchTerm = query.trim();
    if (searchTerm.length < 2 || skipSearchRef.current) {
      skipSearchRef.current = false;
      return;
    }

    let cancelled = false;
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(async () => {
      setLoading(true);
      setSearchError(false);
      try {
        const hits = await searchCities(searchTerm);
        if (!cancelled) {
          setResults(hits);
          setOpen(true);
        }
      } catch {
        if (!cancelled) {
          setResults([]);
          setSearchError(true);
          setOpen(true);
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    }, 400);
    return () => {
      cancelled = true;
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, [query]);

  function handleSelect(city: CitySearchResult) {
    if (debounceRef.current) clearTimeout(debounceRef.current);
    skipSearchRef.current = query !== city.city_name;
    setQuery(city.city_name);
    setResults([]);
    setOpen(false);
    setSearchError(false);
    setLoading(false);
    onSelect(city);
  }

  function handleChange(value: string) {
    setQuery(value);
    setResults([]);
    setOpen(false);
    setSearchError(false);
    if (value.trim().length < 2) {
      setLoading(false);
    }
  }

  return (
    <div className="relative w-full max-w-xl mx-auto">
      <div className="flex items-center gap-2 bg-white rounded-2xl shadow-lg px-4 py-3 border border-slate-200">
        {loading
          ? <Loader2 className="text-slate-400 animate-spin" size={20} />
          : <Search className="text-slate-400" size={20} />
        }
        <input
          type="text"
          placeholder="Search a city… e.g. Bengaluru, Tokyo, London"
          className="flex-1 outline-none text-slate-800 text-base placeholder:text-slate-400"
          value={query}
          onChange={(e) => handleChange(e.target.value)}
          disabled={disabled}
        />
      </div>

      {open && results.length > 0 && (
        <ul className="absolute z-20 w-full bg-white border border-slate-200 rounded-2xl shadow-xl mt-2 overflow-hidden">
          {results.map((city) => (
            <li
              key={city.division_id}
              className="flex items-center gap-3 px-4 py-3 hover:bg-indigo-50 cursor-pointer transition-colors"
              onClick={() => handleSelect(city)}
            >
              <MapPin size={16} className="text-indigo-400 shrink-0" />
              <div>
                <span className="font-medium text-slate-800">{city.city_name}</span>
                <span className="ml-2 text-sm text-slate-400">
                  {city.country} · {city.subtype}
                </span>
              </div>
            </li>
          ))}
        </ul>
      )}
      {open && !loading && (searchError || results.length === 0) && (
        <div className="absolute z-20 w-full bg-white border border-slate-200 rounded-2xl shadow-xl mt-2 px-4 py-3 text-sm text-slate-500"
             role="status">
          {searchError ? 'City search is unavailable. Please try again.' : 'No matching cities found.'}
        </div>
      )}
    </div>
  );
}
