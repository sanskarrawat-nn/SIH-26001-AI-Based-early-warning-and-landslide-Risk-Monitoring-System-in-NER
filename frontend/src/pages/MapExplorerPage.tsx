import React, { useState } from 'react';
import { GISMap } from '../components/map/GISMap';
import { LocationDrawer } from '../components/map/LocationDrawer';
import { LocationItem, HistoricalLandslide } from '../types';
import { RiskBadge } from '../components/common/RiskBadge';
import { Search, Filter, Mountain } from 'lucide-react';

interface MapExplorerPageProps {
  locations: LocationItem[];
  historicalEvents: HistoricalLandslide[];
  selectedLocation: LocationItem | null;
  onSelectLocation: (loc: LocationItem) => void;
  onOpenSimulator: (loc: LocationItem) => void;
  onSyncTelemetry: (locId: string) => Promise<void>;
}

export const MapExplorerPage: React.FC<MapExplorerPageProps> = ({
  locations,
  historicalEvents,
  selectedLocation,
  onSelectLocation,
  onOpenSimulator,
  onSyncTelemetry,
}) => {
  const [search, setSearch] = useState('');
  const [stateFilter, setStateFilter] = useState('ALL');
  const [riskFilter, setRiskFilter] = useState('ALL');

  const states = ['ALL', ...Array.from(new Set(locations.map(l => l.state)))];

  const filteredLocations = locations.filter(loc => {
    const matchesSearch = loc.name.toLowerCase().includes(search.toLowerCase()) ||
                          loc.district.toLowerCase().includes(search.toLowerCase());
    const matchesState = stateFilter === 'ALL' || loc.state === stateFilter;
    const matchesRisk = riskFilter === 'ALL' || loc.risk_level === riskFilter;
    return matchesSearch && matchesState && matchesRisk;
  });

  return (
    <div className="space-y-4">
      {/* Top Search & Filter Toolbar */}
      <div className="p-4 rounded-xl bg-[#0c1527] border border-slate-800 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2 flex-1 max-w-md">
          <div className="relative w-full">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-2.5" />
            <input
              type="text"
              placeholder="Search vulnerable site or district..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              className="w-full pl-9 pr-3 py-2 rounded-lg bg-slate-900 border border-slate-700 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-blue-500 font-sans"
            />
          </div>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 text-xs text-slate-400 font-mono">
            <Filter className="w-3.5 h-3.5" />
            <span>STATE:</span>
            <select
              value={stateFilter}
              onChange={(e) => setStateFilter(e.target.value)}
              className="px-2.5 py-1.5 rounded-lg bg-slate-900 border border-slate-700 text-slate-200 text-xs font-semibold focus:outline-none"
            >
              {states.map(s => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>

          <div className="flex items-center gap-1.5 text-xs text-slate-400 font-mono">
            <span>RISK:</span>
            <select
              value={riskFilter}
              onChange={(e) => setRiskFilter(e.target.value)}
              className="px-2.5 py-1.5 rounded-lg bg-slate-900 border border-slate-700 text-slate-200 text-xs font-semibold focus:outline-none"
            >
              <option value="ALL">All Levels</option>
              <option value="SEVERE">Severe (&gt;75)</option>
              <option value="HIGH">High (50-75)</option>
              <option value="MODERATE">Moderate (25-50)</option>
              <option value="LOW">Low (&lt;25)</option>
            </select>
          </div>
        </div>
      </div>

      {/* Map & Sidebar Grid */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Sites Sidebar (4 cols) */}
        <div className="lg:col-span-4 rounded-xl bg-[#0c1527] border border-slate-800 p-4 flex flex-col h-[620px]">
          <div className="flex items-center justify-between pb-3 border-b border-slate-800 mb-2">
            <span className="text-xs font-bold uppercase tracking-wider text-slate-300 font-mono">
              Monitored Locations ({filteredLocations.length})
            </span>
            <span className="text-[10px] text-slate-500 font-mono">Click to Inspect</span>
          </div>

          <div className="flex-1 overflow-y-auto space-y-2 pr-1">
            {filteredLocations.map(loc => {
              const isSelected = selectedLocation?.location_id === loc.location_id;
              return (
                <div
                  key={loc.location_id}
                  onClick={() => onSelectLocation(loc)}
                  className={`p-3 rounded-lg border transition-all cursor-pointer ${
                    isSelected
                      ? 'bg-blue-950/40 border-blue-500/60 shadow-md shadow-blue-950/50'
                      : 'bg-slate-900/40 border-slate-800/80 hover:border-slate-700'
                  }`}
                >
                  <div className="flex items-start justify-between">
                    <div>
                      <h4 className="text-xs font-bold text-white tracking-tight">{loc.name}</h4>
                      <p className="text-[11px] text-slate-400 mt-0.5">{loc.district}, {loc.state}</p>
                    </div>
                    <RiskBadge level={loc.risk_level} size="sm" showPulse={loc.risk_level === 'SEVERE'} />
                  </div>

                  <div className="mt-2 flex items-center justify-between text-[11px] font-mono text-slate-400">
                    <span className="flex items-center gap-1">
                      <Mountain className="w-3 h-3 text-amber-400" />
                      <span>{loc.slope}° slope</span>
                    </span>
                    <span>Score: <strong className="text-slate-200">{loc.current_risk_score.toFixed(1)}</strong></span>
                    <span>Rain: <strong className="text-cyan-400">{loc.latest_measurements?.rainfall_24h || 0}mm</strong></span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* GIS Map (8 cols) */}
        <div className="lg:col-span-8">
          <GISMap
            locations={filteredLocations}
            historicalEvents={historicalEvents}
            selectedLocation={selectedLocation}
            onSelectLocation={onSelectLocation}
          />
        </div>
      </div>

      {/* Location Drawer */}
      <LocationDrawer
        location={selectedLocation}
        onClose={() => onSelectLocation(null as any)}
        onOpenSimulator={onOpenSimulator}
        onSyncTelemetry={onSyncTelemetry}
      />
    </div>
  );
};
