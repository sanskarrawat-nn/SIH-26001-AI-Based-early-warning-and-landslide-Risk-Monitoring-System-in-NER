import React from 'react';
import { AlertTriangle, CheckCircle, Clock } from 'lucide-react';
import { AlertItem } from '../../types';
import { RiskBadge } from '../common/RiskBadge';

interface RecentAlertsTableProps {
  alerts: AlertItem[];
  onAcknowledge: (alertId: string) => void;
  onSelectAlert: (alert: AlertItem) => void;
}

export const RecentAlertsTable: React.FC<RecentAlertsTableProps> = ({
  alerts,
  onAcknowledge,
  onSelectAlert
}) => {
  return (
    <div className="rounded-xl bg-[#0c1527] border border-slate-800 overflow-hidden">
      <div className="p-5 border-b border-slate-800 flex items-center justify-between">
        <div>
          <h3 className="text-sm font-semibold text-white uppercase tracking-wider flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-rose-500" />
            <span>Autonomous Early Warnings & Crisis Dispatch</span>
          </h3>
          <p className="text-xs text-slate-400">Triggered dynamically when risk score breaches configurable thresholds</p>
        </div>
        <span className="text-xs px-2.5 py-1 rounded bg-slate-800 text-slate-300 font-mono">
          {alerts.length} Warnings Logged
        </span>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left text-xs">
          <thead className="bg-slate-900/60 text-slate-400 uppercase font-mono tracking-wider text-[11px] border-b border-slate-800">
            <tr>
              <th className="px-5 py-3">Alert ID / Timestamp</th>
              <th className="px-4 py-3">Location</th>
              <th className="px-4 py-3">Severity</th>
              <th className="px-4 py-3">Score</th>
              <th className="px-4 py-3">Primary Trigger</th>
              <th className="px-4 py-3">Status</th>
              <th className="px-5 py-3 text-right">Action</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60 font-sans">
            {alerts.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-5 py-8 text-center text-slate-500">
                  No active warnings detected. All monitored sites are within safe thresholds.
                </td>
              </tr>
            ) : (
              alerts.slice(0, 6).map((alert) => {
                const triggerText = alert.triggering_factors?.[0]?.factor || 'Cumulative precipitation surge';
                const timeAgo = new Date(alert.created_at).toLocaleTimeString('en-IN', {
                  hour: '2-digit',
                  minute: '2-digit',
                  hour12: false
                });

                return (
                  <tr
                    key={alert.id}
                    className="hover:bg-slate-800/40 transition-colors cursor-pointer"
                    onClick={() => onSelectAlert(alert)}
                  >
                    <td className="px-5 py-3.5 font-mono text-slate-300">
                      <div className="font-semibold text-blue-400">{alert.alert_id}</div>
                      <div className="text-[10px] text-slate-500 flex items-center gap-1 mt-0.5">
                        <Clock className="w-3 h-3" />
                        <span>{timeAgo} IST</span>
                      </div>
                    </td>
                    <td className="px-4 py-3.5">
                      <div className="font-semibold text-white">{alert.location_name}</div>
                      <div className="text-[11px] text-slate-400">{alert.district}, {alert.state}</div>
                    </td>
                    <td className="px-4 py-3.5">
                      <RiskBadge level={alert.severity} size="sm" showPulse />
                    </td>
                    <td className="px-4 py-3.5 font-mono font-bold text-slate-200">
                      {alert.risk_score.toFixed(1)}
                    </td>
                    <td className="px-4 py-3.5 text-slate-300 max-w-xs truncate">
                      {triggerText}
                    </td>
                    <td className="px-4 py-3.5">
                      <span className={`px-2 py-0.5 rounded text-[10px] font-mono uppercase font-bold tracking-wider ${
                        alert.status === 'ACTIVE'
                          ? 'bg-rose-950/70 text-rose-400 border border-rose-800/50'
                          : alert.status === 'ACKNOWLEDGED'
                          ? 'bg-amber-950/70 text-amber-400 border border-amber-800/50'
                          : 'bg-emerald-950/70 text-emerald-400 border border-emerald-800/50'
                      }`}>
                        {alert.status}
                      </span>
                    </td>
                    <td className="px-5 py-3.5 text-right" onClick={(e) => e.stopPropagation()}>
                      {alert.status === 'ACTIVE' ? (
                        <button
                          onClick={() => onAcknowledge(alert.alert_id)}
                          className="px-2.5 py-1 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 border border-slate-700 font-semibold text-[11px] transition-colors"
                        >
                          Acknowledge
                        </button>
                      ) : (
                        <span className="text-[11px] text-emerald-400 flex items-center justify-end gap-1">
                          <CheckCircle className="w-3.5 h-3.5" />
                          <span>Logged</span>
                        </span>
                      )}
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
