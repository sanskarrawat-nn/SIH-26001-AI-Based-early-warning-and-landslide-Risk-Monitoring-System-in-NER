import React, { useState } from 'react';
import { HistoricalLandslide } from '../../types';
import { Calendar, Users, AlertTriangle, FileSpreadsheet } from 'lucide-react';

interface HistoricalCatalogProps {
  events: HistoricalLandslide[];
}

export const HistoricalCatalog: React.FC<HistoricalCatalogProps> = ({ events }) => {
  const [selectedState, setSelectedState] = useState<string>('ALL');

  const states = ['ALL', ...Array.from(new Set(events.map(e => e.state)))];

  const filtered = selectedState === 'ALL'
    ? events
    : events.filter(e => e.state === selectedState);

  return (
    <div className="rounded-xl bg-[#0c1527] border border-slate-800 overflow-hidden">
      <div className="p-5 border-b border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h3 className="text-sm font-semibold text-white uppercase tracking-wider flex items-center gap-2">
            <FileSpreadsheet className="w-4 h-4 text-purple-400" />
            <span>North East India Historical Landslide Catalog</span>
          </h3>
          <p className="text-xs text-slate-400">Validated geological records from Geological Survey of India (GSI) & NDMA</p>
        </div>

        {/* State Filter */}
        <div className="flex items-center gap-2">
          <span className="text-xs text-slate-400 font-mono">STATE:</span>
          <select
            value={selectedState}
            onChange={(e) => setSelectedState(e.target.value)}
            className="px-3 py-1.5 rounded-lg bg-slate-900 border border-slate-700 text-slate-200 text-xs font-semibold focus:outline-none focus:border-purple-500"
          >
            {states.map(st => (
              <option key={st} value={st}>{st}</option>
            ))}
          </select>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead className="bg-slate-900/60 text-slate-400 uppercase font-mono tracking-wider text-[11px] border-b border-slate-800">
            <tr>
              <th className="px-5 py-3">Event ID & Date</th>
              <th className="px-4 py-3">Location & State</th>
              <th className="px-4 py-3">Severity</th>
              <th className="px-4 py-3">Trigger Rain (24h)</th>
              <th className="px-4 py-3">Casualties</th>
              <th className="px-4 py-3">Lithology / Terrain</th>
              <th className="px-5 py-3">Impact Summary</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60 font-sans">
            {filtered.map((item) => (
              <tr key={item.id} className="hover:bg-slate-800/30 transition-colors">
                <td className="px-5 py-3.5 font-mono text-slate-300">
                  <div className="font-semibold text-purple-400">{item.event_id}</div>
                  <div className="text-[10px] text-slate-500 flex items-center gap-1 mt-0.5">
                    <Calendar className="w-3 h-3" />
                    <span>{new Date(item.event_date).toLocaleDateString('en-IN', { year: 'numeric', month: 'short', day: 'numeric' })}</span>
                  </div>
                </td>
                <td className="px-4 py-3.5">
                  <div className="font-semibold text-white">{item.location_name}</div>
                  <div className="text-[11px] text-slate-400">{item.district}, {item.state}</div>
                </td>
                <td className="px-4 py-3.5">
                  <span className={`px-2 py-0.5 rounded text-[10px] font-mono uppercase font-bold tracking-wider ${
                    item.severity === 'CATASTROPHIC'
                      ? 'bg-rose-950/70 text-rose-300 border border-rose-800/50'
                      : 'bg-orange-950/70 text-orange-300 border border-orange-800/50'
                  }`}>
                    {item.severity}
                  </span>
                </td>
                <td className="px-4 py-3.5 font-mono font-bold text-cyan-400">
                  {item.triggering_rainfall_24h ? `${item.triggering_rainfall_24h} mm` : 'N/A'}
                </td>
                <td className="px-4 py-3.5">
                  <span className="flex items-center gap-1 font-mono font-bold text-rose-400">
                    <Users className="w-3 h-3" />
                    <span>{item.casualties}</span>
                  </span>
                </td>
                <td className="px-4 py-3.5 text-slate-400 max-w-xs truncate text-[11px]">
                  {item.geological_formation || 'Flysch sedimentary rocks'}
                </td>
                <td className="px-5 py-3.5 text-slate-300 max-w-sm text-[11px]">
                  {item.infrastructure_damage || item.notes}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
