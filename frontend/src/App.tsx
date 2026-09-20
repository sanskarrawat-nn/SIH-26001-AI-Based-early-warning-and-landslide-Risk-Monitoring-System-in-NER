import {CoordinatorInbox} from './pages/VerifiedReports';
import {AccountsPage} from './pages/AccessPortal';
import {ResponsePage} from './pages/ResponsePage';
import { ReadinessPage } from './pages/ReadinessPage';
import { OfflineStatus } from './components/common/OfflineStatus';
import { OperationsPage } from './pages/OperationsPage';
import React, { useState, useEffect, useCallback, useRef } from 'react';
import { Navbar } from './components/layout/Navbar';
import { AlertBanner } from './components/layout/AlertBanner';
import { DashboardPage } from './pages/DashboardPage';
import { MapExplorerPage } from './pages/MapExplorerPage';
import { PredictionSimulatorPage } from './pages/PredictionSimulatorPage';
import { HistoricalAnalysisPage } from './pages/HistoricalAnalysisPage';
import { AlertsCenterPage } from './pages/AlertsCenterPage';
import { AdminSettingsPage } from './pages/AdminSettingsPage';
import { LocationItem, AlertItem, HistoricalLandslide, ThresholdSettings, PredictionOutput } from './types';
import { api } from './services/api';
import { ShieldAlert, Terminal, CheckCircle2 } from 'lucide-react';

