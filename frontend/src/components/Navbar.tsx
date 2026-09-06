import React from 'react';
import { useAuth } from '../context/AuthContext';
import { useWebSocket } from '../context/WebSocketContext';
import { ThemeToggle } from './ThemeToggle';
import {
  Tv,
  LogOut,
  Radio,
  Sliders,
  CheckCircle2,
  Sparkles,
} from 'lucide-react';

interface NavbarProps {
  onOpenSettings: () => void;
  onOpenTwitchAuth: () => void;
}

export const Navbar: React.FC<NavbarProps> = ({ onOpenSettings, onOpenTwitchAuth }) => {
  const { user, twitchAccount, logout } = useAuth();
  const { isConnected } = useWebSocket();

  return (
    <header className="sticky top-0 z-30 border-b border-slate-800/80 bg-slate-900/90 backdrop-blur-md">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        {/* Brand */}
        <div className="flex items-center space-x-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-600 to-indigo-700 flex items-center justify-center shadow-lg shadow-purple-500/20">
            <Tv className="w-5 h-5 text-white" />
          </div>
          <div>
            <div className="flex items-center space-x-2">
              <span className="font-bold text-lg tracking-tight bg-gradient-to-r from-white via-slate-100 to-slate-400 bg-clip-text text-transparent">
                Twitch Drop Miner
              </span>
              <span className="text-[10px] px-2 py-0.5 rounded-full font-medium bg-purple-500/10 text-purple-600 dark:text-purple-400 border border-purple-500/20">
                v3.2.0
              </span>
            </div>
            <p className="text-xs text-slate-400 hidden sm:block">Headless Automated Reward Claimer</p>
          </div>
        </div>

        {/* Status Indicators & Actions */}
        <div className="flex items-center space-x-2 sm:space-x-4">
          {/* Live WS Pill */}
          <div
            className={`hidden sm:flex items-center space-x-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${
              isConnected
                ? 'bg-emerald-950/40 text-emerald-400 border-emerald-500/30'
                : 'bg-rose-950/40 text-rose-400 border-rose-500/30'
            }`}
          >
            <Radio className={`w-3.5 h-3.5 ${isConnected ? 'animate-pulse text-emerald-400' : 'text-rose-400'}`} />
            <span>{isConnected ? 'Telemetry Live' : 'Connecting...'}</span>
          </div>

          {/* Twitch Account Pill / Connect Button */}
          {twitchAccount?.connected ? (
            <button
              onClick={onOpenTwitchAuth}
              className="flex items-center space-x-2 px-3 py-1.5 rounded-lg text-xs font-medium bg-purple-950/50 hover:bg-purple-900/50 text-purple-300 border border-purple-500/30 transition-colors"
            >
              <CheckCircle2 className="w-4 h-4 text-purple-400" />
              <span>@{twitchAccount.twitch_username}</span>
            </button>
          ) : (
            <button
              onClick={onOpenTwitchAuth}
              className="flex items-center space-x-1.5 px-3 py-1.5 rounded-lg text-xs font-semibold bg-purple-600 hover:bg-purple-500 text-white shadow-md shadow-purple-600/30 transition-all hover:scale-[1.02]"
            >
              <Sparkles className="w-3.5 h-3.5" />
              <span>Connect Twitch</span>
            </button>
          )}

          {/* Settings Button */}
          <button
            onClick={onOpenSettings}
            className="p-2 rounded-lg bg-slate-800/80 hover:bg-slate-700 text-slate-300 hover:text-white border border-slate-700/50 transition-colors"
            title="System Settings & Hashes"
          >
            <Sliders className="w-5 h-5" />
          </button>

          {/* Theme Toggle */}
          <ThemeToggle />

          {/* Logout Button */}
          {user?.is_active && (
            <button
              onClick={logout}
              className="p-2 rounded-lg bg-slate-800/80 hover:bg-rose-950/60 text-slate-300 hover:text-rose-400 border border-slate-700/50 hover:border-rose-500/30 transition-colors"
              title="Log Out"
            >
              <LogOut className="w-5 h-5" />
            </button>
          )}
        </div>
      </div>
    </header>
  );
};
