import React, { useState, useEffect } from 'react';
import { api } from '../services/api';
import { AppSettings } from '../services/types';
import {
  X,
  Sliders,
  Save,
  RotateCcw,
  CheckCircle2,
  Database,
  Hash,
  Activity,
  Globe,
  Loader2,
} from 'lucide-react';

interface SettingsModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const SettingsModal: React.FC<SettingsModalProps> = ({ isOpen, onClose }) => {
  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isSaving, setIsSaving] = useState(false);
  const [savedSuccess, setSavedSuccess] = useState(false);
  const [hashesJson, setHashesJson] = useState('');

  useEffect(() => {
    if (!isOpen) return;

    const fetchSettings = async () => {
      try {
        setIsLoading(true);
        const data = await api.getSettings();
        setSettings(data);
        setHashesJson(JSON.stringify(data.custom_query_hashes || {}, null, 2));
      } catch (err) {
        console.error('Failed to load settings', err);
      } finally {
        setIsLoading(false);
      }
    };
    fetchSettings();
  }, [isOpen]);

  const handleSave = async () => {
    if (!settings) return;
    try {
      setIsSaving(true);
      let parsedHashes: Record<string, string> | undefined;
      if (hashesJson.trim()) {
        try {
          parsedHashes = JSON.parse(hashesJson);
        } catch {
          alert('Invalid JSON in Persisted Query Hashes field.');
          return;
        }
      }

      await api.updateSettings({
        poll_interval_minutes: settings.poll_interval_minutes,
        watch_heartbeat_seconds: settings.watch_heartbeat_seconds,
        auto_claim_drops: settings.auto_claim_drops,
        auto_failover_streamers: settings.auto_failover_streamers,
        timezone: settings.timezone,
        custom_spade_url: settings.custom_spade_url,
        custom_query_hashes: parsedHashes,
      });

      setSavedSuccess(true);
      setTimeout(() => setSavedSuccess(false), 2500);
    } catch (err: any) {
      alert(`Failed to save settings: ${err.message}`);
    } finally {
      setIsSaving(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in">
      <div className="bg-slate-900 border border-slate-800 w-full max-w-2xl rounded-2xl shadow-2xl overflow-hidden p-6 relative max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between pb-4 border-b border-slate-800">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-purple-600/20 text-purple-400 border border-purple-500/30 flex items-center justify-center">
              <Sliders className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-lg font-bold text-white">System Settings & Hashes</h3>
              <p className="text-xs text-slate-400">Configure engine timing and persisted query registry</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Form Body */}
        <div className="mt-4 overflow-y-auto space-y-5 pr-1 flex-1">
          {isLoading || !settings ? (
            <div className="py-12 text-center text-slate-500 text-xs flex items-center justify-center space-x-2">
              <Loader2 className="w-4 h-4 animate-spin text-purple-400" />
              <span>Loading configuration...</span>
            </div>
          ) : (
            <>
              {/* General Engine Options */}
              <div className="space-y-4">
                <h4 className="text-xs font-bold text-purple-400 uppercase tracking-wider flex items-center space-x-1.5">
                  <Activity className="w-4 h-4" />
                  <span>Mining Schedule & Failover</span>
                </h4>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs font-semibold text-slate-300 mb-1">
                      Campaign Polling Interval (minutes)
                    </label>
                    <input
                      type="number"
                      min={5}
                      max={1440}
                      value={settings.poll_interval_minutes}
                      onChange={(e) =>
                        setSettings({
                          ...settings,
                          poll_interval_minutes: parseInt(e.target.value) || 30,
                        })
                      }
                      className="w-full px-3 py-2 text-xs rounded-xl bg-slate-950 border border-slate-700 text-white focus:outline-none focus:border-purple-500"
                    />
                    <span className="text-[10px] text-slate-500">Default: 30 minutes</span>
                  </div>

                  <div>
                    <label className="block text-xs font-semibold text-slate-300 mb-1">
                      Watch Heartbeat Interval (seconds)
                    </label>
                    <input
                      type="number"
                      min={30}
                      max={120}
                      value={settings.watch_heartbeat_seconds}
                      onChange={(e) =>
                        setSettings({
                          ...settings,
                          watch_heartbeat_seconds: parseInt(e.target.value) || 60,
                        })
                      }
                      className="w-full px-3 py-2 text-xs rounded-xl bg-slate-950 border border-slate-700 text-white focus:outline-none focus:border-purple-500"
                    />
                    <span className="text-[10px] text-slate-500">Default: 60 seconds</span>
                  </div>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 pt-2">
                  <label className="flex items-center space-x-2.5 p-3 rounded-xl bg-slate-950/60 border border-slate-800 cursor-pointer hover:border-slate-700">
                    <input
                      type="checkbox"
                      checked={settings.auto_claim_drops}
                      onChange={(e) =>
                        setSettings({ ...settings, auto_claim_drops: e.target.checked })
                      }
                      className="rounded text-purple-600 focus:ring-purple-500 bg-slate-900 border-slate-700"
                    />
                    <span className="text-xs text-slate-200 font-medium">Auto-Claim Drops</span>
                  </label>

                  <label className="flex items-center space-x-2.5 p-3 rounded-xl bg-slate-950/60 border border-slate-800 cursor-pointer hover:border-slate-700">
                    <input
                      type="checkbox"
                      checked={settings.auto_failover_streamers}
                      onChange={(e) =>
                        setSettings({ ...settings, auto_failover_streamers: e.target.checked })
                      }
                      className="rounded text-purple-600 focus:ring-purple-500 bg-slate-900 border-slate-700"
                    />
                    <span className="text-xs text-slate-200 font-medium">
                      Auto-Failover on Offline Stream
                    </span>
                  </label>
                </div>
              </div>

              {/* Spade & Hashes Config */}
              <div className="space-y-4 pt-3 border-t border-slate-800">
                <h4 className="text-xs font-bold text-purple-400 uppercase tracking-wider flex items-center space-x-1.5">
                  <Hash className="w-4 h-4" />
                  <span>Twitch GQL Query Hashes & Spade Tracker</span>
                </h4>

                <div>
                  <label className="block text-xs font-semibold text-slate-300 mb-1">
                    Spade Telemetry URL
                  </label>
                  <input
                    type="text"
                    value={settings.custom_spade_url || ''}
                    onChange={(e) => setSettings({ ...settings, custom_spade_url: e.target.value })}
                    placeholder="https://spade.twitch.tv/batched"
                    className="w-full px-3 py-2 text-xs font-mono rounded-xl bg-slate-950 border border-slate-700 text-white focus:outline-none focus:border-purple-500"
                  />
                </div>

                <div>
                  <div className="flex items-center justify-between mb-1">
                    <label className="block text-xs font-semibold text-slate-300">
                      Persisted Query Hashes (JSON)
                    </label>
                    <span className="text-[10px] text-purple-400">
                      Edit here when Twitch rotates hashes
                    </span>
                  </div>
                  <textarea
                    rows={7}
                    value={hashesJson}
                    onChange={(e) => setHashesJson(e.target.value)}
                    className="w-full p-3 text-xs font-mono rounded-xl bg-slate-950 border border-slate-700 text-slate-300 focus:outline-none focus:border-purple-500"
                  />
                </div>
              </div>
            </>
          )}
        </div>

        {/* Footer */}
        <div className="pt-4 mt-2 border-t border-slate-800 flex items-center justify-between">
          <div>
            {savedSuccess && (
              <span className="flex items-center space-x-1 text-xs text-emerald-400 font-medium">
                <CheckCircle2 className="w-4 h-4" />
                <span>Settings saved successfully!</span>
              </span>
            )}
          </div>
          <div className="flex items-center space-x-2">
            <button
              onClick={onClose}
              className="px-4 py-2 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-300 transition-colors"
            >
              Cancel
            </button>
            <button
              onClick={handleSave}
              disabled={isSaving}
              className="flex items-center space-x-1.5 px-4 py-2 rounded-xl text-xs font-bold bg-purple-600 hover:bg-purple-500 text-white shadow-md shadow-purple-600/30 transition-all disabled:opacity-50"
            >
              {isSaving ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  <span>Saving...</span>
                </>
              ) : (
                <>
                  <Save className="w-3.5 h-3.5" />
                  <span>Save Changes</span>
                </>
              )}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
