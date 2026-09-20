import React from 'react';
import { MapPin, AlertOctagon, AlertTriangle, Bell, Gauge, CloudRain } from 'lucide-react';
import { StatCard } from '../common/StatCard';
import { LocationItem, AlertItem } from '../../types';

interface MetricOverviewProps {
  locations: LocationItem[];
  alerts: AlertItem[];
}

export const MetricOverview: React.FC<MetricOverviewProps> = ({ locations, alerts }) => {
  const totalLocations = locations.length;
  const severeLocations = locations.filter(l => l.risk_level === 'SEVERE').length;
  const highLocations = locations.filter(l => l.risk_level === 'HIGH').length;
  const activeAlerts = alerts.filter(a => a.status === 'ACTIVE').length;

  const avgRisk = totalLocations > 0
    ? (locations.reduce((acc, l) => acc + (l.current_risk_score || 0), 0) / totalLocations).toFixed(1)
    : '0.0';

  const maxRainfall = totalLocations > 0
    ? Math.max(...locations.map(l => l.latest_measurements?.rainfall_24h || 0)).toFixed(1)
    : '0.0';

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
      <StatCard
        title="Monitored Sites"
        value={totalLocations}
        subtitle="All 8 North Eastern States"
        icon={<MapPin className="w-5 h-5 text-blue-400" />}
      />
      <StatCard
        title="Severe Risk Sites"
        value={severeLocations}
        subtitle="Score > 75 (Immediate Evacuation)"
        icon={<AlertOctagon className="w-5 h-5 text-rose-400" />}
        highlight={severeLocations > 0 ? 'danger' : 'default'}
      />
      <StatCard
        title="High Risk Sites"
        value={highLocations}
        subtitle="Score 50-75 (Preventive Action)"
        icon={<AlertTriangle className="w-5 h-5 text-orange-400" />}
        highlight={highLocations > 0 ? 'warning' : 'default'}
      />
      <StatCard
        title="Active Warnings"
        value={activeAlerts}
        subtitle="Unresolved Emergency Feeds"
        icon={<Bell className="w-5 h-5 text-amber-400" />}
        highlight={activeAlerts > 0 ? 'danger' : 'default'}
      />
      <StatCard
        title="Regional Mean Risk"
        value={`${avgRisk}/100`}
        subtitle="Himalayan Basin Average"
        icon={<Gauge className="w-5 h-5 text-indigo-400" />}
      />
      <StatCard
        title="Peak 24h Rain"
        value={`${maxRainfall} mm`}
        subtitle="Telemetry Max Burst"
        icon={<CloudRain className="w-5 h-5 text-cyan-400" />}
      />
    </div>
  );
};
