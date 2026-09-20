import React from 'react';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  Legend,
  CartesianGrid
} from 'recharts';

interface TimeSeriesTrendsProps {
  timeseries: any[];
  stateBreakdown: Array<{ state: string; monitored_sites: number; avg_risk: number; critical_sites: number }>;
}

export const TimeSeriesTrends: React.FC<TimeSeriesTrendsProps> = ({
  timeseries,
  stateBreakdown
}) => {
  return (
    <div className="space-y-6">
      {/* Time-Series Correlation */}
      <div className="p-5 rounded-xl bg-[#0c1527] border border-slate-800">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h3 className="text-sm font-semibold text-white uppercase tracking-wider">
              Rainfall vs. Hazard Score Progression
            </h3>
            <p className="text-xs text-slate-400">Dynamic tracking of pore saturation triggers and model risk output</p>
          </div>
          <span className="text-xs font-mono text-slate-400">Chronological Telemetry</span>
        </div>

        <div className="h-72 w-full">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={timeseries} margin={{ top: 10, right: 20, left: -15, bottom: 10 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#1e293b" />
              <XAxis dataKey="timestamp" stroke="#64748b" tick={{ fill: '#94a3b8', fontSize: 10 }} />
              <YAxis yAxisId="left" stroke="#38bdf8" domain={[0, 250]} tick={{ fill: '#38bdf8', fontSize: 10 }} />
              <YAxis yAxisId="right" orientation="right" stroke="#ef4444" domain={[0, 100]} tick={{ fill: '#ef4444', fontSize: 10 }} />
              <Tooltip
                contentStyle={{ backgroundColor: '#070d19', borderColor: '#334155', borderRadius: '8px' }}
                itemStyle={{ fontSize: '11px' }}
              />
              <Legend verticalAlign="top" wrapperStyle={{ fontSize: '11px', paddingBottom: '10px' }} />
              <Line
                yAxisId="left"
                type="monotone"
                dataKey="rainfall_24h"
                name="24h Rainfall (mm)"
                stroke="#38bdf8"
                strokeWidth={2}
                dot={{ r: 2 }}
              />
              <Line
                yAxisId="left"
                type="monotone"
                dataKey="soil_moisture"
                name="Soil Moisture (%)"
                stroke="#34d399"
                strokeWidth={1.5}
                strokeDasharray="4 4"
                dot={false}
              />
              <Line
                yAxisId="right"
                type="monotone"
                dataKey="risk_score"
                name="Predicted Risk Score (0-100)"
                stroke="#ef4444"
                strokeWidth={2.5}
                dot={{ r: 3, fill: '#ef4444' }}
              />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </div>

      {/* State-by-State Risk Summary */}
      <div className="p-5 rounded-xl bg-[#0c1527] border border-slate-800">
        <h3 className="text-sm font-semibold text-white uppercase tracking-wider mb-3">
          State-Wise Geological Vulnerability Breakdown
        </h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {stateBreakdown.map((sb, idx) => (
            <div key={idx} className="p-3.5 rounded-lg bg-slate-900/40 border border-slate-800">
              <span className="text-xs font-bold text-white block">{sb.state}</span>
              <div className="mt-2 flex items-baseline justify-between text-xs font-mono">
                <span className="text-slate-400">Avg Risk:</span>
                <span className={`font-bold ${sb.avg_risk >= 50 ? 'text-rose-400' : 'text-emerald-400'}`}>
                  {sb.avg_risk} / 100
                </span>
              </div>
              <div className="mt-1 flex items-baseline justify-between text-xs font-mono">
                <span className="text-slate-400">Critical Sites:</span>
                <span className="font-bold text-slate-200">{sb.critical_sites} of {sb.monitored_sites}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
