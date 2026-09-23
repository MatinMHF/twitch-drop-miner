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

  const isMining = status?.state === 'MINING' || status?.is_running;
  const isPaused = status?.state === 'PAUSED' || status?.is_paused;
  const accounts = status?.accounts || [];

  // Extract all active targets across all accounts
  const activeTargets: any[] = [];
  if (status?.active_targets && status.active_targets.length > 0) {
    activeTargets.push(...status.active_targets);
  } else if (accounts.length > 0) {
    accounts.forEach((acc: any) => {
      if (acc.active_drop) {
        activeTargets.push({
          ...acc.active_drop,
          twitch_username: acc.twitch_username,
          channel: acc.active_channel || acc.active_drop.channel,
        });
      }
    });
  } else if (status?.active_drop) {
    activeTargets.push({
      ...status.active_drop,
      channel: status.active_channel,
    });
  }

  const targets = activeTargets;

  return (
    <div className="bg-slate-900/80 backdrop-blur-md border border-slate-800 rounded-2xl p-6 shadow-xl relative">
      {/* Background glow when mining */}
      {isMining && (
        <div className="absolute top-0 right-0 -mr-20 -mt-20 w-80 h-80 rounded-full bg-purple-600/10 blur-3xl pointer-events-none overflow-hidden" />
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

      {/* Multi-Account Status Overview if > 1 account */}
      {accounts.length > 1 && (
        <div className="mt-6 p-4 bg-slate-950/60 border border-slate-800 rounded-xl space-y-3">
          <div className="text-xs font-semibold text-slate-300 flex items-center justify-between">
            <span>Concurrent Mining Accounts ({accounts.length})</span>
            <span className="text-emerald-400 text-[11px] font-mono">Parallel Execution</span>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
            {accounts.map((acc: any) => (
              <div
                key={acc.account_id}
                className="p-3 bg-slate-900 border border-slate-800/80 rounded-lg flex items-center justify-between text-xs"
              >
                <div>
                  <div className="font-bold text-white flex items-center space-x-1.5">
                    <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                    <span>@{acc.twitch_username}</span>
                  </div>
                  <div className="text-[11px] text-slate-400 mt-0.5">
                    {acc.active_drop?.drop_name ? `${acc.active_drop.drop_name} (${acc.active_drop.progress_percentage}%)` : acc.status_text || 'Idle'}
                  </div>
                </div>
                {acc.active_channel?.channel_display_name && (
                  <span className="text-[10px] bg-purple-500/10 text-purple-300 px-2 py-0.5 rounded border border-purple-500/20">
                    {acc.active_channel.channel_display_name}
                  </span>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Active Targets List */}
      {isMining && targets.length > 0 ? (
        <div className={`mt-6 grid gap-4 ${targets.length === 1 ? 'grid-cols-1' : 'grid-cols-1 md:grid-cols-2'}`}>
          {targets.map((target, idx) => (
            <div
              key={target.drop_id || target.campaign_id || idx}
              className="bg-slate-950/70 border border-slate-800 hover:border-purple-500/40 rounded-2xl p-5 relative transition-all shadow-lg flex flex-col justify-between space-y-4"
            >
              {/* Header with Game Cover, Drop Image, and Account Badge */}
              <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4">
                <div className="flex items-start space-x-4 min-w-0">
                  {/* Game Cover Art with Hover Zoom Popup */}
                  <div className="relative group/game shrink-0 cursor-pointer">
                    {target.game_image_url ? (
                      <img
                        src={target.game_image_url}
                        alt={target.game_name}
                        className="w-20 h-28 md:w-24 md:h-32 object-cover rounded-xl border border-slate-700/80 shadow-md bg-slate-900 group-hover/game:border-purple-400 group-hover/game:shadow-purple-500/20 transition-all duration-300"
                      />
                    ) : (
                      <div className="w-20 h-28 md:w-24 md:h-32 rounded-xl bg-purple-600/20 text-purple-400 flex items-center justify-center border border-purple-500/30">
                        <Sparkles className="w-8 h-8" />
                      </div>
                    )}

                    {/* Pop-up on Hover: High-Res Game Art */}
                    {target.game_image_url && (
                      <div className="absolute left-0 bottom-full mb-3 w-56 opacity-0 scale-95 pointer-events-none group-hover/game:opacity-100 group-hover/game:scale-100 transition-all duration-200 ease-out z-50 p-2.5 bg-slate-900/95 backdrop-blur-xl border border-purple-500/50 rounded-2xl shadow-2xl shadow-black/90 space-y-2">
                        <img
                          src={target.game_image_url}
                          alt={target.game_name}
                          className="w-full h-64 object-cover rounded-xl border border-slate-700/60 shadow-inner"
                        />
                        <div className="text-center px-1">
                          <span className="text-[10px] uppercase font-bold tracking-wider text-purple-400 block">Game Cover</span>
                          <span className="text-xs font-bold text-white block truncate">{target.game_name}</span>
                        </div>
                      </div>
                    )}
                  </div>

                  {/* Drop Reward thumbnail with Hover Zoom Popup */}
                  {target.drop_image_url && (
                    <div className="relative group/drop shrink-0 cursor-pointer">
                      <div className="w-16 h-16 md:w-20 md:h-20 rounded-xl bg-slate-900 border border-purple-500/40 p-1.5 shadow-md flex items-center justify-center group-hover/drop:border-purple-400 group-hover/drop:shadow-purple-500/20 transition-all duration-300">
                        <img
                          src={target.drop_image_url}
                          alt={target.drop_name}
                          title={target.drop_name}
                          className="w-full h-full object-contain rounded-lg"
                        />
                      </div>

                      {/* Pop-up on Hover: Large Drop Item Preview */}
                      <div className="absolute left-0 bottom-full mb-3 w-52 opacity-0 scale-95 pointer-events-none group-hover/drop:opacity-100 group-hover/drop:scale-100 transition-all duration-200 ease-out z-50 p-3 bg-slate-900/95 backdrop-blur-xl border border-purple-500/50 rounded-2xl shadow-2xl shadow-black/90 space-y-2">
                        <div className="w-full h-44 bg-slate-950/90 rounded-xl border border-slate-800 p-2 flex items-center justify-center">
                          <img
                            src={target.drop_image_url}
                            alt={target.drop_name}
                            className="w-full h-full object-contain drop-shadow-[0_8px_16px_rgba(168,85,247,0.35)]"
                          />
                        </div>
                        <div className="text-center px-1">
                          <span className="text-[10px] uppercase font-bold tracking-wider text-purple-400 block">Reward Item</span>
                          <span className="text-xs font-bold text-white block truncate" title={target.drop_name}>{target.drop_name}</span>
                          <span className="text-[10px] text-slate-400 block truncate">{target.campaign_name}</span>
                        </div>
                      </div>
                    </div>
                  )}

                  <div className="min-w-0 space-y-1.5 flex-1">
                    {/* Account Badge */}
                    {target.twitch_username && (
                      <div className="inline-flex items-center space-x-1.5 px-3 py-1 rounded-full bg-purple-500/10 text-purple-300 border border-purple-500/25 text-xs font-semibold">
                        <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse" />
                        <span>Account: @{target.twitch_username}</span>
                      </div>
                    )}

                    <div>
                      <span className="text-[11px] font-bold uppercase tracking-wider text-purple-400 block truncate">
                        {target.game_name}
                      </span>
                      <h3 className="text-base md:text-lg font-bold text-white truncate" title={target.drop_name}>
                        {target.drop_name || 'Drop Reward'}
                      </h3>
                      <p className="text-xs text-slate-400 truncate mt-0.5">
                        {target.campaign_name || 'Active Drops Campaign'}
                      </p>
                    </div>
                  </div>
                </div>

                <span className="flex items-center space-x-1.5 text-[10px] font-bold px-2.5 py-1 rounded-full bg-emerald-950/50 text-emerald-400 border border-emerald-500/30 shrink-0 self-start">
                  <span className="w-2 h-2 rounded-full bg-emerald-400 animate-ping" />
                  <span>Mining Active</span>
                </span>
              </div>

              {/* Progress Bar & Channel Info */}
              <div className="space-y-2 pt-1">
                <div className="flex items-center justify-between text-xs font-semibold">
                  <span className="text-slate-300 flex items-center gap-1.5 min-w-0">
                    <span className="text-slate-400">Streamer:</span>
                    <span className="text-purple-300 font-mono text-xs truncate">
                      @{target.channel?.channel_display_name || target.channel?.channel_login || 'live_streamer'}
                    </span>
                    {target.channel?.viewers_count ? (
                      <span className="text-[10px] text-slate-500 hidden sm:inline">({target.channel.viewers_count.toLocaleString()} viewers)</span>
                    ) : null}
                  </span>
                  <span className="text-purple-300 font-mono text-xs shrink-0">
                    {target.current_minutes || 0} / {target.required_minutes || 60}m ({target.progress_percent !== undefined ? target.progress_percent : (target.progress_percentage || 0)}%)
                  </span>
                </div>

                <div className="w-full bg-slate-900 rounded-full h-2.5 overflow-hidden border border-slate-800 p-0.5">
                  <div
                    className="bg-gradient-to-r from-purple-600 via-indigo-500 to-emerald-400 h-full rounded-full transition-all duration-500 shadow-sm"
                    style={{
                      width: `${Math.min(
                        target.progress_percent !== undefined
                          ? target.progress_percent
                          : (target.progress_percentage || Math.round(((target.current_minutes || 0) / Math.max(target.required_minutes || 60, 1)) * 100)),
                        100
                      )}%`,
                    }}
                  />
                </div>
              </div>

              <div className="flex items-center justify-between text-xs text-slate-400 pt-2.5 border-t border-slate-800/80">
                <div className="flex items-center space-x-1.5 min-w-0">
                  <Gift className="w-3.5 h-3.5 text-purple-400 shrink-0" />
                  <span className="truncate text-[11px]">{target.campaign_name || 'Active Campaign'}</span>
                </div>
                <div className="flex items-center space-x-1.5 text-[11px] text-emerald-400 font-semibold shrink-0">
                  <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
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

