import React, { useState, useEffect } from 'react';
import {
  Activity,
  MapPin,
  Sliders,
  History,
  Bell,
  Settings,
  ShieldAlert,
  Volume2,
  VolumeX,
  Radio
} from 'lucide-react';

interface NavbarProps {
  allowedTabs?: string[];
  currentTab: string;
  onSelectTab: (tab: string) => void;
  activeAlertCount: number;
  severeCount: number;
  soundEnabled: boolean;
  onToggleSound: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  allowedTabs,
  currentTab,
  onSelectTab,
  activeAlertCount,
  severeCount,
  soundEnabled,
  onToggleSound
}) => {
  const [timeStr, setTimeStr] = useState<string>('');

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setTimeStr(now.toLocaleTimeString('en-IN', { hour12: false, timeZone: 'Asia/Kolkata' }) + ' IST');
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  const navItems = [
    { id: 'dashboard', label: 'Dashboard', icon: <Activity className="w-4 h-4" /> },
    { id: 'map', label: 'GIS Explorer', icon: <MapPin className="w-4 h-4" /> },
    { id: 'predict', label: 'Prediction Engine', icon: <Sliders className="w-4 h-4" /> },
    { id: 'history', label: 'Historical Analysis', icon: <History className="w-4 h-4" /> },
    {
      id: 'alerts',
      label: 'Early Warnings',
      icon: <Bell className="w-4 h-4" />,
      badge: activeAlertCount > 0 ? activeAlertCount : undefined
    },
    { id: 'operations', label: 'Field Operations', icon: <MapPin className="w-4 h-4" /> },
    { id: 'response', label: 'Response Coordination', icon: <ShieldAlert className="w-4 h-4" /> },
    { id: 'readiness', label: 'Monitoring', icon: <Activity className="w-4 h-4" /> },
    { id: 'accounts', label: 'User Accounts', icon: <Settings className="w-4 h-4" /> },
    { id: 'admin', label: 'Settings', icon: <Settings className="w-4 h-4" /> },
  ].filter(item=>!allowedTabs||allowedTabs.includes(item.id));

  return (
    <header className="sticky top-0 z-40 bg-[#070d19]/95 backdrop-blur border-b border-slate-800">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          {/* Logo & Branding */}
          <div className="flex items-center gap-3 cursor-pointer" onClick={() => onSelectTab('dashboard')}>
            <div className="p-2 rounded-lg bg-gradient-to-br from-rose-600 to-amber-600 shadow-md shadow-rose-950/50">
              <ShieldAlert className="w-6 h-6 text-white" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <span className="text-lg font-extrabold tracking-wider font-mono text-white">NER-LEWS</span>
              </div>
              <div className="text-[11px] text-slate-400 font-medium leading-tight whitespace-nowrap">
                <p>North Eastern Region Early Warning</p>
                <p>Command Center</p>
              </div>
            </div>
          </div>

          {/* Navigation Links */}
          <nav className="hidden 2xl:flex items-center space-x-1">
            {navItems.map((item) => {
              const active = currentTab === item.id;
              return (
                <button
                  key={item.id}
                  onClick={() => onSelectTab(item.id)}
                  className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-semibold tracking-wide transition-colors ${
                    active
                      ? 'bg-blue-600/20 text-blue-400 border border-blue-500/30 shadow-sm'
                      : 'text-slate-300 hover:bg-slate-800/60 hover:text-white'
                  }`}
                >
                  {item.icon}
                  <span>{item.label}</span>
                  {item.badge !== undefined && (
                    <span className={`ml-1 px-1.5 py-0.2 rounded-full text-[10px] font-bold ${
                      severeCount > 0 ? 'bg-rose-600 text-white animate-pulse' : 'bg-amber-600 text-white'
                    }`}>
                      {item.badge}
                    </span>
                  )}
                </button>
              );
            })}
          </nav>

          {/* Right Status / Telemetry */}
          <div className="flex items-center gap-4">
            <div className="hidden lg:flex items-center gap-2 px-3 py-1.5 rounded-lg bg-[#0c1527] border border-slate-800 text-xs font-mono text-slate-300">
              <Radio className="w-3.5 h-3.5 text-emerald-400 animate-pulse" />
              <span>MONITORING</span>
              <span className="text-slate-500">|</span>
              <span className="text-slate-200">{timeStr}</span>
            </div>

            {/* Audio Alarm Toggle */}
            <button
              onClick={onToggleSound}
              title={soundEnabled ? 'Mute Warning Siren' : 'Enable Warning Siren'}
              className={`p-2 rounded-lg border transition-colors ${
                soundEnabled
                  ? 'bg-rose-950/40 border-rose-800 text-rose-300 hover:bg-rose-900/50'
                  : 'bg-slate-800/60 border-slate-700 text-slate-400 hover:text-slate-200'
              }`}
            >
              {soundEnabled ? <Volume2 className="w-4 h-4" /> : <VolumeX className="w-4 h-4" />}
            </button>
          </div>
        </div>
      </div>
      <nav aria-label="Mobile navigation" className="flex 2xl:hidden overflow-x-auto gap-2 px-4 pb-3">{navItems.map(item=><button key={item.id} onClick={()=>onSelectTab(item.id)} className={`shrink-0 rounded-lg px-4 py-3 text-sm ${currentTab===item.id?'bg-blue-600':'bg-slate-800'}`}>{item.label}</button>)}</nav>
    </header>
  );
};
