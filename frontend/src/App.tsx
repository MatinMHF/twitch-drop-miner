import React, { useState } from 'react';
import { useAuth } from './context/AuthContext';
import { Navbar } from './components/Navbar';
import { QuickStats } from './components/QuickStats';
import { ActiveMiningCard } from './components/ActiveMiningCard';
import { WatchlistManager } from './components/WatchlistManager';
import { DropCampaignList } from './components/DropCampaignList';
import { DropHistoryList } from './components/DropHistoryList';
import { LiveLogsViewer } from './components/LiveLogsViewer';
import { TwitchDeviceAuthModal } from './components/TwitchDeviceAuthModal';
import { SettingsModal } from './components/SettingsModal';
import {
  Tv,
  Lock,
  UserCheck,
  Loader2,
  ShieldCheck,
  Sparkles,
  ArrowRight,
} from 'lucide-react';

export const App: React.FC = () => {
  const { user, isLoading, login, setupAdmin } = useAuth();
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isTwitchAuthOpen, setIsTwitchAuthOpen] = useState(false);
  const [claimedCount, setClaimedCount] = useState(0);
  const [watchlistCount, setWatchlistCount] = useState(0);

  // Form states for login/setup
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [authError, setAuthError] = useState('');

  if (isLoading) {
    return (
      <div className="min-h-screen bg-slate-950 flex flex-col items-center justify-center space-y-4">
        <div className="w-12 h-12 rounded-2xl bg-purple-600/20 text-purple-400 border border-purple-500/30 flex items-center justify-center animate-bounce">
          <Tv className="w-6 h-6" />
        </div>
        <div className="flex items-center space-x-2 text-xs text-slate-400">
          <Loader2 className="w-4 h-4 animate-spin text-purple-400" />
          <span>Starting Twitch Drop Miner...</span>
        </div>
      </div>
    );
  }

  // First-time setup wizard
  if (!user?.is_setup_completed) {
    const handleSetup = async (e: React.FormEvent) => {
      e.preventDefault();
      try {
        setIsSubmitting(true);
        setAuthError('');
        await setupAdmin({ username, password });
      } catch (err: any) {
        setAuthError(err.message || 'Setup failed');
      } finally {
        setIsSubmitting(false);
      }
    };

    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4">
        <div className="w-full max-w-md bg-slate-900 border border-slate-800 rounded-3xl p-8 shadow-2xl relative overflow-hidden">
          <div className="absolute top-0 right-0 -mr-16 -mt-16 w-56 h-56 rounded-full bg-purple-600/20 blur-3xl pointer-events-none" />

          <div className="text-center">
            <div className="w-12 h-12 mx-auto rounded-2xl bg-purple-600/20 text-purple-400 border border-purple-500/30 flex items-center justify-center shadow-lg">
              <Sparkles className="w-6 h-6" />
            </div>
            <h1 className="text-2xl font-black text-white mt-4 tracking-tight">Initial Setup</h1>
            <p className="text-xs text-slate-400 mt-1">
              Create an administrator account to secure your self-hosted web service.
            </p>
          </div>

          <form onSubmit={handleSetup} className="mt-6 space-y-4">
            {authError && (
              <div className="p-3 bg-rose-950/40 border border-rose-500/30 text-rose-400 rounded-xl text-xs">
                {authError}
              </div>
            )}

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">Admin Username</label>
              <input
                type="text"
                required
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="admin"
                className="w-full px-4 py-2.5 text-xs rounded-xl bg-slate-950 border border-slate-800 text-white placeholder-slate-600 focus:outline-none focus:border-purple-500 focus:ring-1 focus:ring-purple-500"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">Password</label>
              <input
                type="password"
                required
                minLength={8}
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                className="w-full px-4 py-2.5 text-xs rounded-xl bg-slate-950 border border-slate-800 text-white placeholder-slate-600 focus:outline-none focus:border-purple-500 focus:ring-1 focus:ring-purple-500"
              />
              <span className="text-[10px] text-slate-500 mt-0.5 block">Minimum 8 characters (bcrypt hashed)</span>
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full py-3 mt-2 rounded-xl text-xs font-bold bg-purple-600 hover:bg-purple-500 text-white shadow-lg shadow-purple-600/30 transition-all flex items-center justify-center space-x-2 disabled:opacity-50"
            >
              {isSubmitting ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <>
                  <span>Create Admin Account</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>
        </div>
      </div>
    );
  }

  // Login Screen
  if (!user?.is_active) {
    const handleLogin = async (e: React.FormEvent) => {
      e.preventDefault();
      try {
        setIsSubmitting(true);
        setAuthError('');
        await login({ username, password });
      } catch (err: any) {
        setAuthError(err.message || 'Invalid credentials');
      } finally {
        setIsSubmitting(false);
      }
    };

    return (
      <div className="min-h-screen bg-slate-950 flex items-center justify-center p-4">
        <div className="w-full max-w-md bg-slate-900 border border-slate-800 rounded-3xl p-8 shadow-2xl relative overflow-hidden">
          <div className="absolute top-0 right-0 -mr-16 -mt-16 w-56 h-56 rounded-full bg-purple-600/20 blur-3xl pointer-events-none" />

          <div className="text-center">
            <div className="w-12 h-12 mx-auto rounded-2xl bg-purple-600/20 text-purple-400 border border-purple-500/30 flex items-center justify-center shadow-lg">
              <Lock className="w-6 h-6" />
            </div>
            <h1 className="text-2xl font-black text-white mt-4 tracking-tight">Twitch Miner Login</h1>
            <p className="text-xs text-slate-400 mt-1">Authenticate to access mining dashboard</p>
          </div>

          <form onSubmit={handleLogin} className="mt-6 space-y-4">
            {authError && (
              <div className="p-3 bg-rose-950/40 border border-rose-500/30 text-rose-400 rounded-xl text-xs">
                {authError}
              </div>
            )}

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">Username</label>
              <input
                type="text"
                required
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="Username"
                className="w-full px-4 py-2.5 text-xs rounded-xl bg-slate-950 border border-slate-800 text-white placeholder-slate-600 focus:outline-none focus:border-purple-500 focus:ring-1 focus:ring-purple-500"
              />
            </div>

            <div>
              <label className="block text-xs font-semibold text-slate-300 mb-1">Password</label>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••••••"
                className="w-full px-4 py-2.5 text-xs rounded-xl bg-slate-950 border border-slate-800 text-white placeholder-slate-600 focus:outline-none focus:border-purple-500 focus:ring-1 focus:ring-purple-500"
              />
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full py-3 mt-2 rounded-xl text-xs font-bold bg-purple-600 hover:bg-purple-500 text-white shadow-lg shadow-purple-600/30 transition-all flex items-center justify-center space-x-2 disabled:opacity-50"
            >
              {isSubmitting ? (
                <Loader2 className="w-4 h-4 animate-spin" />
              ) : (
                <>
                  <span>Sign In</span>
                  <ArrowRight className="w-4 h-4" />
                </>
              )}
            </button>
          </form>
        </div>
      </div>
    );
  }

  // Authenticated Dashboard
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      <Navbar
        onOpenSettings={() => setIsSettingsOpen(true)}
        onOpenTwitchAuth={() => setIsTwitchAuthOpen(true)}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8 space-y-6">
        {/* Quick Stats Grid */}
        <QuickStats claimedCount={claimedCount} watchlistCount={watchlistCount} />

        {/* Active Mining Hero Card */}
        <ActiveMiningCard />

        {/* 2-Column Responsive Layout */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Left Column: Watchlist & History */}
          <div className="space-y-6">
            <WatchlistManager onWatchlistChanged={() => setWatchlistCount((c) => c + 1)} />
            <DropHistoryList />
          </div>

          {/* Right Column: Campaigns & Live Logs */}
          <div className="space-y-6">
            <DropCampaignList />
            <LiveLogsViewer />
          </div>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-900 bg-slate-950/60 py-6 text-center text-xs text-slate-500">
        <p>Twitch Drop Miner &bull; Self-hosted clean-room automated reward claimer.</p>
      </footer>

      {/* Modals */}
      <TwitchDeviceAuthModal
        isOpen={isTwitchAuthOpen}
        onClose={() => setIsTwitchAuthOpen(false)}
      />
      <SettingsModal
        isOpen={isSettingsOpen}
        onClose={() => setIsSettingsOpen(false)}
      />
    </div>
  );
};
