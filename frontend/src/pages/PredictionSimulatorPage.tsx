import React from 'react';
import { ScenarioSimulator } from '../components/predict/ScenarioSimulator';
import { LocationItem, PredictionOutput } from '../types';

interface PredictionSimulatorPageProps {
  locations: LocationItem[];
  selectedLocation: LocationItem | null;
  onPredictionSuccess?: (pred: PredictionOutput) => void;
}

export const PredictionSimulatorPage: React.FC<PredictionSimulatorPageProps> = ({
  locations,
  selectedLocation,
  onPredictionSuccess
}) => {
  return (
    <div className="space-y-6">
      <ScenarioSimulator
        locations={locations}
        initialLocation={selectedLocation}
        onPredictionSuccess={onPredictionSuccess}
      />
    </div>
  );
};
