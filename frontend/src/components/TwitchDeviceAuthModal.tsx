import React, { useState, useEffect, useRef } from 'react';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { DeviceCodeInit } from '../services/types';
import {
  X,
  Tv,
  ExternalLink,
  Copy,
  CheckCircle2,
  Loader2,
  Trash2,
  ShieldCheck,
  UserPlus,
  Users,
} from 'lucide-react';

interface TwitchDeviceAuthModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const TwitchDeviceAuthModal: React.FC<TwitchDeviceAuthModalProps> = ({
  isOpen,
  onClose,
}) => {
  const { twitchAccount, twitchAccounts, refreshTwitchAccount } = useAuth();
  const [deviceFlow, setDeviceFlow] = useState<DeviceCodeInit | null>(null);
  const [statusMsg, setStatusMsg] = useState<string>('');
  const [isCopied, setIsCopied] = useState(false);
  const [isInitializing, setIsInitializing] = useState(false);
  const [disconnectingId, setDisconnectingId] = useState<string | null>(null);
  const pollIntervalRef = useRef<number | null>(null);

  // Combine accounts so even if twitchAccounts array was empty but twitchAccount exists, it shows
  const allAccounts = twitchAccounts.length > 0
    ? twitchAccounts
    : (twitchAccount?.connected ? [twitchAccount] : []);

  useEffect(() => {
    return () => {
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    };
  }, []);

  const handleStartDeviceFlow = async () => {
    try {
      setIsInitializing(true);
      setStatusMsg('Contacting Twitch OAuth server...');
      const init = await api.initDeviceCode();
      setDeviceFlow(init);
      setStatusMsg('Please authorize the miner on Twitch.');

      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);

      pollIntervalRef.current = window.setInterval(async () => {
        try {
          const statusRes = await api.checkDeviceCodeStatus(init.device_code);
          setStatusMsg(statusRes.message);

          if (statusRes.status === 'success') {
            if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
            await refreshTwitchAccount();
            setTimeout(() => {
              setDeviceFlow(null);
            }, 2500);
          } else if (statusRes.status === 'expired' || statusRes.status === 'failed') {
            if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
          }
        } catch {
          // ignore poll error
        }
      }, (init.interval || 5) * 1000);
    } catch (err: any) {
      setStatusMsg(`Error: ${err.message}`);
    } finally {
      setIsInitializing(false);
    }
  };

  const handleCopyCode = () => {
    if (deviceFlow?.user_code) {
      navigator.clipboard.writeText(deviceFlow.user_code);
      setIsCopied(true);
      setTimeout(() => setIsCopied(false), 2000);
    }
  };

  const handleDisconnect = async (accountId?: string, username?: string) => {
    const targetMsg = username ? `@${username}` : 'all connected accounts';
    if (!confirm(`Are you sure you want to disconnect ${targetMsg}?`)) return;
    try {
      setDisconnectingId(accountId || 'all');
      await api.disconnectTwitch(accountId);
      await refreshTwitchAccount();
    } catch (err: any) {
      alert(`Disconnect failed: ${err.message}`);
    } finally {
      setDisconnectingId(null);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm animate-in fade-in">
      <div className="bg-slate-900 border border-slate-800 w-full max-w-lg rounded-2xl shadow-2xl overflow-hidden p-6 relative">
        <button
          onClick={onClose}
          className="absolute top-5 right-5 p-1 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
        >
          <X className="w-5 h-5" />
        </button>

        <div className="flex items-center space-x-3 pb-4 border-b border-slate-800">
          <div className="w-10 h-10 rounded-xl bg-purple-600/20 text-purple-400 border border-purple-500/30 flex items-center justify-center">
            <Tv className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-white">Twitch Multi-Account Authentication</h3>
            <p className="text-xs text-slate-400">Connect multiple accounts to claim drops concurrently</p>
          </div>
        </div>

        {/* Modal Body */}
        <div className="mt-5 space-y-4">
          {/* Active Connected Accounts List */}
          {allAccounts.length > 0 && (
            <div className="space-y-2">
              <div className="flex items-center justify-between text-xs font-semibold text-slate-300">
                <span className="flex items-center space-x-1.5">
                  <Users className="w-4 h-4 text-purple-400" />
                  <span>Connected Accounts ({allAccounts.length})</span>
                </span>
              </div>
              <div className="space-y-2 max-h-48 overflow-y-auto pr-1">
                {allAccounts.map((acc) => (
                  <div
                    key={acc.account_id || acc.twitch_user_id || acc.twitch_username}
                    className="p-3 bg-slate-950/70 border border-slate-800/80 rounded-xl flex items-center justify-between"
                  >
                    <div className="flex items-center space-x-2.5">
                      <div className="w-7 h-7 rounded-full bg-purple-600/20 text-purple-400 border border-purple-500/30 flex items-center justify-center font-bold text-xs uppercase">
                        {acc.twitch_username?.[0] || 'T'}
                      </div>
                      <div>
                        <h4 className="font-bold text-white text-xs">@{acc.twitch_username}</h4>
                        <span className="text-[10px] text-emerald-400 flex items-center space-x-1">
                          <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                          <span>Mining Active</span>
                        </span>
                      </div>
                    </div>

                    <button
                      onClick={() => handleDisconnect(acc.account_id, acc.twitch_username)}
                      disabled={disconnectingId === (acc.account_id || 'all')}
                      className="p-1.5 rounded-lg text-slate-400 hover:text-rose-400 hover:bg-rose-950/30 transition-colors disabled:opacity-50"
                      title="Disconnect this account"
                    >
                      {disconnectingId === (acc.account_id || 'all') ? (
                        <Loader2 className="w-4 h-4 animate-spin text-rose-400" />
                      ) : (
                        <Trash2 className="w-4 h-4" />
                      )}
                    </button>
                  </div>
                ))}
              </div>
            </div>
          )}

          {deviceFlow ? (
            <div className="space-y-4 text-center p-4 bg-slate-950/60 border border-slate-800 rounded-xl">
              <p className="text-xs text-slate-300">
                1. Copy your activation code and open the Twitch activation page:
              </p>

              {/* Big Code Card */}
              <div className="bg-slate-950 p-4 rounded-xl border border-purple-500/40 flex items-center justify-between shadow-inner">
                <span className="font-mono text-2xl font-black tracking-widest text-purple-300 mx-auto">
                  {deviceFlow.user_code}
                </span>
                <button
                  onClick={handleCopyCode}
                  className="p-2 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white transition-colors"
                  title="Copy Code"
                >
                  {isCopied ? (
                    <CheckCircle2 className="w-5 h-5 text-emerald-400" />
                  ) : (
                    <Copy className="w-5 h-5" />
                  )}
                </button>
              </div>

              {/* Step 2: Open link */}
              <a
                href={deviceFlow.verification_uri || 'https://www.twitch.tv/activate'}
                target="_blank"
                rel="noopener noreferrer"
                className="w-full py-2.5 rounded-xl text-xs font-bold bg-purple-600 hover:bg-purple-500 text-white shadow-lg shadow-purple-600/30 transition-all flex items-center justify-center space-x-2"
              >
                <span>Open twitch.tv/activate</span>
                <ExternalLink className="w-4 h-4" />
              </a>

              {/* Polling Spinner */}
              <div className="pt-2 flex items-center justify-center space-x-2 text-xs text-slate-400">
                <Loader2 className="w-4 h-4 animate-spin text-purple-400" />
                <span>{statusMsg || 'Waiting for confirmation...'}</span>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              <button
                onClick={handleStartDeviceFlow}
                disabled={isInitializing}
                className="w-full py-2.5 rounded-xl text-xs font-bold bg-purple-600 hover:bg-purple-500 text-white shadow-lg shadow-purple-600/30 transition-all flex items-center justify-center space-x-2 disabled:opacity-50"
              >
                {isInitializing ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    <span>Contacting Twitch...</span>
                  </>
                ) : (
                  <>
                    <UserPlus className="w-4 h-4" />
                    <span>{allAccounts.length > 0 ? 'Add Another Account' : 'Connect Twitch Account'}</span>
                  </>
                )}
              </button>
            </div>
          )}

          <div className="p-3 bg-slate-950/60 border border-slate-800/80 rounded-xl text-[11px] text-slate-400 space-y-1.5">
            <div className="flex items-center space-x-2 text-slate-300 font-semibold">
              <ShieldCheck className="w-3.5 h-3.5 text-purple-400" />
              <span>Multi-Account Safety</span>
            </div>
            <p>
              Each account runs an isolated session with independent stream watching telemetry and token encryption.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
};
