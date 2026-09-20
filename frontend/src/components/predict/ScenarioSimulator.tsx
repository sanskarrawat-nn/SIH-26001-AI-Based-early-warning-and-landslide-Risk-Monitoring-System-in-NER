import React, { useState } from 'react';
import { Play, Sparkles, AlertTriangle, ShieldCheck, FileText, CheckCircle2 } from 'lucide-react';
import { PredictionInput, PredictionOutput, LocationItem } from '../../types';
import { ops } from '../../pages/OperationsPage';
import { api } from '../../services/api';
import { RiskGauge } from './RiskGauge';
import { FactorBreakdown } from './FactorBreakdown';

interface ScenarioSimulatorProps {
  locations: LocationItem[];
  initialLocation?: LocationItem | null;
  onPredictionSuccess?: (pred: PredictionOutput) => void;
}

export const ScenarioSimulator: React.FC<ScenarioSimulatorProps> = ({
  locations,
  initialLocation,
  onPredictionSuccess
}) => {
  const [selectedLocId, setSelectedLocId] = useState<string>(
    initialLocation ? initialLocation.location_id : (locations[0]?.location_id || 'LOC-AS-02')
  );

  const activeLoc = locations.find(l => l.location_id === selectedLocId) || locations[0];

  // Sliders State
  const [rainfall1h, setRainfall1h] = useState<number>(activeLoc?.latest_measurements?.rainfall_1h || 18.0);
  const [rainfall24h, setRainfall24h] = useState<number>(activeLoc?.latest_measurements?.rainfall_24h || 120.0);
  const [rainfall7d, setRainfall7d] = useState<number>(activeLoc?.latest_measurements?.rainfall_7d || 320.0);
  const [soilMoisture, setSoilMoisture] = useState<number>(activeLoc?.latest_measurements?.soil_moisture || 85.0);
  const [slope, setSlope] = useState<number>(activeLoc?.slope || 41.0);
  const [elevation, setElevation] = useState<number>(activeLoc?.elevation || 680.0);
  const [ndvi, setNdvi] = useState<number>(activeLoc?.latest_measurements?.vegetation_index || 0.45);

  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [prediction, setPrediction] = useState<PredictionOutput | null>(null);

  const [satelliteNote,setSatelliteNote]=useState('');
  const [satelliteBusy,setSatelliteBusy]=useState(false);

  // Handle Location Select
  React.useEffect(() => {
    try {
      const params = new URLSearchParams(window.location.search);
      if (params.get('autopredict') === 'true') {
        applyPreset('catastrophic');
        const timer = setTimeout(() => {
          handleRunPrediction();
        }, 300);
        return () => clearTimeout(timer);
      }
    } catch {}
  }, []);

  const handleLocationChange = (locId: string) => {
    setSatelliteNote('');
    setSelectedLocId(locId);
    const loc = locations.find(l => l.location_id === locId);
    if (loc) {
      setSlope(loc.slope);
      setElevation(loc.elevation);
      if (loc.latest_measurements) {
        setRainfall1h(loc.latest_measurements.rainfall_1h || 5.0);
        setRainfall24h(loc.latest_measurements.rainfall_24h || 40.0);
        setRainfall7d(loc.latest_measurements.rainfall_7d || 110.0);
        setSoilMoisture(loc.latest_measurements.soil_moisture || 55.0);
        setNdvi(loc.latest_measurements.vegetation_index || 0.60);
      }
    }
  };

  // Preset scenarios
  const applyPreset = (preset: 'dry' | 'moderate' | 'cloudburst' | 'catastrophic') => {
    setSatelliteNote('');
    if (preset === 'dry') {
      setRainfall1h(0.0);
      setRainfall24h(5.0);
      setRainfall7d(25.0);
      setSoilMoisture(22.0);
      setNdvi(0.75);
    } else if (preset === 'moderate') {
      setRainfall1h(8.0);
      setRainfall24h(55.0);
      setRainfall7d(160.0);
      setSoilMoisture(65.0);
      setNdvi(0.60);
    } else if (preset === 'cloudburst') {
      setRainfall1h(38.0);
      setRainfall24h(135.0);
      setRainfall7d(290.0);
      setSoilMoisture(88.0);
      setNdvi(0.42);
    } else if (preset === 'catastrophic') {
      setRainfall1h(45.0);
      setRainfall24h(220.0);
      setRainfall7d(540.0);
      setSoilMoisture(96.0);
      setNdvi(0.30);
    }
  };

  // Run Real Prediction
  const handleRunPrediction = async () => {
    setLoading(true);
    setError(null);

    const payload: PredictionInput = {
      location_id: selectedLocId,
      latitude: activeLoc?.latitude || 25.1783,
      longitude: activeLoc?.longitude || 93.0250,
      rainfall_1h: rainfall1h,
      rainfall_24h: rainfall24h,
      rainfall_7d: rainfall7d,
      soil_moisture: soilMoisture,
      slope: slope,
      elevation: elevation,
      terrain_roughness: activeLoc?.terrain_roughness || 20.0,
      vegetation_index: ndvi,
    };

    try {
      const res = await api.predictLandslide(payload);
      setPrediction(res);
      if (onPredictionSuccess) {
        onPredictionSuccess(res);
      }
    } catch (err: any) {
      setError(err.message || 'Prediction execution failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="space-y-6">
      <div className="rounded-xl border border-slate-700 p-3 text-sm space-y-2"><button className="rounded bg-blue-600 px-3 py-2 disabled:opacity-50" disabled={!activeLoc||satelliteBusy} onClick={async()=>{setSatelliteBusy(true);setSatelliteNote('');const requestedId=selectedLocId;try{const {observation}=await ops(`/satellite/${encodeURIComponent(requestedId)}`);if(!observation)throw new Error('Fetch an observation in Field Operations → Satellite NDVI first.');if(observation.stale)throw new Error('Satellite observation is stale; refresh it first.');setNdvi(observation.ndvi);setSatelliteNote(`Satellite NDVI loaded: ${observation.ndvi} · ${observation.source} · composite ${observation.composite_date}. Applies to this simulation only.`);}catch(e:any){setSatelliteNote(e.message);}finally{setSatelliteBusy(false);}}}>{satelliteBusy?'Loading…':'Use saved satellite NDVI in simulation'}</button>{satelliteNote&&<p role="status">{satelliteNote}</p>}</div>
      {/* Top Controls: Location & Presets */}
      <div className="p-5 rounded-xl bg-[#0c1527] border border-slate-800">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <h2 className="text-base font-bold text-white uppercase tracking-wider flex items-center gap-2">
              <Sparkles className="w-5 h-5 text-blue-400" />
              <span>What-If Landslide Scenario Simulator</span>
            </h2>
            <p className="text-xs text-slate-400 mt-1">
              Simulate extreme cloudbursts or continuous precipitation to evaluate the AI early warning response.
            </p>
          </div>

          {/* Location Selector */}
          <div className="flex items-center gap-2">
            <span className="text-xs text-slate-400 font-mono">SITE:</span>
            <select
              value={selectedLocId}
              disabled={satelliteBusy}
              onChange={(e) => handleLocationChange(e.target.value)}
              className="px-3 py-2 rounded-lg bg-slate-900 border border-slate-700 text-slate-200 text-xs font-semibold focus:outline-none focus:border-blue-500"
            >
              {locations.map((loc) => (
                <option key={loc.location_id} value={loc.location_id}>
                  {loc.name} ({loc.state})
                </option>
              ))}
            </select>
          </div>
        </div>

        {/* Rapid Stress Presets */}
        <div className="flex flex-wrap items-center gap-2 mt-4 pt-4 border-t border-slate-800">
          <span className="text-xs text-slate-400 font-mono mr-2">QUICK STRESS PRESETS:</span>
          <button
            onClick={() => applyPreset('dry')}
            className="px-3 py-1.5 rounded-lg bg-emerald-950/50 hover:bg-emerald-900/60 text-emerald-300 border border-emerald-800/60 text-xs font-mono font-medium transition-colors"
          >
            Dry Baseline (Low)
          </button>
          <button
            onClick={() => applyPreset('moderate')}
            className="px-3 py-1.5 rounded-lg bg-amber-950/50 hover:bg-amber-900/60 text-amber-300 border border-amber-800/60 text-xs font-mono font-medium transition-colors"
          >
            Monsoon Shower (Moderate)
          </button>
          <button
            onClick={() => applyPreset('cloudburst')}
            className="px-3 py-1.5 rounded-lg bg-orange-950/50 hover:bg-orange-900/60 text-orange-300 border border-orange-800/60 text-xs font-mono font-medium transition-colors"
          >
            Cloudburst Surge (High)
          </button>
          <button
            onClick={() => applyPreset('catastrophic')}
            className="px-3 py-1.5 rounded-lg bg-rose-950/50 hover:bg-rose-900/60 text-rose-300 border border-rose-800/60 text-xs font-mono font-medium transition-colors"
          >
            Extreme Cyclone Deluge (Severe)
          </button>
        </div>
      </div>

      {/* Main Grid: Sliders on Left, Prediction Output on Right */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Sliders Form (7 cols) */}
        <div className="lg:col-span-7 p-6 rounded-xl bg-[#0c1527] border border-slate-800 space-y-5">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300 font-mono">
            Environmental & Geotechnical Parameters
          </h3>

          {/* 24h Cumulative Rainfall */}
          <div>
            <div className="flex justify-between text-xs font-mono mb-1.5">
              <span className="text-slate-300 font-bold">24-Hour Cumulative Rainfall (R24)</span>
              <span className="text-cyan-400 font-bold">{rainfall24h.toFixed(1)} mm</span>
            </div>
            <input
              type="range"
              min="0"
              max="350"
              step="1"
              value={rainfall24h}
              onChange={(e) => setRainfall24h(parseFloat(e.target.value))}
              className="w-full h-2 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-cyan-400"
            />
            <div className="flex justify-between text-[10px] text-slate-500 font-mono mt-1">
              <span>0 mm (Dry)</span>
              <span>100 mm (Critical Threshold)</span>
              <span>350 mm (Extreme Deluge)</span>
            </div>
          </div>

          {/* 1h Rainfall Surge */}
          <div>
            <div className="flex justify-between text-xs font-mono mb-1.5">
              <span className="text-slate-300 font-bold">1-Hour Cloudburst Intensity (R1)</span>
              <span className="text-blue-400 font-bold">{rainfall1h.toFixed(1)} mm/h</span>
            </div>
            <input
              type="range"
              min="0"
              max="80"
              step="0.5"
              value={rainfall1h}
              onChange={(e) => setRainfall1h(parseFloat(e.target.value))}
              className="w-full h-2 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-blue-500"
            />
            <div className="flex justify-between text-[10px] text-slate-500 font-mono mt-1">
              <span>0 mm/h</span>
              <span>25 mm/h (Torrential)</span>
              <span>80 mm/h (Cloudburst)</span>
            </div>
          </div>

          {/* 7d Antecedent Rainfall */}
          <div>
            <div className="flex justify-between text-xs font-mono mb-1.5">
              <span className="text-slate-300 font-bold">7-Day Antecedent Rainfall (R7)</span>
              <span className="text-indigo-400 font-bold">{rainfall7d.toFixed(1)} mm</span>
            </div>
            <input
              type="range"
              min="0"
              max="700"
              step="5"
              value={rainfall7d}
              onChange={(e) => setRainfall7d(parseFloat(e.target.value))}
              className="w-full h-2 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-indigo-500"
            />
          </div>

          {/* Soil Moisture */}
          <div>
            <div className="flex justify-between text-xs font-mono mb-1.5">
              <span className="text-slate-300 font-bold">Soil Moisture Saturation</span>
              <span className="text-emerald-400 font-bold">{soilMoisture.toFixed(1)}%</span>
            </div>
            <input
              type="range"
              min="5"
              max="100"
              step="0.5"
              value={soilMoisture}
              onChange={(e) => setSoilMoisture(parseFloat(e.target.value))}
              className="w-full h-2 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-emerald-500"
            />
            <div className="flex justify-between text-[10px] text-slate-500 font-mono mt-1">
              <span>0% (Bone Dry)</span>
              <span>80% (Field Capacity)</span>
              <span>100% (Fully Liquified)</span>
            </div>
          </div>

          {/* Slope & Elevation */}
          <div className="grid grid-cols-2 gap-4">
            <div>
              <div className="flex justify-between text-xs font-mono mb-1.5">
                <span className="text-slate-300 font-bold">Slope Angle</span>
                <span className="text-amber-400 font-bold">{slope.toFixed(1)}°</span>
              </div>
              <input
                type="range"
                min="5"
                max="60"
                step="0.5"
                value={slope}
                onChange={(e) => setSlope(parseFloat(e.target.value))}
                className="w-full h-2 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-amber-500"
              />
            </div>

            <div>
              <div className="flex justify-between text-xs font-mono mb-1.5">
                <span className="text-slate-300 font-bold">Vegetation (NDVI)</span>
                <span className="text-teal-400 font-bold">{ndvi.toFixed(2)}</span>
              </div>
              <input
                type="range"
                min="-0.2"
                max="1.0"
                step="0.02"
                value={ndvi}
                onChange={(e) => {setSatelliteNote('');setNdvi(parseFloat(e.target.value));}}
                className="w-full h-2 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-teal-400"
              />
            </div>
          </div>

          {/* Execute Prediction Button */}
          <div className="pt-2">
            <button
              onClick={handleRunPrediction}
              disabled={loading}
              className="w-full py-3 px-6 rounded-xl bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white font-bold text-xs uppercase tracking-wider flex items-center justify-center gap-2.5 shadow-lg shadow-blue-900/40 transition-all disabled:opacity-50"
            >
              <Play className={`w-4 h-4 fill-white ${loading ? 'animate-spin' : ''}`} />
              <span>{loading ? 'Processing ML Pipeline...' : 'Run Dynamic Prediction & Early Warning'}</span>
            </button>
          </div>

          {error && (
            <div className="p-3 rounded-lg bg-rose-950/60 border border-rose-800 text-xs text-rose-300">
              {error}
            </div>
          )}
        </div>

        {/* Prediction Results & Explanation (5 cols) */}
        <div className="lg:col-span-5 space-y-6">
          {prediction ? (
            <>
              {/* Dynamic Risk Gauge */}
              <RiskGauge
                score={prediction.risk_score}
                level={prediction.risk_level}
                confidence={prediction.confidence}
                probability={prediction.probability}
              />

              {/* Contributing Factors */}
              <FactorBreakdown factors={prediction.risk_factors} />

              {/* Geotechnical Narrative */}
              <div className="p-5 rounded-xl bg-[#0c1527] border border-slate-800">
                <h3 className="text-xs font-bold uppercase tracking-wider text-slate-300 font-mono mb-2 flex items-center gap-2">
                  <FileText className="w-4 h-4 text-purple-400" />
                  <span>AI Geotechnical Diagnostic Report</span>
                </h3>
                <p className="text-xs text-slate-300 leading-relaxed bg-slate-900/40 p-3 rounded-lg border border-slate-800">
                  {prediction.explanation}
                </p>

                <div className="mt-3 p-3 rounded-lg bg-blue-950/30 border border-blue-900/40 text-xs text-blue-200">
                  <strong className="block font-mono text-[11px] uppercase mb-1">Standard Operating Procedure:</strong>
                  {prediction.recommendation}
                </div>
              </div>
            </>
          ) : (
            <div className="h-full min-h-[380px] flex flex-col items-center justify-center p-8 rounded-xl bg-[#0c1527] border border-slate-800 text-center text-slate-500">
              <Sparkles className="w-12 h-12 text-slate-700 mb-3" />
              <h4 className="text-sm font-bold text-slate-300">Prediction Engine Idle</h4>
              <p className="text-xs max-w-xs mt-1">
                Select a location or adjust the weather and slope sliders, then click "Run Dynamic Prediction" to test the model.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
