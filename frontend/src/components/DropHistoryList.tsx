import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import { ClaimedDrop } from '../services/types';
import { Award, CheckCircle2, Clock, Tv, Loader2 } from 'lucide-react';

export const DropHistoryList: React.FC = () => {
  const [history, setHistory] = useState<ClaimedDrop[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchHistory = async () => {
      try {
        const data = await api.getClaimedDrops(50);
        setHistory(data);
      } catch (err) {
        console.error('Failed to load claimed drops', err);
      } finally {
        setIsLoading(false);
      }
    };
    fetchHistory();
  }, []);

  return (
    <div className="bg-slate-900/80 backdrop-blur-md border border-slate-800 rounded-2xl p-6 shadow-xl">
      <div className="flex items-center justify-between pb-4 border-b border-slate-800/80">
        <div>
          <h2 className="text-xl font-bold text-white tracking-tight flex items-center space-x-2">
            <span>Claimed Rewards</span>
            <span className="text-xs font-normal text-slate-400 bg-slate-800 px-2 py-0.5 rounded-full border border-slate-700">
              {history.length}
            </span>
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Log of drops successfully claimed and added to your Twitch inventory.
          </p>
        </div>
      </div>

      <div className="mt-4 space-y-2.5 max-h-96 overflow-y-auto pr-1">
        {isLoading ? (
          <div className="py-12 text-center text-slate-500 text-xs flex items-center justify-center space-x-2">
            <Loader2 className="w-4 h-4 animate-spin text-purple-400" />
            <span>Loading reward history...</span>
          </div>
        ) : history.length === 0 ? (
          <div className="py-8 text-center text-slate-500 text-xs">
            No drops claimed yet. Keep the miner running to claim rewards automatically.
          </div>
        ) : (
          history.map((item) => (
            <div
              key={item.id}
              className="p-3 bg-slate-950/40 border border-slate-800/80 rounded-xl hover:border-slate-700 transition-colors flex items-center justify-between"
            >
              <div className="flex items-center space-x-3 min-w-0">
                <div className="p-2 rounded-lg bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  <Award className="w-4 h-4" />
                </div>
                <div className="min-w-0">
                  <div className="flex items-center space-x-2">
                    <h4 className="text-sm font-bold text-white truncate">{item.drop_name}</h4>
                    <span className="text-[10px] text-purple-400 font-medium">{item.game_name}</span>
                  </div>
                  <div className="flex items-center space-x-3 text-[11px] text-slate-400 mt-0.5">
                    <span className="flex items-center space-x-1">
                      <Clock className="w-3 h-3 text-slate-500" />
                      <span>{new Date(item.claimed_at).toLocaleString()}</span>
                    </span>
                    {item.channel_name && (
                      <span className="flex items-center space-x-1">
                        <Tv className="w-3 h-3 text-slate-500" />
                        <span>@{item.channel_name}</span>
                      </span>
                    )}
                  </div>
                </div>
              </div>

              <div className="flex items-center space-x-1 text-xs text-emerald-400 font-semibold">
                <CheckCircle2 className="w-4 h-4" />
                <span>Claimed</span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
