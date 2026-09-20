import React from 'react';
import { RiskLevel } from '../../types';
import { RiskBadge } from '../common/RiskBadge';

interface RiskGaugeProps {
  score: number;
  level: RiskLevel;
  confidence: number;
  probability: number;
}

export const RiskGauge: React.FC<RiskGaugeProps> = ({
  score,
  level,
  confidence,
  probability
}) => {
  const clampedScore = Math.min(100, Math.max(0, score));

  // Determine gauge color
  let color = '#10b981'; // green
  if (level === 'SEVERE') color = '#ef4444';
  else if (level === 'HIGH') color = '#f97316';
  else if (level === 'MODERATE') color = '#f59e0b';

  return (
    <div className="flex flex-col items-center justify-center p-6 rounded-xl bg-[#0c1527] border border-slate-800 text-center">
      <span className="text-xs font-mono uppercase tracking-wider text-slate-400 mb-2">
        Composite Landslide Hazard Index
      </span>

      {/* SVG Semi-Circle / Full Gauge */}
      <div className="relative w-48 h-48 flex items-center justify-center my-2">
        <svg className="w-full h-full transform -rotate-90" viewBox="0 0 36 36">
          <path
            className="text-slate-800"
            strokeWidth="3.2"
            stroke="currentColor"
            fill="none"
            d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
          />
          <path
            style={{ stroke: color }}
            strokeDasharray={`${clampedScore}, 100`}
            strokeWidth="3.4"
            strokeLinecap="round"
            fill="none"
            d="M18 2.0845 a 15.9155 15.9155 0 0 1 0 31.831 a 15.9155 15.9155 0 0 1 0 -31.831"
          />
        </svg>

        <div className="absolute flex flex-col items-center">
          <span className="text-4xl font-extrabold font-mono tracking-tighter text-white">
            {clampedScore.toFixed(1)}
          </span>
          <span className="text-[11px] font-mono text-slate-400">OUT OF 100</span>
        </div>
      </div>

      <div className="mt-1">
        <RiskBadge level={level} size="lg" showPulse={level === 'SEVERE'} />
      </div>

      {/* Probability & Tree Agreement */}
      <div className="w-full grid grid-cols-2 gap-2 mt-5 pt-4 border-t border-slate-800 text-xs font-mono">
        <div className="bg-slate-900/50 p-2 rounded">
          <span className="text-slate-400 block text-[10px]">FAILURE PROBABILITY</span>
          <strong className="text-white text-sm">{(probability * 100).toFixed(1)}%</strong>
        </div>
        <div className="bg-slate-900/50 p-2 rounded">
          <span className="text-slate-400 block text-[10px]">MODEL CONFIDENCE</span>
          <strong className="text-emerald-400 text-sm">{(confidence * 100).toFixed(1)}%</strong>
        </div>
      </div>
    </div>
  );
};
