import React from 'react';
import { RiskFactor } from '../../types';
import { Layers } from 'lucide-react';

interface FactorBreakdownProps {
  factors: RiskFactor[];
}

export const FactorBreakdown: React.FC<FactorBreakdownProps> = ({ factors }) => {
  const getImpactBadge = (impact: string) => {
    switch (impact) {
      case 'CRITICAL':
        return 'bg-rose-950/70 text-rose-300 border-rose-800/60';
      case 'HIGH':
        return 'bg-orange-950/70 text-orange-300 border-orange-800/60';
      case 'MODERATE':
        return 'bg-amber-950/70 text-amber-300 border-amber-800/60';
      default:
        return 'bg-slate-800 text-slate-300 border-slate-700';
    }
  };

  const getBarColor = (impact: string) => {
    switch (impact) {
      case 'CRITICAL': return 'bg-rose-500';
      case 'HIGH': return 'bg-orange-500';
      case 'MODERATE': return 'bg-amber-500';
      default: return 'bg-emerald-500';
    }
  };

  return (
    <div className="p-5 rounded-xl bg-[#0c1527] border border-slate-800">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-sm font-semibold text-white uppercase tracking-wider flex items-center gap-2">
            <Layers className="w-4 h-4 text-blue-400" />
            <span>AI Factor Attribution & Explainability</span>
          </h3>
          <p className="text-xs text-slate-400">Relative weight and impact of environmental triggers on current prediction</p>
        </div>
        <span className="text-xs font-mono text-slate-400">SHAP-based Attribution</span>
      </div>

      <div className="space-y-3.5">
        {factors.length === 0 ? (
          <div className="text-xs text-slate-500 py-4 text-center">
            Run a prediction to compute factor attributions.
          </div>
        ) : (
          factors.map((f, idx) => {
            const barWidth = Math.min(100, Math.max(15, f.weight * 300));
            return (
              <div key={idx} className="p-3 rounded-lg bg-slate-900/40 border border-slate-800/70">
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-xs font-bold text-slate-200">{f.factor}</span>
                  <span className={`px-2 py-0.5 rounded text-[10px] font-mono font-bold uppercase border ${getImpactBadge(f.impact)}`}>
                    {f.impact}
                  </span>
                </div>

                <div className="w-full bg-slate-800 rounded-full h-1.5 mb-2 overflow-hidden">
                  <div
                    className={`h-full rounded-full ${getBarColor(f.impact)}`}
                    style={{ width: `${barWidth}%` }}
                  />
                </div>

                <p className="text-[11px] text-slate-400 font-sans">{f.description}</p>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
