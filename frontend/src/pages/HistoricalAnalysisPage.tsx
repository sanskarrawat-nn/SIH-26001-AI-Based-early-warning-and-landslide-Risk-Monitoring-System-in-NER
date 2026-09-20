import React, { useState } from 'react';
import { HistoricalCatalog } from '../components/history/HistoricalCatalog';
import { TimeSeriesTrends } from '../components/history/TimeSeriesTrends';
import { ModelMetricsView } from '../components/history/ModelMetricsView';
import { HistoricalLandslide } from '../types';
import { FileSpreadsheet, TrendingUp, Cpu } from 'lucide-react';

interface HistoricalAnalysisPageProps {
  historicalEvents: HistoricalLandslide[];
  trendsData: {
    timeseries: any[];
    state_breakdown: any[];
  } | null;
  modelMetrics: any | null;
}

export const HistoricalAnalysisPage: React.FC<HistoricalAnalysisPageProps> = ({
  historicalEvents,
  trendsData,
  modelMetrics
}) => {
  const [activeSubTab, setActiveSubTab] = useState<'catalog' | 'trends' | 'model'>('catalog');

  return (
    <div className="space-y-6">
      {/* Subtabs Header */}
      <div className="flex items-center gap-2 p-1.5 rounded-xl bg-[#0c1527] border border-slate-800 w-fit text-xs font-semibold">
        <button
          onClick={() => setActiveSubTab('catalog')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
            activeSubTab === 'catalog'
              ? 'bg-purple-600 text-white shadow'
              : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
          }`}
        >
          <FileSpreadsheet className="w-4 h-4" />
          <span>Historical GSI Catalog</span>
        </button>

        <button
          onClick={() => setActiveSubTab('trends')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
            activeSubTab === 'trends'
              ? 'bg-purple-600 text-white shadow'
              : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
          }`}
        >
          <TrendingUp className="w-4 h-4" />
          <span>Rainfall & Risk Trends</span>
        </button>

        <button
          onClick={() => setActiveSubTab('model')}
          className={`flex items-center gap-2 px-4 py-2 rounded-lg transition-colors ${
            activeSubTab === 'model'
              ? 'bg-purple-600 text-white shadow'
              : 'text-slate-400 hover:text-white hover:bg-slate-800/60'
          }`}
        >
          <Cpu className="w-4 h-4" />
          <span>Model Architecture & Metrics</span>
        </button>
      </div>

      {/* Subtab Content */}
      {activeSubTab === 'catalog' && (
        <HistoricalCatalog events={historicalEvents} />
      )}

      {activeSubTab === 'trends' && (
        <TimeSeriesTrends
          timeseries={trendsData?.timeseries || []}
          stateBreakdown={trendsData?.state_breakdown || []}
        />
      )}

      {activeSubTab === 'model' && (
        <ModelMetricsView metrics={modelMetrics} />
      )}
    </div>
  );
};
