import React, { useState } from 'react';
import { X, RefreshCw, Sliders, CloudRain, Mountain, Droplets, Compass, ShieldAlert, CheckCircle2 } from 'lucide-react';
import { LocationItem } from '../../types';
import { RiskBadge } from '../common/RiskBadge';

interface LocationDrawerProps {
  location: LocationItem | null;
  onClose: () => void;
  onOpenSimulator: (loc: LocationItem) => void;
  onSyncTelemetry: (locId: string) => Promise<void>;
}

export const LocationDrawer: React.FC<LocationDrawerProps> = ({
  location,
  onClose,
  onOpenSimulator,
  onSyncTelemetry,
}) => {
  const [syncing, setSyncing] = useState(false);
  const [syncMessage, setSyncMessage] = useState<string | null>(null);

  if (!location) return null;

  const handleSync = async () => {
    setSyncing(true);
    setSyncMessage(null);
    try {
      await onSyncTelemetry(location.location_id);
      setSyncMessage('Live telemetry updated!');
      setTimeout(() => setSyncMessage(null), 3000);
    } catch (e: any) {
      setSyncMessage(e.message || 'Sync failed');
    } finally {
      setSyncing(false);
    }
  };

  const m = location.latest_measurements || {};
  const pred: any = location.latest_prediction || {};
  const score = location.current_risk_score || 0;

  return (
    <div className="fixed inset-y-0 right-0 z-50 w-full max-w-md bg-[#0c1527] border-l border-slate-800 shadow-2xl flex flex-col transform transition-transform duration-300">
      {/* Header */}
      <div className="p-5 border-b border-slate-800 flex items-start justify-between bg-slate-900/40">
        <div>
          <div className="flex items-center gap-2">
            <h2 className="text-lg font-bold text-white tracking-tight">{location.name}</h2>
            <RiskBadge level={location.risk_level} size="sm" showPulse />
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            {location.district}, {location.state} &bull; <span className="font-mono">{location.location_id}</span>
          </p>
        </div>
        <button
          onClick={onClose}
          className="p-1.5 rounded-lg bg-slate-800/80 text-slate-400 hover:text-white hover:bg-slate-700 transition-colors"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Body Content */}
      <div className="flex-1 overflow-y-auto p-5 space-y-5">
        {/* Risk Score Gauge Tile */}
        <div className="p-4 rounded-xl bg-slate-900/60 border border-slate-800 flex items-center justify-between">
          <div>
            <span className="text-xs font-mono uppercase tracking-wider text-slate-400">Current Hazard Index</span>
            <div className="text-3xl font-extrabold font-mono text-white mt-1">
              {score.toFixed(1)} <span className="text-sm font-normal text-slate-400">/ 100</span>
            </div>
            <span className="text-xs text-slate-400">Status: <strong className="text-slate-200">{location.alert_status}</strong></span>
          </div>

          <div className="w-24 h-24 relative flex items-center justify-center">
            {/* Simple Circular Visual */}
            <svg className="w-full h-full transform -rotate-90" viewBox="0 0 36 36">
              <path
                className="text-slate-800"
                strokeWidth="3.5"
                stroke="currentColor"
                fill="none"
                d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
              />
              <path
                className={
                  location.risk_level === 'SEVERE'
                    ? 'text-rose-500'
                    : location.risk_level === 'HIGH'
                    ? 'text-orange-500'
                    : location.risk_level === 'MODERATE'
                    ? 'text-amber-500'
                    : 'text-emerald-500'
                }
                strokeDasharray={`${score}, 100`}
                strokeWidth="3.5"
                strokeLinecap="round"
                stroke="currentColor"
                fill="none"
                d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
              />
            </svg>
            <span className="absolute font-mono font-bold text-xs text-white">
              {Math.round(score)}%
            </span>
          </div>
        </div>

        {/* Topographic & Geotechnical Attributes */}
        <div>
          <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2.5">
            Topographic & Geological Profile
          </h4>
          <div className="grid grid-cols-2 gap-2.5 text-xs font-mono">
            <div className="p-3 rounded-lg bg-slate-900/40 border border-slate-800 flex items-center gap-2">
              <Mountain className="w-4 h-4 text-amber-400" />
              <div>
                <span className="text-[10px] text-slate-500 block">SLOPE</span>
                <strong className="text-slate-200">{location.slope}° Grade</strong>
              </div>
            </div>
            <div className="p-3 rounded-lg bg-slate-900/40 border border-slate-800 flex items-center gap-2">
              <Compass className="w-4 h-4 text-blue-400" />
              <div>
                <span className="text-[10px] text-slate-500 block">ELEVATION</span>
                <strong className="text-slate-200">{location.elevation}m a.s.l.</strong>
              </div>
            </div>
          </div>
          <div className="mt-2 p-3 rounded-lg bg-slate-900/40 border border-slate-800 text-xs">
            <span className="text-[10px] text-slate-500 uppercase font-mono block">Lithology & Ground Cover</span>
            <p className="text-slate-300 mt-1 font-medium">{location.geology_type || 'Weathered flysch sediments'}</p>
          </div>
        </div>

        {/* Real-Time Environmental Telemetry */}
        <div>
          <div className="flex items-center justify-between mb-2.5">
            <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400">
              Active Sensor Telemetry
            </h4>
            <button
              onClick={handleSync}
              disabled={syncing}
              className="flex items-center gap-1 text-[11px] text-blue-400 hover:text-blue-300 font-semibold"
            >
              <RefreshCw className={`w-3 h-3 ${syncing ? 'animate-spin' : ''}`} />
              <span>{syncing ? 'Polling...' : 'Sync Sensor'}</span>
            </button>
          </div>

          {syncMessage && (
            <div className="mb-2 p-2 rounded bg-blue-950/60 border border-blue-800 text-[11px] text-blue-300 flex items-center gap-1.5">
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>{syncMessage}</span>
            </div>
          )}

          <div className="grid grid-cols-2 gap-2.5 text-xs font-mono">
            <div className="p-3 rounded-lg bg-slate-900/40 border border-slate-800">
              <div className="flex items-center gap-1.5 text-cyan-400 mb-1">
                <CloudRain className="w-4 h-4" />
                <span className="text-[10px] text-slate-400">24H RAINFALL</span>
              </div>
              <span className="text-lg font-bold text-white">{m.rainfall_24h || 0}</span>
              <span className="text-xs text-slate-400 ml-1">mm</span>
            </div>

            <div className="p-3 rounded-lg bg-slate-900/40 border border-slate-800">
              <div className="flex items-center gap-1.5 text-indigo-400 mb-1">
                <Droplets className="w-4 h-4" />
                <span className="text-[10px] text-slate-400">SOIL MOISTURE</span>
              </div>
              <span className="text-lg font-bold text-white">{m.soil_moisture || 0}</span>
              <span className="text-xs text-slate-400 ml-1">%</span>
            </div>

            <div className="p-3 rounded-lg bg-slate-900/40 border border-slate-800">
              <span className="text-[10px] text-slate-400 block mb-1">1H INTENSITY</span>
              <span className="text-base font-bold text-white">{m.rainfall_1h || 0}</span>
              <span className="text-xs text-slate-400 ml-1">mm/h</span>
            </div>

            <div className="p-3 rounded-lg bg-slate-900/40 border border-slate-800">
              <span className="text-[10px] text-slate-400 block mb-1">7D ANTECEDENT</span>
              <span className="text-base font-bold text-white">{m.rainfall_7d || 0}</span>
              <span className="text-xs text-slate-400 ml-1">mm</span>
            </div>
          </div>
        </div>

        {/* AI Geotechnical Explanation */}
        <div>
          <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
            AI Geotechnical Assessment
          </h4>
          <div className="p-3.5 rounded-lg bg-slate-900/60 border border-slate-800 text-xs text-slate-300 leading-relaxed">
            {pred.explanation || (
              <span>
                Environmental measurements are being processed through the calibrated ensemble classifier.
                Slope stability is governed by effective pore-water stress and antecedent saturation index.
              </span>
            )}
          </div>
        </div>

        {/* Recommended Action */}
        {pred.recommendation && (
          <div>
            <h4 className="text-xs font-semibold uppercase tracking-wider text-slate-400 mb-2">
              Actionable SOP Directive
            </h4>
            <div className="p-3.5 rounded-lg bg-rose-950/30 border border-rose-900/40 text-xs text-rose-200">
              {pred.recommendation}
            </div>
          </div>
        )}
      </div>

      {/* Footer Action */}
      <div className="p-4 border-t border-slate-800 bg-slate-900/50 flex gap-2">
        <button
          onClick={() => onOpenSimulator(location)}
          className="flex-1 py-2.5 px-4 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs flex items-center justify-center gap-2 shadow-lg shadow-blue-900/30 transition-colors"
        >
          <Sliders className="w-4 h-4" />
          <span>Launch Scenario Simulator</span>
        </button>
      </div>
    </div>
  );
};
