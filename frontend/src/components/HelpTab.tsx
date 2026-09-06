import React from 'react';
import {
  HelpCircle,
  Zap,
  ListOrdered,
  Radio,
  Gift,
  Cpu,
  RefreshCw,
} from 'lucide-react';

export const HelpTab: React.FC = () => {
  return (
    <div className="space-y-6">
      <div className="bg-slate-900/80 backdrop-blur-md border border-slate-800 rounded-2xl p-6 shadow-xl">
        <div className="flex items-center space-x-3 pb-6 border-b border-slate-800/80">
          <div className="w-10 h-10 rounded-xl bg-purple-500/10 text-purple-600 dark:text-purple-400 border border-purple-500/20 flex items-center justify-center">
            <HelpCircle className="w-5 h-5" />
          </div>
          <div>
            <h2 className="text-xl font-bold text-white tracking-tight">Twitch Drops Miner User Guide</h2>
            <p className="text-xs text-slate-400 mt-0.5">
              Everything you need to know about automated 24/7 headless drop mining and claiming.
            </p>
          </div>
        </div>

        <div className="mt-6 grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {/* Card 1: How it Works */}
          <div className="p-5 bg-slate-950/60 border border-slate-800 rounded-xl space-y-3">
            <div className="w-8 h-8 rounded-lg bg-purple-500/10 text-purple-600 dark:text-purple-400 flex items-center justify-center border border-purple-500/20">
              <Zap className="w-4 h-4" />
            </div>
            <h3 className="text-sm font-bold text-white">Automated Drop Mining</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              The miner automatically tracks active drop campaigns for games in your priority watchlist, streams telemetry headlessly without video bandwidth, and progresses your drops 24/7.
            </p>
          </div>

          {/* Card 2: Priority List */}
          <div className="p-5 bg-slate-950/60 border border-slate-800 rounded-xl space-y-3">
            <div className="w-8 h-8 rounded-lg bg-emerald-500/10 text-emerald-600 dark:text-emerald-400 flex items-center justify-center border border-emerald-500/20">
              <ListOrdered className="w-4 h-4" />
            </div>
            <h3 className="text-sm font-bold text-white">Priority Watchlist</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Games higher in your watchlist take precedence. When a campaign finishes or is offline, the miner immediately falls back to the next game in your priority queue.
            </p>
          </div>

          {/* Card 3: Auto Claim */}
          <div className="p-5 bg-slate-950/60 border border-slate-800 rounded-xl space-y-3">
            <div className="w-8 h-8 rounded-lg bg-amber-500/10 text-amber-600 dark:text-amber-400 flex items-center justify-center border border-amber-500/20">
              <Gift className="w-4 h-4" />
            </div>
            <h3 className="text-sm font-bold text-white">Instant Auto-Claiming</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Through the real-time Twitch PubSub WebSocket connection, completed drops are instantly claimed within milliseconds so subsequent chained drops start progressing without delay.
            </p>
          </div>

          {/* Card 4: Channels Discovery */}
          <div className="p-5 bg-slate-950/60 border border-slate-800 rounded-xl space-y-3">
            <div className="w-8 h-8 rounded-lg bg-sky-500/10 text-sky-600 dark:text-sky-400 flex items-center justify-center border border-sky-500/20">
              <Radio className="w-4 h-4" />
            </div>
            <h3 className="text-sm font-bold text-white">Smart Channel Discovery</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              The engine continually inspects Twitch directories and official Drop Highlight tags to find the highest reliability live streamers broadcasting your target game.
            </p>
          </div>

          {/* Card 5: Backup & Restore */}
          <div className="p-5 bg-slate-950/60 border border-slate-800 rounded-xl space-y-3">
            <div className="w-8 h-8 rounded-lg bg-rose-500/10 text-rose-600 dark:text-rose-400 flex items-center justify-center border border-rose-500/20">
              <RefreshCw className="w-4 h-4" />
            </div>
            <h3 className="text-sm font-bold text-white">Backup & Restore</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Export your priority games list to a JSON file at any time. When reinstalling or deploying to a new server, restore your exact games list and ordering with one click.
            </p>
          </div>

          {/* Card 6: Headless Efficiency */}
          <div className="p-5 bg-slate-950/60 border border-slate-800 rounded-xl space-y-3">
            <div className="w-8 h-8 rounded-lg bg-indigo-500/10 text-indigo-600 dark:text-indigo-400 flex items-center justify-center border border-indigo-500/20">
              <Cpu className="w-4 h-4" />
            </div>
            <h3 className="text-sm font-bold text-white">Lightweight Resource Usage</h3>
            <p className="text-xs text-slate-400 leading-relaxed">
              Consumes ~80MB RAM and near zero CPU by avoiding heavy Chromium instances and decoding pure stream telemetry payloads directly.
            </p>
          </div>
        </div>
      </div>

      {/* Status Indicators Reference */}
      <div className="bg-slate-900/80 backdrop-blur-md border border-slate-800 rounded-2xl p-6 shadow-xl">
        <h3 className="text-lg font-bold text-white tracking-tight mb-4">Status & Indicator Reference</h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
          <div className="p-4 bg-slate-950/60 border border-slate-800 rounded-xl flex items-start space-x-3">
            <span className="w-3 h-3 rounded-full bg-emerald-400 animate-ping mt-0.5 shrink-0" />
            <div>
              <span className="font-bold text-emerald-400">MINING</span>
              <p className="text-slate-400 mt-0.5">The engine is actively progressing drops for eligible live campaigns.</p>
            </div>
          </div>

          <div className="p-4 bg-slate-950/60 border border-slate-800 rounded-xl flex items-start space-x-3">
            <span className="w-3 h-3 rounded-full bg-amber-400 mt-0.5 shrink-0" />
            <div>
              <span className="font-bold text-amber-400">PAUSED</span>
              <p className="text-slate-400 mt-0.5">Miner operations are paused. Click Resume in the dashboard to continue.</p>
            </div>
          </div>

          <div className="p-4 bg-slate-950/60 border border-slate-800 rounded-xl flex items-start space-x-3">
            <span className="w-3 h-3 rounded-full bg-slate-500 mt-0.5 shrink-0" />
            <div>
              <span className="font-bold text-slate-300">IDLE</span>
              <p className="text-slate-400 mt-0.5">No active drops available or waiting for next scheduled poll cycle.</p>
            </div>
          </div>

          <div className="p-4 bg-slate-950/60 border border-slate-800 rounded-xl flex items-start space-x-3">
            <span className="w-3 h-3 rounded-full bg-purple-400 mt-0.5 shrink-0" />
            <div>
              <span className="font-bold text-purple-400">PUBSUB WEBSOCKET</span>
              <p className="text-slate-400 mt-0.5">Connected to Twitch real-time events for instant drop notifications.</p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
