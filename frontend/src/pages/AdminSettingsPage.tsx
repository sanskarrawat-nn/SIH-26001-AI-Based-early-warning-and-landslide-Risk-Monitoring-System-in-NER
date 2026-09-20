import { WhatsAppSettings } from '../components/admin/WhatsAppSettings';
import React from 'react';
import { ThresholdConfig } from '../components/admin/ThresholdConfig';
import { LocationManager } from '../components/admin/LocationManager';
import { SystemStatus } from '../components/admin/SystemStatus';
import { ThresholdSettings, LocationItem } from '../types';

interface AdminSettingsPageProps {
  thresholds: ThresholdSettings | null;
  locations: LocationItem[];
  onThresholdsUpdated: (newSettings: ThresholdSettings) => void;
  onLocationAdded: (newLoc: LocationItem) => void;
  onLocationDeleted: (locId: string) => void;
}

export const AdminSettingsPage: React.FC<AdminSettingsPageProps> = ({
  thresholds,
  locations,
  onThresholdsUpdated,
  onLocationAdded,
  onLocationDeleted,
}) => {
  return (
    <div className="space-y-6">
      <SystemStatus />
      <WhatsAppSettings locations={locations} />
      <ThresholdConfig thresholds={thresholds} onUpdated={onThresholdsUpdated} />
      <LocationManager
        locations={locations}
        onLocationAdded={onLocationAdded}
        onLocationDeleted={onLocationDeleted}
      />
    </div>
  );
};
