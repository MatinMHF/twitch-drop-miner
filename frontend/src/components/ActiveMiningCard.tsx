import React, { useState } from 'react';
import { useWebSocket } from '../context/WebSocketContext';
import { api } from '../services/api';
import {
  Play,
  Pause,
  RotateCw,
  Square,
  Radio,
  Clock,
  Eye,
  Gift,
  ExternalLink,
  Layers,
  Sparkles,
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
    : (status?.active_channel ? [{
        game_id: status.active_game_id || '',
        game_name: status.active_game_name || 'Watchlisted Game',
        campaign_id: status.active_campaign_id || '',
        campaign_name: status.active_campaign_name || 'Drop Campaign',
        drop_id: status.current_drop_id || '',
        drop_name: status.current_drop_name || 'Drop Reward',
        required_minutes: status.current_drop_required_minutes || 0,
        current_minutes: status.current_drop_minutes_watched || 0,
        progress_percent: status.current_drop_progress_percent || 0,
        channel: status.active_channel,
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
              {isMining && targets.length > 1 && (
                <span className="flex items-center gap-1 text-xs font-semibold px-2.5 py-0.5 rounded-full bg-purple-500/20 text-purple-300 border border-purple-500/30">
                  <Layers className="w-3 h-3" />
                  <span>{targets.length} Concurrent Streams</span>
                </span>
              )}
            </h2>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            {isMining
              ? targets.length > 1
                ? `Mining ${targets.length} games simultaneously across active drop campaigns.`
                : `Currently mining drops for ${targets[0]?.game_name || status?.active_game_name || 'watchlisted game'}`
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
              className="flex items-center space-x-1.5 px-3.5 py-2 rounded-xl text-xs font-semibold bg-amber-500/10 hover:bg-amber-500/20 text-amber-300 border border-amber-500/30 transition-all disabled:opacity-50"
            >
              <Pause className="w-3.5 h-3.5" />
              <span>Pause</span>
            </button>
          ) : isPaused ? (
            <button
              onClick={() => handleControl('resume')}
              disabled={isActing}
              className="flex items-center space-x-1.5 px-3.5 py-2 rounded-xl text-xs font-semibold bg-emerald-500/10 hover:bg-emerald-500/20 text-emerald-300 border border-emerald-500/30 transition-all disabled:opacity-50"
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
              className="flex items-center space-x-1.5 px-3.5 py-2 rounded-xl text-xs font-semibold bg-rose-500/10 hover:bg-rose-500/20 text-rose-300 border border-rose-500/30 transition-all disabled:opacity-50"
            >
              <Square className="w-3.5 h-3.5" />
              <span>Stop</span>
            </button>
          )}
        </div>
      </div>

      {/* Main Mining Grid Body */}
      {isMining && targets.length > 0 ? (
        <div className={`mt-6 grid gap-6 ${targets.length === 1 ? 'grid-cols-1' : 'grid-cols-1 xl:grid-cols-2'}`}>
          {targets.map((target, idx) => {
            const ch = target.channel;
            const progressPct = target.progress_percent || 0;
            const minutesLeft = Math.max(0, (target.required_minutes || 0) - (target.current_minutes || 0));

            return (
              <div
                key={target.campaign_id || idx}
                className="bg-slate-950/70 border border-slate-800/90 rounded-xl p-5 relative overflow-hidden transition-all hover:border-slate-700"
              >
                {/* Top Badge Row */}
                <div className="flex items-center justify-between gap-2 mb-3">
                  <span className="text-xs font-bold text-purple-400 uppercase tracking-wider flex items-center gap-1.5">
                    <Sparkles className="w-3.5 h-3.5 text-purple-400" />
                    <span>{target.game_name}</span>
                  </span>
                  <span className="flex items-center space-x-1 text-[11px] text-rose-400 bg-rose-950/40 px-2 py-0.5 rounded-full border border-rose-500/20 font-medium">
                    <Radio className="w-3 h-3 animate-pulse" />
                    <span>LIVE</span>
                  </span>
                </div>

                {/* Streamer Header */}
                <div className="flex items-start justify-between gap-4 mb-4">
                  <div className="min-w-0">
                    <div className="flex items-center space-x-2">
                      <h3 className="font-bold text-base text-white truncate">
                        @{ch?.channel_display_name || ch?.channel_login || 'Channel'}
                      </h3>
                      {ch?.channel_login && (
                        <a
                          href={`https://twitch.tv/${ch.channel_login}`}
                          target="_blank"
                          rel="noreferrer"
                          className="text-slate-400 hover:text-purple-400 transition-colors"
                          title="Open Twitch Channel"
                        >
                          <ExternalLink className="w-3.5 h-3.5" />
                        </a>
                      )}
                    </div>
                    <p className="text-xs text-slate-400 mt-0.5 line-clamp-1">
                      {ch?.title || 'Drops Enabled Stream'}
                    </p>
                  </div>

                  <div className="text-right shrink-0">
                    <span className="flex items-center justify-end space-x-1 text-xs text-slate-400">
                      <Eye className="w-3.5 h-3.5 text-slate-500" />
                      <span>{ch?.viewers_count?.toLocaleString() || '0'}</span>
                    </span>
                  </div>
                </div>

                {/* Drop Info & Progress */}
                <div className="bg-slate-900/90 rounded-lg p-3.5 border border-slate-800/80">
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center space-x-2 min-w-0">
                      <Gift className="w-4 h-4 text-purple-400 shrink-0" />
                      <div className="min-w-0">
                        <h4 className="font-semibold text-white text-xs truncate">
                          {target.drop_name || 'Drop Reward'}
                        </h4>
                        <p className="text-[11px] text-slate-400 truncate">
                          {target.campaign_name || 'Campaign'}
                        </p>
                      </div>
                    </div>
                    <div className="text-right shrink-0">
                      <span className="text-lg font-black text-purple-400">{progressPct}%</span>
                      <p className="text-[10px] text-slate-500">
                        {target.current_minutes} / {target.required_minutes}m
                      </p>
                    </div>
                  </div>

                  {/* Progress Bar */}
                  <div className="w-full bg-slate-800/80 h-2.5 rounded-full overflow-hidden p-0.5 border border-slate-700/50 my-2">
                    <div
                      className="bg-gradient-to-r from-purple-600 via-indigo-500 to-purple-400 h-full rounded-full transition-all duration-500 shadow-sm shadow-purple-500/30"
                      style={{ width: `${progressPct}%` }}
                    />
                  </div>

                  {/* Progress Footer */}
                  <div className="flex items-center justify-between text-[11px] text-slate-400 mt-2">
                    <span className="flex items-center space-x-1">
                      <Clock className="w-3 h-3 text-slate-500" />
                      <span>
                        {minutesLeft > 0
                          ? `Est. ${minutesLeft}m left`
                          : 'Reward ready for auto-claim!'}
                      </span>
                    </span>
                    <span className="text-emerald-400 font-medium">Auto-Claim Active</span>
                  </div>
                </div>
              </div>
            );
          })}
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
            Concurrent multi-stream engine runs 24/7 in the background with zero video bandwidth.
          </p>
        </div>
      )}
    </div>
  );
};
