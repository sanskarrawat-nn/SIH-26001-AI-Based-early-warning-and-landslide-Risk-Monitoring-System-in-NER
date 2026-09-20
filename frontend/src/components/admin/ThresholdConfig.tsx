import React, { useState, useEffect } from 'react';
import { Sliders, Save, CheckCircle2, AlertCircle } from 'lucide-react';
import { ThresholdSettings } from '../../types';
import { api } from '../../services/api';

interface ThresholdConfigProps {
  thresholds: ThresholdSettings | null;
  onUpdated: (newSettings: ThresholdSettings) => void;
}

export const ThresholdConfig: React.FC<ThresholdConfigProps> = ({ thresholds, onUpdated }) => {
  const [low, setLow] = useState<number>(thresholds?.threshold_low || 25.0);
  const [mod, setMod] = useState<number>(thresholds?.threshold_moderate || 50.0);
  const [high, setHigh] = useState<number>(thresholds?.threshold_high || 75.0);

  const [saving, setSaving] = useState(false);
  const [msg, setMsg] = useState<{ type: 'success' | 'error'; text: string } | null>(null);

  useEffect(() => {
    if (thresholds) {
      setLow(thresholds.threshold_low);
      setMod(thresholds.threshold_moderate);
      setHigh(thresholds.threshold_high);
    }
  }, [thresholds]);

  const handleSave = async () => {
    if (!(low < mod && mod < high)) {
      setMsg({ type: 'error', text: 'Thresholds must satisfy: Low < Moderate < High' });
      return;
    }

    setSaving(true);
    setMsg(null);
    try {
      const updated = await api.updateThresholds({
        threshold_low: low,
        threshold_moderate: mod,
        threshold_high: high,
        updated_by: 'COMMAND_CENTER_ADMIN',
      });
      onUpdated(updated);
      setMsg({ type: 'success', text: 'Dynamic hazard thresholds successfully reconfigured!' });
      setTimeout(() => setMsg(null), 4000);
    } catch (e: any) {
      setMsg({ type: 'error', text: e.message || 'Failed to update thresholds' });
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="p-6 rounded-xl bg-[#0c1527] border border-slate-800">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-sm font-semibold text-white uppercase tracking-wider flex items-center gap-2">
            <Sliders className="w-4 h-4 text-amber-400" />
            <span>Configurable Early Warning Hazard Thresholds</span>
          </h3>
          <p className="text-xs text-slate-400">
            Define boundaries for automated alert generation and emergency standard operating procedures (SOPs).
          </p>
        </div>
      </div>

      {msg && (
        <div className={`p-3 rounded-lg mb-4 text-xs flex items-center gap-2 ${
          msg.type === 'success' ? 'bg-emerald-950/60 border border-emerald-800 text-emerald-300' : 'bg-rose-950/60 border border-rose-800 text-rose-300'
        }`}>
          {msg.type === 'success' ? <CheckCircle2 className="w-4 h-4" /> : <AlertCircle className="w-4 h-4" />}
          <span>{msg.text}</span>
        </div>
      )}

      {/* Threshold Visualizer Bar */}
      <div className="mb-6 p-4 rounded-lg bg-slate-900/50 border border-slate-800">
        <div className="h-6 w-full rounded-md flex overflow-hidden text-[10px] font-mono font-bold">
          <div style={{ width: `${low}%` }} className="bg-emerald-600 flex items-center justify-center text-white">
            LOW (0–{low})
          </div>
          <div style={{ width: `${mod - low}%` }} className="bg-amber-500 flex items-center justify-center text-slate-900">
            MODERATE ({low}–{mod})
          </div>
          <div style={{ width: `${high - mod}%` }} className="bg-orange-500 flex items-center justify-center text-white">
            HIGH ({mod}–{high})
          </div>
          <div style={{ width: `${100 - high}%` }} className="bg-rose-600 flex items-center justify-center text-white">
            SEVERE ({high}–100)
          </div>
        </div>
      </div>

      {/* Sliders */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
        <div className="p-4 rounded-lg bg-slate-900/40 border border-slate-800">
          <label className="text-xs font-mono font-semibold text-emerald-400 block mb-1">
            LOW BOUNDARY (Default 25)
          </label>
          <input
            type="number"
            min="10"
            max="35"
            step="1"
            value={low}
            onChange={(e) => setLow(parseFloat(e.target.value))}
            className="w-full px-3 py-2 rounded bg-slate-950 border border-slate-700 text-white font-mono font-bold text-sm"
          />
          <span className="text-[10px] text-slate-500 mt-1 block">Routine monitoring below this score</span>
        </div>

        <div className="p-4 rounded-lg bg-slate-900/40 border border-slate-800">
          <label className="text-xs font-mono font-semibold text-amber-400 block mb-1">
            MODERATE BOUNDARY (Default 50)
          </label>
          <input
            type="number"
            min="30"
            max="65"
            step="1"
            value={mod}
            onChange={(e) => setMod(parseFloat(e.target.value))}
            className="w-full px-3 py-2 rounded bg-slate-950 border border-slate-700 text-white font-mono font-bold text-sm"
          />
          <span className="text-[10px] text-slate-500 mt-1 block">Heightened monitoring & vigilance</span>
        </div>

        <div className="p-4 rounded-lg bg-slate-900/40 border border-slate-800">
          <label className="text-xs font-mono font-semibold text-rose-400 block mb-1">
            HIGH / SEVERE BOUNDARY (Default 75)
          </label>
          <input
            type="number"
            min="60"
            max="90"
            step="1"
            value={high}
            onChange={(e) => setHigh(parseFloat(e.target.value))}
            className="w-full px-3 py-2 rounded bg-slate-950 border border-slate-700 text-white font-mono font-bold text-sm"
          />
          <span className="text-[10px] text-slate-500 mt-1 block">Immediate evacuation & road closure trigger</span>
        </div>
      </div>

      <div className="mt-5 flex justify-end">
        <button
          onClick={handleSave}
          disabled={saving}
          className="flex items-center gap-2 px-5 py-2.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white font-semibold text-xs transition-colors shadow-md disabled:opacity-50"
        >
          <Save className="w-4 h-4" />
          <span>{saving ? 'Updating System...' : 'Apply Operational Thresholds'}</span>
        </button>
      </div>
    </div>
  );
};
