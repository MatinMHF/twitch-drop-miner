import React, { useState } from 'react';
import { useWebSocket } from '../context/WebSocketContext';
import { api } from '../services/api';
import {
  Play,
  Pause,
  RotateCw,
  Square,
  Gift,
  Sparkles,
  CheckCircle2,
  Zap,
} from 'lucide-react';

export const ActiveMiningCard: React.FC = () => {
  const { status } = useWebSocket();
  const [isActing, setIsActing] = useState(false);

  const handleControl = async (action: 'start' | 'stop' | 'pause' | 'resume' | 'force_check') => {
    try {
      setIsActing(true);
      await api.controlMiner(action);
    } catch (err: any) {
      alert(`Action failed: ${err.message}`);
    } finally {
      setIsActing(false);
    }
  };

  const isMining = status?.state === 'MINING';
  const isPaused = status?.state === 'PAUSED';
  const targets = status?.active_targets && status.active_targets.length > 0
    ? status.active_targets
    : (status?.active_game_name ? [{
        game_id: status.active_game_id || '',
        game_name: status.active_game_name || 'Watchlisted Game',
        campaign_id: status.active_campaign_id || '',
        campaign_name: status.active_campaign_name || 'Drop Campaign',
        drop_id: status.current_drop_id || '',
        drop_name: status.current_drop_name || 'Drop Reward',
      }] : []);

  return (
    <div className="bg-slate-900/80 backdrop-blur-md border border-slate-800 rounded-2xl p-6 shadow-xl relative overflow-hidden">
      {/* Background glow when mining */}
      {isMining && (
        <div className="absolute top-0 right-0 -mr-20 -mt-20 w-80 h-80 rounded-full bg-purple-600/10 blur-3xl pointer-events-none" />
      )}

      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-slate-800/80">
        <div>
          <div className="flex items-center space-x-2">
            <span
              className={`w-2.5 h-2.5 rounded-full ${
                isMining ? 'bg-emerald-400 animate-ping' : isPaused ? 'bg-amber-400' : 'bg-slate-500'
              }`}
            />
            <h2 className="text-xl font-bold text-white tracking-tight flex items-center gap-2">
              <span>Active Mining Operations</span>
              {isMining && targets.length > 0 && (
                <span className="flex items-center gap-1 text-xs font-semibold px-2.5 py-0.5 rounded-full bg-purple-500/10 text-purple-600 dark:text-purple-300 border border-purple-500/20">
                  <Zap className="w-3 h-3" />
                  <span>{targets.length} Active {targets.length === 1 ? 'Target' : 'Targets'}</span>
                </span>
              )}
            </h2>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            {isMining
              ? `Automated headless drop claimer is actively mining rewards for your watchlisted games.`
              : isPaused
              ? 'Mining paused. Resume when you are ready.'
              : 'Idle — Watching for eligible drop campaigns in your watchlist...'}
          </p>
        </div>

        {/* Action Controls */}
        <div className="flex items-center flex-wrap gap-2">
          {isMining ? (
            <button
              onClick={() => handleControl('pause')}
              disabled={isActing}
              className="flex items-center space-x-1.5 px-3.5 py-2 rounded-xl text-xs font-semibold bg-amber-500/10 hover:bg-amber-500/20 text-amber-600 dark:text-amber-300 border border-amber-500/30 transition-all disabled:opacity-50"
            >
              <Pause className="w-3.5 h-3.5" />
              <span>Pause</span>
            </button>
          ) : isPaused ? (
            <button
              onClick={() => handleControl('resume')}
              disabled={isActing}
              className="flex items-center space-x-1.5 px-3.5 py-2 rounded-xl text-xs font-semibold bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-600 dark:text-emerald-300 border border-emerald-500/30 transition-all disabled:opacity-50"
            >
              <Play className="w-3.5 h-3.5" />
              <span>Resume</span>
            </button>
          ) : (
            <button
              onClick={() => handleControl('start')}
              disabled={isActing}
              className="flex items-center space-x-1.5 px-3.5 py-2 rounded-xl text-xs font-semibold bg-purple-600 hover:bg-purple-500 text-white shadow-md shadow-purple-600/30 transition-all disabled:opacity-50"
            >
              <Play className="w-3.5 h-3.5" />
              <span>Start Miner</span>
            </button>
          )}

          <button
            onClick={() => handleControl('force_check')}
            disabled={isActing}
            className="flex items-center space-x-1.5 px-3.5 py-2 rounded-xl text-xs font-medium bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white border border-slate-700/60 transition-all disabled:opacity-50"
            title="Force immediate check of watchlist and drops"
          >
            <RotateCw className={`w-3.5 h-3.5 ${isActing ? 'animate-spin' : ''}`} />
            <span>Poll Now</span>
          </button>

          {isMining && (
            <button
              onClick={() => handleControl('stop')}
              disabled={isActing}
              className="flex items-center space-x-1.5 px-3.5 py-2 rounded-xl text-xs font-semibold bg-rose-500/10 hover:bg-rose-500/20 text-rose-600 dark:text-rose-300 border border-rose-500/30 transition-all disabled:opacity-50"
            >
              <Square className="w-3.5 h-3.5" />
              <span>Stop</span>
            </button>
          )}
        </div>
      </div>

      {/* Active Targets List */}
      {isMining && targets.length > 0 ? (
        <div className={`mt-6 grid gap-4 ${targets.length === 1 ? 'grid-cols-1' : 'grid-cols-1 md:grid-cols-2'}`}>
          {targets.map((target, idx) => (
            <div
              key={target.campaign_id || idx}
              className="bg-slate-950/60 border border-slate-800/80 rounded-xl p-4 relative overflow-hidden transition-all hover:border-slate-700 flex flex-col justify-between space-y-3"
            >
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-center space-x-2.5 min-w-0">
                  <div className="w-8 h-8 rounded-lg bg-purple-500/10 text-purple-600 dark:text-purple-400 flex items-center justify-center shrink-0 border border-purple-500/20">
                    <Sparkles className="w-4 h-4" />
                  </div>
                  <div className="min-w-0">
                    <span className="text-[10px] font-bold uppercase tracking-wider text-purple-600 dark:text-purple-400">
                      {target.game_name}
                    </span>
                    <h3 className="text-sm font-bold text-white truncate">
                      {target.drop_name || 'Drop Reward'}
                    </h3>
                  </div>
                </div>

                <span className="flex items-center space-x-1 text-[10px] font-semibold px-2 py-0.5 rounded-full bg-emerald-950/40 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30 shrink-0">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                  <span>Mining Active</span>
                </span>
              </div>

              <div className="flex items-center justify-between text-xs text-slate-400 pt-2 border-t border-slate-800/60">
                <div className="flex items-center space-x-1.5 min-w-0">
                  <Gift className="w-3.5 h-3.5 text-slate-500 shrink-0" />
                  <span className="truncate">{target.campaign_name || 'Active Campaign'}</span>
                </div>
                <div className="flex items-center space-x-1 text-[11px] text-purple-600 dark:text-purple-400 font-medium shrink-0">
                  <CheckCircle2 className="w-3 h-3 text-emerald-500" />
                  <span>Auto-Claim Enabled</span>
                </div>
              </div>
            </div>
          ))}
        </div>
      ) : (
        <div className="mt-6 py-8 px-4 text-center border border-dashed border-slate-800 rounded-xl bg-slate-950/30">
          <Gift className="w-10 h-10 text-slate-600 mx-auto mb-2" />
          <p className="text-sm font-medium text-slate-300">
            {status?.state === 'NO_ACCOUNT'
              ? 'No Twitch account connected. Click "Connect Twitch" in the header to authenticate.'
              : isPaused
              ? 'Miner is paused. Click "Resume" to continue.'
              : 'Miner is idle. Add games with active drops to your watchlist to start mining automatically.'}
          </p>
          <p className="text-xs text-slate-500 mt-1">
            Clean headless automated reward claimer running 24/7.
          </p>
        </div>
      )}
    </div>
  );
};

