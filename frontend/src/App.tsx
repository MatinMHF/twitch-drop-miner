import React, { useState } from 'react';
import { useAuth } from './context/AuthContext';
import { Navbar } from './components/Navbar';
import { QuickStats } from './components/QuickStats';
import { ActiveMiningCard } from './components/ActiveMiningCard';
import { WatchlistManager } from './components/WatchlistManager';
import { LiveLogsViewer } from './components/LiveLogsViewer';
import { ChannelsTab } from './components/ChannelsTab';
import { InventoryTab } from './components/InventoryTab';
import { HelpTab } from './components/HelpTab';
import { TwitchDeviceAuthModal } from './components/TwitchDeviceAuthModal';
import { SettingsModal } from './components/SettingsModal';
import {
  Tv,
  Lock,
  Loader2,
  Sparkles,
  ArrowRight,
  Activity,
  Radio,
  Gift,
  ListOrdered,
  HelpCircle,
  Settings,
} from 'lucide-react';

export const App: React.FC = () => {
  const { user, isLoading, login, setupAdmin } = useAuth();
  const [currentTab, setCurrentTab] = useState<'overview' | 'channels' | 'inventory' | 'priority' | 'help'>('overview');
  const [isSettingsOpen, setIsSettingsOpen] = useState(false);
  const [isTwitchAuthOpen, setIsTwitchAuthOpen] = useState(false);
  const [claimedCount] = useState(0);
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

  // Authenticated Dashboard with Tabs
  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      <Navbar
        onOpenSettings={() => setIsSettingsOpen(true)}
        onOpenTwitchAuth={() => setIsTwitchAuthOpen(true)}
      />

      <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 space-y-6">
        {/* Navigation Tabs Bar */}
        <div className="flex items-center justify-between flex-wrap gap-3 pb-2 border-b border-slate-800/80">
          <div className="flex items-center space-x-1.5 overflow-x-auto pb-1 max-w-full">
            <button
              onClick={() => setCurrentTab('overview')}
              className={`flex items-center space-x-2 px-4 py-2.5 rounded-xl text-xs font-bold transition-all shrink-0 ${
                currentTab === 'overview'
                  ? 'bg-purple-600 text-white shadow-lg shadow-purple-600/30'
                  : 'bg-slate-900/60 text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 border border-slate-800/80'
              }`}
            >
              <Activity className="w-4 h-4" />
              <span>Overview</span>
            </button>

            <button
              onClick={() => setCurrentTab('channels')}
              className={`flex items-center space-x-2 px-4 py-2.5 rounded-xl text-xs font-bold transition-all shrink-0 ${
                currentTab === 'channels'
                  ? 'bg-purple-600 text-white shadow-lg shadow-purple-600/30'
                  : 'bg-slate-900/60 text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 border border-slate-800/80'
              }`}
            >
              <Radio className="w-4 h-4" />
              <span>Channels</span>
            </button>

            <button
              onClick={() => setCurrentTab('inventory')}
              className={`flex items-center space-x-2 px-4 py-2.5 rounded-xl text-xs font-bold transition-all shrink-0 ${
                currentTab === 'inventory'
                  ? 'bg-purple-600 text-white shadow-lg shadow-purple-600/30'
                  : 'bg-slate-900/60 text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 border border-slate-800/80'
              }`}
            >
              <Gift className="w-4 h-4" />
              <span>Inventory</span>
            </button>

            <button
              onClick={() => setCurrentTab('priority')}
              className={`flex items-center space-x-2 px-4 py-2.5 rounded-xl text-xs font-bold transition-all shrink-0 ${
                currentTab === 'priority'
                  ? 'bg-purple-600 text-white shadow-lg shadow-purple-600/30'
                  : 'bg-slate-900/60 text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 border border-slate-800/80'
              }`}
            >
              <ListOrdered className="w-4 h-4" />
              <span>Priority List</span>
            </button>

            <button
              onClick={() => setCurrentTab('help')}
              className={`flex items-center space-x-2 px-4 py-2.5 rounded-xl text-xs font-bold transition-all shrink-0 ${
                currentTab === 'help'
                  ? 'bg-purple-600 text-white shadow-lg shadow-purple-600/30'
                  : 'bg-slate-900/60 text-slate-400 hover:text-slate-200 hover:bg-slate-800/60 border border-slate-800/80'
              }`}
            >
              <HelpCircle className="w-4 h-4" />
              <span>Help & Guide</span>
            </button>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={() => setIsSettingsOpen(true)}
              className="flex items-center space-x-1.5 px-3 py-2 rounded-xl text-xs font-semibold bg-slate-900/80 hover:bg-slate-800 text-slate-300 hover:text-white border border-slate-800 transition-all"
            >
              <Settings className="w-3.5 h-3.5" />
              <span className="hidden sm:inline">Settings</span>
            </button>
          </div>
        </div>

        {/* Tab Content Rendering */}
        {currentTab === 'overview' && (
          <div className="space-y-6">
            {/* Quick Stats */}
            <QuickStats claimedCount={claimedCount} watchlistCount={watchlistCount} />

            {/* Active Mining Hero Operations */}
            <ActiveMiningCard />

            {/* Overview Dual Grid: Watchlist & Live Logs */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <WatchlistManager onWatchlistChanged={() => setWatchlistCount((c) => c + 1)} />
              <LiveLogsViewer />
            </div>
          </div>
        )}

        {currentTab === 'channels' && <ChannelsTab />}

        {currentTab === 'inventory' && <InventoryTab />}

        {currentTab === 'priority' && (
          <div className="max-w-4xl mx-auto">
            <WatchlistManager onWatchlistChanged={() => setWatchlistCount((c) => c + 1)} />
          </div>
        )}

        {currentTab === 'help' && <HelpTab />}
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-900 bg-slate-950/60 py-6 text-center text-xs text-slate-500">
        <p>Twitch Drops Miner &bull; Self-hosted clean-room automated reward claimer.</p>
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
