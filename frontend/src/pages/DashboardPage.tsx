import React from 'react';
import { MetricOverview } from '../components/dashboard/MetricOverview';
import { RiskChart } from '../components/dashboard/RiskChart';
import { RecentAlertsTable } from '../components/dashboard/RecentAlertsTable';
import { GISMap } from '../components/map/GISMap';
import { LocationDrawer } from '../components/map/LocationDrawer';
import { LocationItem, AlertItem, HistoricalLandslide } from '../types';
import { Map, Sliders, ArrowRight } from 'lucide-react';

interface DashboardPageProps {
  locations: LocationItem[];
  alerts: AlertItem[];
  historicalEvents: HistoricalLandslide[];
  selectedLocation: LocationItem | null;
  onSelectLocation: (loc: LocationItem) => void;
  onAcknowledgeAlert: (alertId: string) => void;
  onSelectAlert: (alert: AlertItem) => void;
  onOpenSimulator: (loc?: LocationItem) => void;
  onSyncTelemetry: (locId: string) => Promise<void>;
  onNavigateTab: (tab: string) => void;
}

export const DashboardPage: React.FC<DashboardPageProps> = ({
  locations,
  alerts,
  historicalEvents,
  selectedLocation,
  onSelectLocation,
  onAcknowledgeAlert,
  onSelectAlert,
  onOpenSimulator,
  onSyncTelemetry,
  onNavigateTab,
}) => {
  return (
    <div className="space-y-6">
      {/* 1. Metric Overview Cards */}
      <MetricOverview locations={locations} alerts={alerts} />

      {/* 2. Interactive Map Section with Quick Inspector */}
      <div className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-sm font-bold uppercase tracking-wider text-white font-mono flex items-center gap-2">
            <Map className="w-4 h-4 text-blue-400" />
            <span>North Eastern Region GIS Command Center</span>
          </h2>
          <button
            onClick={() => onNavigateTab('map')}
            className="flex items-center gap-1 text-xs text-blue-400 hover:text-blue-300 font-semibold"
          >
            <span>Full Map Explorer</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>

        <GISMap
          locations={locations}
          historicalEvents={historicalEvents}
          selectedLocation={selectedLocation}
          onSelectLocation={onSelectLocation}
        />
      </div>

      {/* 3. Hazard Distribution & Top Vulnerable Sites */}
      <RiskChart locations={locations} />

      {/* 4. Active Early Warnings & Crisis Dispatch */}
      <RecentAlertsTable
        alerts={alerts}
        onAcknowledge={onAcknowledgeAlert}
        onSelectAlert={onSelectAlert}
      />

      {/* Drawer */}
      <LocationDrawer
        location={selectedLocation}
        onClose={() => onSelectLocation(null as any)}
        onOpenSimulator={(loc) => onOpenSimulator(loc)}
        onSyncTelemetry={onSyncTelemetry}
      />
    </div>
  );
};
