import React from 'react';

interface StatCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  icon: React.ReactNode;
  trend?: {
    value: string;
    isUp: boolean;
  };
  highlight?: 'default' | 'danger' | 'warning' | 'success';
}

export const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  subtitle,
  icon,
  trend,
  highlight = 'default'
}) => {
  const highlightStyles = {
    default: 'border-slate-800 bg-[#0c1527] hover:border-slate-700',
    danger: 'border-rose-900/60 bg-rose-950/20 hover:border-rose-700/80 shadow-lg shadow-rose-950/20',
    warning: 'border-amber-900/60 bg-amber-950/20 hover:border-amber-700/80',
    success: 'border-emerald-900/60 bg-emerald-950/20 hover:border-emerald-700/80',
  };

  const textHighlights = {
    default: 'text-white',
    danger: 'text-rose-400',
    warning: 'text-amber-400',
    success: 'text-emerald-400',
  };

  return (
    <div className={`p-5 rounded-xl border transition-all duration-200 ${highlightStyles[highlight]}`}>
      <div className="flex items-center justify-between">
        <span className="text-xs font-medium uppercase tracking-wider text-slate-400">{title}</span>
        <div className="p-2 rounded-lg bg-slate-800/60 text-slate-300">
          {icon}
        </div>
      </div>
      <div className="mt-3 flex items-baseline gap-2">
        <span className={`text-3xl font-bold font-mono tracking-tight ${textHighlights[highlight]}`}>
          {value}
        </span>
        {trend && (
          <span className={`text-xs font-semibold ${trend.isUp ? 'text-rose-400' : 'text-emerald-400'}`}>
            {trend.isUp ? '↑' : '↓'} {trend.value}
          </span>
        )}
      </div>
      {subtitle && (
        <p className="mt-1.5 text-xs text-slate-400 truncate">{subtitle}</p>
      )}
    </div>
  );
};
