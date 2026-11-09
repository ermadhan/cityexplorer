import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell,
} from 'recharts';
import type { CategoryCount } from '../types';

// Colour palette — one per bar, cycles if more entries than colours
const COLORS = [
  '#6366f1', '#8b5cf6', '#06b6d4', '#10b981', '#f59e0b',
  '#ef4444', '#ec4899', '#14b8a6', '#f97316', '#84cc16',
];

interface Props {
  title: string;
  emoji: string;
  data: CategoryCount[];
  colorOffset?: number;
}

function formatLabel(raw: string) {
  return raw.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

function formatCount(n: number) {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  return n.toString();
}

export default function CategoryCard({ title, emoji, data, colorOffset = 0 }: Props) {
  const top = data.slice(0, 12); // show top 12 categories
  const chartData = top.map((d) => ({ name: formatLabel(d.label), count: d.count }));

  return (
    <div className="bg-white rounded-2xl shadow-md border border-slate-100 p-5 flex flex-col gap-4">
      <h2 className="text-lg font-semibold text-slate-700 flex items-center gap-2">
        <span className="text-2xl">{emoji}</span> {title}
        <span className="ml-auto text-sm font-normal text-slate-400">
          {data.length} categories · {formatCount(data.reduce((s, d) => s + d.count, 0))} total
        </span>
      </h2>

      <ResponsiveContainer width="100%" height={Math.max(180, top.length * 30)}>
        <BarChart
          data={chartData}
          layout="vertical"
          margin={{ top: 0, right: 60, bottom: 0, left: 10 }}
        >
          <XAxis type="number" hide />
          <YAxis
            type="category"
            dataKey="name"
            width={160}
            tick={{ fontSize: 12, fill: '#64748b' }}
          />
          <Tooltip
            formatter={(value: number) => [value.toLocaleString(), 'Count']}
            contentStyle={{ borderRadius: '0.75rem', border: '1px solid #e2e8f0' }}
          />
          <Bar dataKey="count" radius={[0, 4, 4, 0]}>
            {chartData.map((_, i) => (
              <Cell
                key={i}
                fill={COLORS[(i + colorOffset) % COLORS.length]}
                fillOpacity={0.85}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
