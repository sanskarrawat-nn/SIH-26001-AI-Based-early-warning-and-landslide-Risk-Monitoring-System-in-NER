import React, { useEffect, useState } from 'react';
import { Activity, Database, Cpu, Cloud, CheckCircle2, AlertTriangle, RefreshCw } from 'lucide-react';
import { SystemHealth } from '../../types';
import { api } from '../../services/api';

export const SystemStatus: React.FC = () => {
  const [health, setHealth] = useState<SystemHealth | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  const checkHealth = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.getHealth();
      setHealth(data);
    } catch (err: any) {
      setError(err.message || 'System diagnostic check failed');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    checkHealth();
  }, []);

  return (
    <div className="p-6 rounded-xl bg-[#0c1527] border border-slate-800">
      <div className="flex items-center justify-between mb-4">
        <div>
          <h3 className="text-sm font-semibold text-white uppercase tracking-wider flex items-center gap-2">
            <Activity className="w-4 h-4 text-emerald-400" />
            <span>Operational System Diagnostics & Microservices</span>
          </h3>
          <p className="text-xs text-slate-400">
            Real-time backend heartbeat, ORM database connectivity, and ML inference pipelines
          </p>
        </div>
        <button
          onClick={checkHealth}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 text-xs font-mono font-medium transition-colors"
        >
          <RefreshCw className={`w-3.5 h-3.5 ${loading ? 'animate-spin' : ''}`} />
          <span>Ping /health</span>
        </button>
      </div>

      {error && (
        <div className="p-3 rounded-lg bg-rose-950/60 border border-rose-800 text-xs text-rose-300 mb-4 flex items-center gap-2">
          <AlertTriangle className="w-4 h-4" />
          <span>{error}</span>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        {/* Core API Service */}
        <div className="p-4 rounded-lg bg-slate-900/50 border border-slate-800">
          <div className="flex items-center justify-between text-xs font-mono text-slate-400 mb-2">
            <span>CORE BACKEND</span>
            <Activity className="w-4 h-4 text-emerald-400" />
          </div>
          <div className="flex items-center gap-2">
            <span className={`w-2.5 h-2.5 rounded-full ${health?.status === 'healthy' ? 'bg-emerald-500' : health ? 'bg-amber-500' : 'bg-rose-500'}`}></span>
            <span className="font-bold text-sm text-white">{health?.service || (loading ? 'Connecting...' : 'FastAPI Microservice')}</span>
          </div>
          <span className="text-[10px] text-slate-500 font-mono mt-1 block">
            v{health?.version || '1.0.0'} &bull; Status: {health?.status?.toUpperCase() || (loading ? 'CHECKING' : 'OFFLINE')}
          </span>
        </div>

        {/* Database */}
        <div className="p-4 rounded-lg bg-slate-900/50 border border-slate-800">
          <div className="flex items-center justify-between text-xs font-mono text-slate-400 mb-2">
            <span>RELATIONAL DB</span>
            <Database className="w-4 h-4 text-blue-400" />
          </div>
          <div className="flex items-center gap-2">
            <span className={`w-2.5 h-2.5 rounded-full ${health?.database === 'healthy' ? 'bg-emerald-500' : health ? 'bg-amber-500' : 'bg-rose-500'}`}></span>
            <span className="font-bold text-sm text-white">PostgreSQL / SQLite</span>
          </div>
          <span className="text-[10px] text-slate-500 font-mono mt-1 block">
            ORM: SQLAlchemy 2.0 &bull; {health ? (health.database === 'healthy' ? 'Connected' : health.database) : (loading ? 'Checking...' : 'Disconnected')}
          </span>
        </div>

        {/* ML Engine */}
        <div className="p-4 rounded-lg bg-slate-900/50 border border-slate-800">
          <div className="flex items-center justify-between text-xs font-mono text-slate-400 mb-2">
            <span>ML ENSEMBLE</span>
            <Cpu className="w-4 h-4 text-purple-400" />
          </div>
          <div className="flex items-center gap-2">
            <span className={`w-2.5 h-2.5 rounded-full ${health?.ml_engine === 'loaded' ? 'bg-emerald-500' : health ? 'bg-amber-500' : 'bg-rose-500'}`}></span>
            <span className="font-bold text-sm text-white">{health?.ml_engine ? (health.ml_engine === 'loaded' ? 'Calibrated & Loaded' : health.ml_engine) : (loading ? 'Loading...' : 'Unloaded')}</span>
          </div>
          <span className="text-[10px] text-slate-500 font-mono mt-1 block">Ensemble: Random Forest + Platt Scaling</span>
        </div>

        {/* Weather Provider */}
        <div className="p-4 rounded-lg bg-slate-900/50 border border-slate-800">
          <div className="flex items-center justify-between text-xs font-mono text-slate-400 mb-2">
            <span>METEOROLOGY</span>
            <Cloud className="w-4 h-4 text-cyan-400" />
          </div>
          <div className="flex items-center gap-2">
            <span className={`w-2.5 h-2.5 rounded-full ${health ? 'bg-emerald-500' : 'bg-amber-500'}`}></span>
            <span className="font-bold text-sm text-white uppercase">{health?.weather_provider || 'Hybrid (Open-Meteo / SIM)'}</span>
          </div>
          <span className="text-[10px] text-slate-500 font-mono mt-1 block">Live API with Physical Sensor Fallback</span>
        </div>
      </div>
    </div>
  );
};