export const App: React.FC<{accountRole?:'admin'|'coordinator'}> = ({accountRole='admin'}) => {
  const allowedTabs=accountRole==='admin'?['dashboard','map','predict','history','alerts','operations','response','readiness','admin','accounts']:['dashboard','map','predict','history','alerts','operations','response'];
  const getInitialTab = (): string => {
    try {
      const params = new URLSearchParams(window.location.search);
      if(params.has('response'))return 'response';
      const tab = params.get('tab');
      if (tab) return tab;
      const hash = window.location.hash.replace('#', '');
      if (hash) return hash;
    } catch {
      // fallback
    }
    return 'dashboard';
  };
  const [currentTab, selectTab] = useState<string>(()=>allowedTabs.includes(getInitialTab())?getInitialTab():(accountRole==='coordinator'?'response':'dashboard'));
  const setCurrentTab=(tab:string)=>selectTab(allowedTabs.includes(tab)?tab:'dashboard');
  useEffect(()=>{const open=()=>setCurrentTab('response');window.addEventListener('open-response',open);return()=>window.removeEventListener('open-response',open)},[]);
  const [locations, setLocations] = useState<LocationItem[]>([]);
  const [alerts, setAlerts] = useState<AlertItem[]>([]);
  const [historicalEvents, setHistoricalEvents] = useState<HistoricalLandslide[]>([]);
  const [thresholds, setThresholds] = useState<ThresholdSettings | null>(null);
  const [trendsData, setTrendsData] = useState<any>(null);
  const [modelMetrics, setModelMetrics] = useState<any>(null);

  const [selectedLocation, setSelectedLocation] = useState<LocationItem | null>(null);
  const [soundEnabled, setSoundEnabled] = useState<boolean>(false);
  const [loading, setLoading] = useState<boolean>(true);

  const [loadError,setLoadError]=useState('');
  const soundRef=useRef(soundEnabled); soundRef.current=soundEnabled;
  const knownAlerts=useRef(new Set<string>());
  // Play synthesized Web Audio Chime for Critical Alerts
  const playAlertSiren = useCallback(() => {
    if (!soundRef.current) return;
    try {
      const audioCtx = new (window.AudioContext || (window as any).webkitAudioContext)();
      const osc = audioCtx.createOscillator();
      const gain = audioCtx.createGain();
      osc.type = 'sawtooth';
      osc.frequency.setValueAtTime(587.33, audioCtx.currentTime); // D5
      osc.frequency.exponentialRampToValueAtTime(880.0, audioCtx.currentTime + 0.3); // A5
      gain.gain.setValueAtTime(0.15, audioCtx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.4);
      osc.connect(gain);
      gain.connect(audioCtx.destination);
      osc.start();
      osc.stop(audioCtx.currentTime + 0.4);
      osc.onended=()=>{void audioCtx.close();};
    } catch {
      // Audio context might be restricted before user interaction
    }
  }, [soundEnabled]);

  // Initial Data Fetching
  const loadInitialData = async () => {
    try {
      const results=await Promise.allSettled([api.getLocations(),api.getAlerts(),api.getHistoricalLandslides(),api.getThresholds(),api.getTrends(),api.getModelPerformance()]);
      const setters:any[]=[setLocations,setAlerts,setHistoricalEvents,setThresholds,setTrendsData,setModelMetrics];
      results.forEach((r,i)=>{if(r.status==='fulfilled')setters[i](r.value);});
      const locResult=results[0];
      if(locResult.status==='fulfilled'){try{localStorage.setItem('ner-locations-cache',JSON.stringify(locResult.value));}catch{}}
      else {try{setLocations(JSON.parse(localStorage.getItem('ner-locations-cache')||'[]'));}catch{}}
      if(results.some(r=>r.status==='rejected'))setLoadError('Some services are unavailable. Cached data may be stale. Retry when connected.');else setLoadError('');
      const alertResult=results[1];if(alertResult.status==='fulfilled')knownAlerts.current=new Set(alertResult.value.map(a=>a.alert_id));
    } catch (err) {
      setLoadError('Could not load dashboard data. Please retry.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadInitialData();
    window.addEventListener('online',loadInitialData);

    // Auto-refresh alerts and telemetry every 30s
    const pollInterval = setInterval(async () => {
      try {
        const [latestAlerts, latestLocations] = await Promise.all([
          api.getAlerts(),
          api.getLocations()
        ]);
        if(latestAlerts.some(a=>a.severity==='SEVERE'&&a.status==='ACTIVE'&&!knownAlerts.current.has(a.alert_id)))playAlertSiren();
        knownAlerts.current=new Set(latestAlerts.map(a=>a.alert_id));
        setAlerts(latestAlerts);
        setLocations(latestLocations);
        setLoadError('');
      } catch {
        // silent fail on background poll
      }
    }, 30000);

    return () => {clearInterval(pollInterval);window.removeEventListener('online',loadInitialData);};
  }, []);

  // Alert Actions
  const handleAcknowledgeAlert = async (alertId: string) => {
    try {
      const updated = await api.acknowledgeAlert(alertId, 'COMMAND_OFFICER_ON_DUTY');
      setAlerts(prev => prev.map(a => a.alert_id === alertId ? updated : a));
    } catch (e: any) {
      alert(e.message || 'Failed to acknowledge alert');
    }
  };

  const handleResolveAlert = async (alertId: string, notes: string) => {
    try {
      const updated = await api.resolveAlert(alertId, 'FIELD_ENGINEER', notes);
      setAlerts(prev => prev.map(a => a.alert_id === alertId ? updated : a));
    } catch (e: any) {
      alert(e.message || 'Failed to resolve alert');
    }
  };

  // Sync Telemetry for a Location
  const handleSyncTelemetry = async (locationId: string) => {
    const updated = await api.syncLocation(locationId);
    setLocations(prev => prev.map(l => l.location_id === locationId ? updated : l));
    if (selectedLocation?.location_id === locationId) {
      setSelectedLocation(updated);
    }
    // Refresh alerts as sync might have triggered one
    const latestAlerts = await api.getAlerts();
    setAlerts(latestAlerts);
  };

  // Prediction Callback
  const handlePredictionSuccess = async (pred: PredictionOutput) => {
    // Refresh alerts and locations after prediction
    const [latestAlerts, latestLocations, latestTrends] = await Promise.all([
      api.getAlerts(),
      api.getLocations(),
      api.getTrends()
    ]);
    setAlerts(latestAlerts);
    setLocations(latestLocations);
    setTrendsData(latestTrends);

    if (pred.risk_level === 'SEVERE') {
      playAlertSiren();
    }
  };

  const activeAlertCount = alerts.filter(a => a.status === 'ACTIVE').length;
  const severeCount = alerts.filter(a => a.severity === 'SEVERE' && a.status === 'ACTIVE').length;

  return (
    <div className="command-app min-h-screen flex flex-col bg-[#070d19] text-slate-100 selection:bg-rose-500 selection:text-white">
      {/* Top Navigation */}
      <Navbar
        allowedTabs={allowedTabs}
        currentTab={currentTab}
        onSelectTab={setCurrentTab}
        activeAlertCount={activeAlertCount}
        severeCount={severeCount}
        soundEnabled={soundEnabled}
        onToggleSound={() => setSoundEnabled(!soundEnabled)}
      />

      <OfflineStatus />
      <CoordinatorInbox onOpen={()=>{sessionStorage.setItem('response-review','1');setCurrentTab('response');window.dispatchEvent(new Event('open-verification'))}}/>
      {/* Persistent Emergency Warning Banner */}
      <AlertBanner
        alerts={alerts}
        onViewAlerts={() => setCurrentTab('alerts')}
      />

      {/* Main Command Center Body */}
      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6">
        {loadError&&<div role="alert" className="mb-4 rounded-lg bg-amber-950 border border-amber-700 p-4">{loadError} <button className="underline" onClick={loadInitialData}>Retry</button></div>}
        {loading ? (
          <div className="h-[60vh] flex flex-col items-center justify-center space-y-4">
            <div className="w-10 h-10 border-4 border-blue-500 border-t-transparent rounded-full animate-spin"></div>
            <p className="text-xs font-mono text-slate-400">CONNECTING TO NER EARLY WARNING SYSTEM...</p>
          </div>
        ) : (
          <>
            {currentTab === 'dashboard' && (
              <DashboardPage
                locations={locations}
                alerts={alerts}
                historicalEvents={historicalEvents}
                selectedLocation={selectedLocation}
                onSelectLocation={setSelectedLocation}
                onAcknowledgeAlert={handleAcknowledgeAlert}
                onSelectAlert={(a) => {
                  const targetLoc = locations.find(l => l.location_id === a.location_id);
                  if (targetLoc) setSelectedLocation(targetLoc);
                  setCurrentTab('map');
                }}
                onOpenSimulator={(loc) => {
                  if (loc) setSelectedLocation(loc);
                  setCurrentTab('predict');
                }}
                onSyncTelemetry={handleSyncTelemetry}
                onNavigateTab={setCurrentTab}
              />
            )}

            {currentTab === 'map' && (
              <MapExplorerPage
                locations={locations}
                historicalEvents={historicalEvents}
                selectedLocation={selectedLocation}
                onSelectLocation={setSelectedLocation}
                onOpenSimulator={(loc) => {
                  setSelectedLocation(loc);
                  setCurrentTab('predict');
                }}
                onSyncTelemetry={handleSyncTelemetry}
              />
            )}

            {currentTab === 'predict' && (
              <PredictionSimulatorPage
                locations={locations}
                selectedLocation={selectedLocation}
                onPredictionSuccess={handlePredictionSuccess}
              />
            )}

            {currentTab === 'history' && (
              <HistoricalAnalysisPage
                historicalEvents={historicalEvents}
                trendsData={trendsData}
                modelMetrics={modelMetrics}
              />
            )}

            {currentTab === 'alerts' && (
              <AlertsCenterPage
                alerts={alerts}
                onAcknowledge={handleAcknowledgeAlert}
                onResolve={handleResolveAlert}
              />
            )}

            {currentTab === 'accounts' && accountRole==='admin' && <AccountsPage/>}
            {currentTab === 'response' && <ResponsePage locations={locations} />}
            {currentTab === 'readiness' && <ReadinessPage locations={locations} />}
          {currentTab === 'operations' && <OperationsPage locations={locations} accountRole={accountRole}/>}
            {currentTab === 'admin' && (
              <AdminSettingsPage
                thresholds={thresholds}
                locations={locations}
                onThresholdsUpdated={(th) => setThresholds(th)}
                onLocationAdded={(newLoc) => setLocations(prev => [newLoc, ...prev])}
                onLocationDeleted={(id) => setLocations(prev => prev.filter(l => l.location_id !== id))}
              />
            )}
          </>
        )}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800/80 bg-[#070d19] py-4 text-xs text-slate-500">
        <div className="max-w-7xl mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-2">
          <div className="flex items-center gap-2">
            <span className="font-mono font-bold text-slate-400">NER-LEWS</span>
            <span>&bull;</span>
            <span>AI-Based Landslide Prediction and Early Warning System</span>
          </div>
          <div className="flex items-center gap-4 text-[11px] font-mono">
            <span className="flex items-center gap-1 text-emerald-400">
              <CheckCircle2 className="w-3.5 h-3.5" />
              <span>Prototype · validate before operational use</span>
            </span>
            <span className="text-slate-600">|</span>
            <span>Open-Meteo / simulated environmental data</span>
          </div>
        </div>
      </footer>
    </div>
  );
};

export default App;
