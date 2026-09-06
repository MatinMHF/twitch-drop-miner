import React, { useState, useEffect, useRef } from 'react';
import { api } from '../services/api';
import { useAuth } from '../context/AuthContext';
import { DeviceCodeInit, DeviceCodeStatus } from '../services/types';
import {
  X,
  Tv,
  ExternalLink,
  Copy,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Trash2,
  KeyRound,
  ShieldCheck,
} from 'lucide-react';

interface TwitchDeviceAuthModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const TwitchDeviceAuthModal: React.FC<TwitchDeviceAuthModalProps> = ({
  isOpen,
  onClose,
}) => {
  const { twitchAccount, refreshTwitchAccount } = useAuth();
  const [deviceFlow, setDeviceFlow] = useState<DeviceCodeInit | null>(null);
  const [statusMsg, setStatusMsg] = useState<string>('');
  const [isCopied, setIsCopied] = useState(false);
  const [isInitializing, setIsInitializing] = useState(false);
  const [isDisconnecting, setIsDisconnecting] = useState(false);
  const pollIntervalRef = useRef<number | null>(null);

  // Stop polling on unmount or close
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

      // Start polling status
      pollIntervalRef.current = window.setInterval(async () => {
        try {
          const statusRes = await api.checkDeviceCodeStatus(init.device_code);
          setStatusMsg(statusRes.message);

          if (statusRes.status === 'success') {
            if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
            await refreshTwitchAccount();
            setTimeout(() => {
              setDeviceFlow(null);
            }, 1500);
          } else if (statusRes.status === 'expired' || statusRes.status === 'failed') {
            if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
          }
        } catch (err: any) {
          console.error('Polling error', err);
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

  const handleDisconnect = async () => {
    if (!confirm('Are you sure you want to disconnect your Twitch account?')) return;
    try {
      setIsDisconnecting(true);
      await api.disconnectTwitch();
      await refreshTwitchAccount();
    } catch (err: any) {
      alert(`Disconnect failed: ${err.message}`);
    } finally {
      setIsDisconnecting(false);
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
            <h3 className="text-lg font-bold text-white">Twitch Authentication</h3>
            <p className="text-xs text-slate-400">OAuth 2.0 Device Flow (No password required)</p>
          </div>
        </div>

        {/* Modal Body */}
        <div className="mt-5">
          {twitchAccount?.connected ? (
            <div className="space-y-4">
              <div className="p-4 bg-emerald-950/30 border border-emerald-500/30 rounded-xl flex items-center justify-between">
                <div className="flex items-center space-x-3">
                  <CheckCircle2 className="w-6 h-6 text-emerald-400" />
                  <div>
                    <h4 className="font-bold text-white text-sm">
                      Connected as @{twitchAccount.twitch_username}
                    </h4>
                    <p className="text-xs text-slate-400">
                      Tokens are AES-256 encrypted at rest.
                    </p>
                  </div>
                </div>
              </div>

              <div className="p-4 bg-slate-950/60 border border-slate-800 rounded-xl text-xs text-slate-400 space-y-2">
                <div className="flex items-center space-x-2 text-slate-300 font-semibold">
                  <ShieldCheck className="w-4 h-4 text-purple-400" />
                  <span>Security & Permissions</span>
                </div>
                <p>
                  Your credentials are encrypted using AES-256-GCM and stored only in your local
                  database volume. No audio or video streams are downloaded.
                </p>
              </div>

              <div className="pt-2 flex justify-between">
                <button
                  onClick={handleStartDeviceFlow}
                  className="px-4 py-2 rounded-xl text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-white border border-slate-700 transition-colors"
                >
                  Switch Account
                </button>
                <button
                  onClick={handleDisconnect}
                  disabled={isDisconnecting}
                  className="flex items-center space-x-1.5 px-4 py-2 rounded-xl text-xs font-semibold bg-rose-950/40 hover:bg-rose-900/40 text-rose-300 border border-rose-500/30 transition-colors disabled:opacity-50"
                >
                  <Trash2 className="w-4 h-4" />
                  <span>Disconnect</span>
                </button>
              </div>
            </div>
          ) : deviceFlow ? (
            <div className="space-y-5 text-center">
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

              <div className="flex justify-center">
                <a
                  href={deviceFlow.verification_uri}
                  target="_blank"
                  rel="noreferrer"
                  className="inline-flex items-center space-x-2 px-5 py-2.5 rounded-xl text-xs font-bold bg-purple-600 hover:bg-purple-500 text-white shadow-lg shadow-purple-600/30 transition-all hover:scale-[1.02]"
                >
                  <span>Authorize on Twitch</span>
                  <ExternalLink className="w-4 h-4" />
                </a>
              </div>

              {/* Polling Spinner */}
              <div className="pt-2 flex items-center justify-center space-x-2 text-xs text-slate-400">
                <Loader2 className="w-4 h-4 animate-spin text-purple-400" />
                <span>{statusMsg || 'Waiting for confirmation...'}</span>
              </div>
            </div>
          ) : (
            <div className="space-y-4">
              <p className="text-xs text-slate-300 leading-relaxed">
                Connect using the official Twitch OAuth Device Code Grant. You will be provided an
                activation code to enter on <strong className="text-purple-400">twitch.tv/activate</strong>.
              </p>

              <div className="p-4 bg-slate-950/60 border border-slate-800 rounded-xl space-y-2 text-xs text-slate-400">
                <div className="flex items-center space-x-2 text-slate-300 font-semibold">
                  <KeyRound className="w-4 h-4 text-purple-400" />
                  <span>Why Device Flow?</span>
                </div>
                <ul className="list-disc list-inside space-y-1 text-slate-400">
                  <li>No Twitch passwords or 2FA codes are ever entered here.</li>
                  <li>No brittle browser automation (Puppeteer/Selenium) required.</li>
                  <li>Tokens are automatically encrypted at rest using AES-256-GCM.</li>
                </ul>
              </div>

              <div className="pt-2">
                <button
                  onClick={handleStartDeviceFlow}
                  disabled={isInitializing}
                  className="w-full py-2.5 rounded-xl text-xs font-bold bg-purple-600 hover:bg-purple-500 text-white shadow-lg shadow-purple-600/30 transition-all flex items-center justify-center space-x-2 disabled:opacity-50"
                >
                  {isInitializing ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span>Initiating Device Flow...</span>
                    </>
                  ) : (
                    <span>Generate Activation Code</span>
                  )}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
