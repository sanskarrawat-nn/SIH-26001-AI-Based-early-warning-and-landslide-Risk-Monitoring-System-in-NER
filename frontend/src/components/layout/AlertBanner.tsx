import React from 'react';
import { AlertTriangle, ChevronRight, ShieldAlert } from 'lucide-react';
import { LocalizedAlert } from '../common/AlertLanguage';
import { AlertItem } from '../../types';

interface AlertBannerProps {
  alerts: AlertItem[];
  onViewAlerts: () => void;
}

export const AlertBanner: React.FC<AlertBannerProps> = ({ alerts, onViewAlerts }) => {
  const severeAlerts = alerts.filter(a => a.severity === 'SEVERE' && a.status === 'ACTIVE');
  const highAlerts = alerts.filter(a => a.severity === 'HIGH' && a.status === 'ACTIVE');

  if (severeAlerts.length === 0 && highAlerts.length === 0) {
    return null;
  }

  const isCritical = severeAlerts.length > 0;
  const topAlert = severeAlerts[0] || highAlerts[0];

  return (
    <div className={`px-4 py-2.5 text-xs border-b ${
      isCritical
        ? 'bg-rose-950/80 border-rose-700/60 text-rose-100 shadow-md shadow-rose-950/40'
        : 'bg-amber-950/80 border-amber-700/60 text-amber-100'
    }`}>
      <div className="max-w-7xl mx-auto flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2.5">
          <div className={`p-1 rounded ${isCritical ? 'bg-rose-600 animate-pulse text-white' : 'bg-amber-600 text-white'}`}>
            {isCritical ? <ShieldAlert className="w-4 h-4" /> : <AlertTriangle className="w-4 h-4" />}
          </div>
          <div>
            <span className="font-extrabold uppercase tracking-wide mr-2">
              {isCritical ? `CRITICAL WARNING (${severeAlerts.length} Active)` : `HIGH ADVISORY (${highAlerts.length} Active)`}:
            </span>
            <div className="font-medium text-slate-200">
              <LocalizedAlert alert={topAlert}/>
              {topAlert.title} — Risk Score {topAlert.risk_score.toFixed(1)}/100
            </div>
          </div>
        </div>

        <button
          onClick={onViewAlerts}
          className={`flex items-center gap-1 font-bold px-3 py-1 rounded transition-colors ${
            isCritical
              ? 'bg-rose-600 hover:bg-rose-500 text-white shadow-sm'
              : 'bg-amber-600 hover:bg-amber-500 text-white'
          }`}
        >
          <span>Acknowledge & View SOPs</span>
          <ChevronRight className="w-3.5 h-3.5" />
        </button>
      </div>
    </div>
  );
};
