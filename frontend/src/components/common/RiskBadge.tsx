import React from 'react';
import { RiskLevel } from '../../types';

interface RiskBadgeProps {
  level: RiskLevel | string;
  size?: 'sm' | 'md' | 'lg';
  showPulse?: boolean;
}

export const RiskBadge: React.FC<RiskBadgeProps> = ({ level, size = 'md', showPulse = false }) => {
  const normLevel = (level || 'LOW').toUpperCase();

  const colorStyles: Record<string, string> = {
    LOW: 'bg-emerald-950/70 text-emerald-400 border-emerald-500/30',
    MODERATE: 'bg-amber-950/70 text-amber-400 border-amber-500/30',
    HIGH: 'bg-orange-950/70 text-orange-400 border-orange-500/30',
    SEVERE: 'bg-rose-950/80 text-rose-300 border-rose-500/50 shadow-rose-900/50',
  };

  const dotStyles: Record<string, string> = {
    LOW: 'bg-emerald-400',
    MODERATE: 'bg-amber-400',
    HIGH: 'bg-orange-400',
    SEVERE: 'bg-rose-500 animate-ping',
  };

  const sizeStyles: Record<string, string> = {
    sm: 'text-xs px-2 py-0.5',
    md: 'text-xs px-2.5 py-1 font-semibold',
    lg: 'text-sm px-3.5 py-1.5 font-bold',
  };

  const currentStyle = colorStyles[normLevel] || colorStyles.LOW;
  const currentDot = dotStyles[normLevel] || dotStyles.LOW;
  const currentSize = sizeStyles[size];

  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border shadow-sm tracking-wider uppercase font-mono ${currentStyle} ${currentSize}`}
    >
      <span className={`relative flex h-2 w-2`}>
        {showPulse && normLevel === 'SEVERE' && (
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-rose-400 opacity-75"></span>
        )}
        <span className={`relative inline-flex rounded-full h-2 w-2 ${currentDot}`}></span>
      </span>
      {normLevel}
    </span>
  );
};
