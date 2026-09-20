import {openResponseDraft} from '../services/dispatch';
import React, { useState } from 'react';
import { AlertLanguageSelect, LocalizedAlert } from '../components/common/AlertLanguage';
import { AlertItem } from '../types';
import { RiskBadge } from '../components/common/RiskBadge';
import {
  Bell,
  ShieldAlert,
  AlertTriangle,
  CheckCircle,
  Clock,
  CheckCheck,
  ListChecks,
  ChevronDown,
  ChevronUp
} from 'lucide-react';

interface AlertsCenterPageProps {
  alerts: AlertItem[];
  onAcknowledge: (alertId: string) => void;
  onResolve: (alertId: string, notes: string) => void;
}

export const AlertsCenterPage: React.FC<AlertsCenterPageProps> = ({
  alerts,
  onAcknowledge,
  onResolve
}) => {
  const [severityFilter, setSeverityFilter] = useState<string>('ALL');
  const [statusFilter, setStatusFilter] = useState<string>('ALL');
  const [expandedAlertId, setExpandedAlertId] = useState<string | null>(null);

  React.useEffect(() => {
    try {
      const params = new URLSearchParams(window.location.search);
      if (params.get('expand') === 'true' && alerts.length > 0) {
        setExpandedAlertId(alerts[0].alert_id);
      }
    } catch {}
  }, [alerts]);

  const filtered = alerts.filter(a => {
    const matchSev = severityFilter === 'ALL' || a.severity === severityFilter;
    const matchStat = statusFilter === 'ALL' || a.status === statusFilter;
    return matchSev && matchStat;
  });

  const activeCount = alerts.filter(a => a.status === 'ACTIVE').length;
  const severeCount = alerts.filter(a => a.severity === 'SEVERE').length;
  const ackCount = alerts.filter(a => a.status === 'ACKNOWLEDGED').length;
  const resolvedCount = alerts.filter(a => a.status === 'RESOLVED').length;

  return (
    <div className="space-y-6">
      <AlertLanguageSelect />
      {/* Alert Header Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <div className="p-4 rounded-xl bg-rose-950/20 border border-rose-900/50">
          <div className="flex items-center justify-between text-xs text-rose-300 font-mono">
            <span>ACTIVE CRISIS ALERTS</span>
            <ShieldAlert className="w-4 h-4 text-rose-400" />
          </div>
          <div className="text-3xl font-extrabold font-mono text-rose-400 mt-1">{activeCount}</div>
          <span className="text-[10px] text-rose-400/80">Requires response or evacuation</span>
        </div>

        <div className="p-4 rounded-xl bg-orange-950/20 border border-orange-900/50">
          <div className="flex items-center justify-between text-xs text-orange-300 font-mono">
            <span>SEVERE HAZARDS</span>
            <AlertTriangle className="w-4 h-4 text-orange-400" />
          </div>
          <div className="text-3xl font-extrabold font-mono text-orange-400 mt-1">{severeCount}</div>
          <span className="text-[10px] text-orange-400/80">Risk Score &gt; 75/100</span>
        </div>

        <div className="p-4 rounded-xl bg-amber-950/20 border border-amber-900/50">
          <div className="flex items-center justify-between text-xs text-amber-300 font-mono">
            <span>ACKNOWLEDGED</span>
            <Clock className="w-4 h-4 text-amber-400" />
          </div>
          <div className="text-3xl font-extrabold font-mono text-amber-400 mt-1">{ackCount}</div>
          <span className="text-[10px] text-amber-400/80">Field teams notified</span>
        </div>

        <div className="p-4 rounded-xl bg-emerald-950/20 border border-emerald-900/50">
          <div className="flex items-center justify-between text-xs text-emerald-300 font-mono">
            <span>RESOLVED</span>
            <CheckCheck className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="text-3xl font-extrabold font-mono text-emerald-400 mt-1">{resolvedCount}</div>
          <span className="text-[10px] text-emerald-400/80">Hazard mitigated or passed</span>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="p-4 rounded-xl bg-[#0c1527] border border-slate-800 flex flex-wrap items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <Bell className="w-4 h-4 text-blue-400" />
          <h3 className="text-xs font-bold uppercase tracking-wider text-white font-mono">
            Emergency Alert & Early Warning Dispatch Log ({filtered.length})
          </h3>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 text-xs text-slate-400 font-mono">
            <span>SEVERITY:</span>
            <select
              value={severityFilter}
              onChange={(e) => setSeverityFilter(e.target.value)}
              className="px-2.5 py-1.5 rounded-lg bg-slate-900 border border-slate-700 text-slate-200 text-xs font-semibold focus:outline-none"
            >
              <option value="ALL">All Severities</option>
              <option value="SEVERE">Severe</option>
              <option value="HIGH">High</option>
              <option value="MODERATE">Moderate</option>
            </select>
          </div>

          <div className="flex items-center gap-1.5 text-xs text-slate-400 font-mono">
            <span>STATUS:</span>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              className="px-2.5 py-1.5 rounded-lg bg-slate-900 border border-slate-700 text-slate-200 text-xs font-semibold focus:outline-none"
            >
              <option value="ALL">All Statuses</option>
              <option value="ACTIVE">Active Only</option>
              <option value="ACKNOWLEDGED">Acknowledged</option>
              <option value="RESOLVED">Resolved</option>
            </select>
          </div>
        </div>
      </div>

      {/* Alerts Feed */}
      <div className="space-y-3.5">
        {filtered.length === 0 ? (
          <div className="p-12 text-center text-slate-500 rounded-xl bg-[#0c1527] border border-slate-800">
            No warnings matching selected filters.
          </div>
        ) : (
          filtered.map((alert) => {
            const isExpanded = expandedAlertId === alert.alert_id;
            return (
              <div
                key={alert.id}
                className={`p-5 rounded-xl border transition-all ${
                  alert.severity === 'SEVERE'
                    ? 'bg-[#0c1527] border-rose-900/60 shadow-lg shadow-rose-950/20'
                    : 'bg-[#0c1527] border-slate-800'
                }`}
              >
                <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
                  <div className="flex items-start gap-3">
                    <div className={`p-2 rounded-lg mt-0.5 ${
                      alert.severity === 'SEVERE' ? 'bg-rose-950 text-rose-400 border border-rose-800' : 'bg-orange-950 text-orange-400 border border-orange-800'
                    }`}>
                      {alert.severity === 'SEVERE' ? <ShieldAlert className="w-5 h-5" /> : <AlertTriangle className="w-5 h-5" />}
                    </div>

                    <div>
                      <div className="flex items-center gap-2">
                        <span className="font-mono font-bold text-xs text-blue-400">{alert.alert_id}</span>
                        <RiskBadge level={alert.severity} size="sm" showPulse={alert.severity === 'SEVERE'} />
                        <span className="text-xs font-mono font-bold text-slate-300">
                          Score: {alert.risk_score.toFixed(1)}/100
                        </span>
                      </div>
                      <LocalizedAlert alert={alert}/><button className="text-blue-300 underline text-xs py-2" onClick={()=>openResponseDraft({location_id:alert.location_id,alert_id:alert.alert_id,title:'Precautionary response: '+(alert.location_name||alert.location_id),description:alert.message,severity:alert.severity,kind:'PRECAUTIONARY_WARNING'})}>Request emergency response</button>
                      <h4 className="text-sm font-bold text-white mt-1">{alert.title}</h4>
                      <p className="text-xs text-slate-300 mt-0.5">{alert.message}</p>
                    </div>
                  </div>

                  {/* Actions & Status */}
                  <div className="flex items-center gap-2 self-end md:self-center">
                    {alert.status === 'ACTIVE' && (
                      <button
                        onClick={() => onAcknowledge(alert.alert_id)}
                        className="px-3.5 py-1.5 rounded-lg bg-blue-600 hover:bg-blue-500 text-white text-xs font-bold transition-colors"
                      >
                        Acknowledge
                      </button>
                    )}

                    {alert.status === 'ACKNOWLEDGED' && (
                      <button
                        onClick={() => onResolve(alert.alert_id, 'Slope stabilized and drainage cleared')}
                        className="px-3.5 py-1.5 rounded-lg bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold transition-colors"
                      >
                        Resolve Alert
                      </button>
                    )}

                    {alert.status === 'RESOLVED' && (
                      <span className="px-3 py-1.5 rounded-lg bg-emerald-950/60 text-emerald-400 border border-emerald-800/60 text-xs font-mono font-bold flex items-center gap-1">
                        <CheckCircle className="w-3.5 h-3.5" />
                        <span>RESOLVED</span>
                      </span>
                    )}

                    <button
                      onClick={() => setExpandedAlertId(isExpanded ? null : alert.alert_id)}
                      className="p-1.5 rounded-lg bg-slate-800 text-slate-400 hover:text-white"
                      title="Expand Standard Operating Procedures"
                    >
                      {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                    </button>
                  </div>
                </div>

                {/* Expanded Standard Operating Procedures (SOPs) */}
                {isExpanded && (
                  <div className="mt-4 pt-4 border-t border-slate-800/80 space-y-3 text-xs">
                    <div className="p-3 rounded-lg bg-slate-900/60 border border-slate-800">
                      <strong className="text-slate-200 font-mono uppercase block mb-1">Recommended Response Directive:</strong>
                      <p className="text-slate-300">{alert.recommended_action}</p>
                    </div>

                    {alert.sop_actions && alert.sop_actions.length > 0 && (
                      <div>
                        <strong className="text-slate-300 font-mono uppercase flex items-center gap-1.5 mb-2">
                          <ListChecks className="w-4 h-4 text-blue-400" />
                          <span>Incident Command Standard Operating Procedure (SOP) Checklist:</span>
                        </strong>
                        <ul className="space-y-1.5 pl-2">
                          {alert.sop_actions.map((act, i) => (
                            <li key={i} className="flex items-start gap-2 text-slate-300">
                              <span className="w-1.5 h-1.5 rounded-full bg-blue-400 mt-1.5"></span>
                              <span>{act}</span>
                            </li>
                          ))}
                        </ul>
                      </div>
                    )}
                  </div>
                )}
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
