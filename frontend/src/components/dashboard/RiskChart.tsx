import React from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Cell,
  PieChart,
  Pie,
  Legend
} from 'recharts';
import { LocationItem } from '../../types';

interface RiskChartProps {
  locations: LocationItem[];
}

export const RiskChart: React.FC<RiskChartProps> = ({ locations }) => {
  // 1. Risk Level Counts
  const counts = { LOW: 0, MODERATE: 0, HIGH: 0, SEVERE: 0 };
  locations.forEach(l => {
    if (counts[l.risk_level] !== undefined) {
      counts[l.risk_level]++;
    }
  });

  const pieData = [
    { name: 'Low Risk', value: counts.LOW, color: '#10b981' },
    { name: 'Moderate Risk', value: counts.MODERATE, color: '#f59e0b' },
    { name: 'High Risk', value: counts.HIGH, color: '#f97316' },
    { name: 'Severe Risk', value: counts.SEVERE, color: '#ef4444' },
  ];

  // 2. Top High-Risk Sites Bar Data
  const sortedSites = [...locations]
    .sort((a, b) => (b.current_risk_score || 0) - (a.current_risk_score || 0))
    .slice(0, 8)
    .map(l => ({
      name: l.name.length > 18 ? l.name.substring(0, 16) + '...' : l.name,
      score: l.current_risk_score,
      rainfall: l.latest_measurements?.rainfall_24h || 0,
      moisture: l.latest_measurements?.soil_moisture || 0,
      level: l.risk_level
    }));

  const getBarColor = (level: string) => {
    switch (level) {
      case 'SEVERE': return '#ef4444';
      case 'HIGH': return '#f97316';
      case 'MODERATE': return '#f59e0b';
      default: return '#10b981';
    }
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
      {/* Top 8 Vulnerable Sites Bar Chart */}
      <div className="lg:col-span-2 p-5 rounded-xl bg-[#0c1527] border border-slate-800">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-sm font-semibold text-white uppercase tracking-wider">Top Vulnerable Locations</h3>
            <p className="text-xs text-slate-400">Current landslide susceptibility score (0–100) and 24h rainfall</p>
          </div>
          <span className="text-xs font-mono text-slate-400">N={locations.length} Sites</span>
        </div>

        <div className="h-64 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={sortedSites} margin={{ top: 10, right: 10, left: -20, bottom: 20 }}>
              <XAxis
                dataKey="name"
                stroke="#64748b"
                tick={{ fill: '#94a3b8', fontSize: 10 }}
                angle={-20}
                textAnchor="end"
              />
              <YAxis
                stroke="#64748b"
                domain={[0, 100]}
                tick={{ fill: '#94a3b8', fontSize: 10 }}
              />
              <Tooltip
                contentStyle={{ backgroundColor: '#070d19', borderColor: '#334155', borderRadius: '8px' }}
                itemStyle={{ color: '#e2e8f0', fontSize: '12px' }}
                labelStyle={{ color: '#38bdf8', fontWeight: 'bold' }}
              />
              <Bar dataKey="score" name="Risk Score (0-100)" radius={[4, 4, 0, 0]}>
                {sortedSites.map((entry, index) => (
                  <Cell key={`cell-${index}`} fill={getBarColor(entry.level)} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* Regional Risk Category Breakdown */}
      <div className="p-5 rounded-xl bg-[#0c1527] border border-slate-800 flex flex-col justify-between">
        <div>
          <h3 className="text-sm font-semibold text-white uppercase tracking-wider">Hazard Distribution</h3>
          <p className="text-xs text-slate-400">Categorical share across North Eastern hill sectors</p>
        </div>

        <div className="h-52 w-full my-auto">
          <ResponsiveContainer width="100%" height="100%">
            <PieChart>
              <Pie
                data={pieData}
                innerRadius={50}
                outerRadius={75}
                paddingAngle={4}
                dataKey="value"
              >
                {pieData.map((entry, index) => (
                  <Cell key={`pie-${index}`} fill={entry.color} />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{ backgroundColor: '#070d19', borderColor: '#334155', borderRadius: '8px' }}
                itemStyle={{ color: '#e2e8f0', fontSize: '12px' }}
              />
              <Legend
                verticalAlign="bottom"
                wrapperStyle={{ fontSize: '11px', color: '#94a3b8', paddingTop: '8px' }}
              />
            </PieChart>
          </ResponsiveContainer>
        </div>

        <div className="grid grid-cols-2 gap-2 pt-2 border-t border-slate-800 text-xs font-mono">
          <div className="flex items-center justify-between text-rose-400">
            <span>Severe:</span>
            <span className="font-bold">{counts.SEVERE}</span>
          </div>
          <div className="flex items-center justify-between text-orange-400">
            <span>High:</span>
            <span className="font-bold">{counts.HIGH}</span>
          </div>
          <div className="flex items-center justify-between text-amber-400">
            <span>Moderate:</span>
            <span className="font-bold">{counts.MODERATE}</span>
          </div>
          <div className="flex items-center justify-between text-emerald-400">
            <span>Low:</span>
            <span className="font-bold">{counts.LOW}</span>
          </div>
        </div>
      </div>
    </div>
  );
};
