import React from 'react';
import { useWebSocket } from '../context/WebSocketContext';
import { Activity, Award, Flame, Zap } from 'lucide-react';

interface QuickStatsProps {
  claimedCount: number;
  watchlistCount: number;
}

export const QuickStats: React.FC<QuickStatsProps> = ({ claimedCount, watchlistCount }) => {
  const { status } = useWebSocket();

  const isMining = status?.state === 'MINING';
  const isPaused = status?.state === 'PAUSED';

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
      {/* Miner Status */}
      <div className="bg-slate-900/60 backdrop-blur-sm border border-slate-800 p-4 rounded-xl shadow-sm">
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium text-slate-400">Mining Status</span>
          <div className="p-2 rounded-lg bg-purple-500/10 text-purple-400">
            <Activity className="w-4 h-4" />
          </div>
        </div>
        <div className="mt-2 flex items-baseline space-x-2">
          <span
            className={`text-xl font-bold ${
              isMining
                ? 'text-emerald-400'
                : isPaused
                ? 'text-amber-400'
                : 'text-slate-300'
            }`}
          >
            {status?.state || 'IDLE'}
          </span>
        </div>
        <p className="text-[11px] text-slate-500 mt-1">
          {isMining ? 'Broadcasting minute heartbeats' : 'Waiting for active campaign'}
        </p>
      </div>

      {/* Drops Claimed */}
      <div className="bg-slate-900/60 backdrop-blur-sm border border-slate-800 p-4 rounded-xl shadow-sm">
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium text-slate-400">Total Claimed</span>
          <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400">
            <Award className="w-4 h-4" />
          </div>
        </div>
        <div className="mt-2 flex items-baseline space-x-2">
          <span className="text-xl font-bold text-white">{claimedCount}</span>
          <span className="text-xs text-slate-400">rewards</span>
        </div>
        <p className="text-[11px] text-slate-500 mt-1">
          Session: +{status?.total_drops_claimed_session || 0}
        </p>
      </div>

      {/* Watchlisted Games */}
      <div className="bg-slate-900/60 backdrop-blur-sm border border-slate-800 p-4 rounded-xl shadow-sm">
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium text-slate-400">Watchlist</span>
          <div className="p-2 rounded-lg bg-blue-500/10 text-blue-400">
            <Flame className="w-4 h-4" />
          </div>
        </div>
        <div className="mt-2 flex items-baseline space-x-2">
          <span className="text-xl font-bold text-white">{watchlistCount}</span>
          <span className="text-xs text-slate-400">games</span>
        </div>
        <p className="text-[11px] text-slate-500 mt-1">Priority-ordered polling</p>
      </div>

      {/* Headless Bandwidth Saved */}
      <div className="bg-slate-900/60 backdrop-blur-sm border border-slate-800 p-4 rounded-xl shadow-sm">
        <div className="flex items-center justify-between">
          <span className="text-xs font-medium text-slate-400">Bandwidth Saved</span>
          <div className="p-2 rounded-lg bg-indigo-500/10 text-indigo-400">
            <Zap className="w-4 h-4" />
          </div>
        </div>
        <div className="mt-2 flex items-baseline space-x-2">
          <span className="text-xl font-bold text-indigo-400">~99.9%</span>
        </div>
        <p className="text-[11px] text-slate-500 mt-1">Zero video / audio downloaded</p>
      </div>
    </div>
  );
};
