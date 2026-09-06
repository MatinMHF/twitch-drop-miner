import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import { Calendar, Loader2 } from 'lucide-react';

export const DropCampaignList: React.FC = () => {
  const [campaigns, setCampaigns] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  useEffect(() => {
    const fetchCampaigns = async () => {
      try {
        const data = await api.getActiveCampaigns();
        setCampaigns(data);
      } catch (err) {
        console.error('Failed to load campaigns', err);
      } finally {
        setIsLoading(false);
      }
    };
    fetchCampaigns();
  }, []);

  return (
    <div className="bg-slate-900/80 backdrop-blur-md border border-slate-800 rounded-2xl p-6 shadow-xl">
      <div className="flex items-center justify-between pb-4 border-b border-slate-800/80">
        <div>
          <h2 className="text-xl font-bold text-white tracking-tight flex items-center space-x-2">
            <span>Discovered Campaigns</span>
            <span className="text-xs font-normal text-slate-400 bg-slate-800 px-2 py-0.5 rounded-full border border-slate-700">
              {campaigns.length}
            </span>
          </h2>
          <p className="text-xs text-slate-400 mt-0.5">
            Active drop events directly fetched from Twitch GQL.
          </p>
        </div>
      </div>

      <div className="mt-4 space-y-3 max-h-96 overflow-y-auto pr-1">
        {isLoading ? (
          <div className="py-12 text-center text-slate-500 text-xs flex items-center justify-center space-x-2">
            <Loader2 className="w-4 h-4 animate-spin text-purple-400" />
            <span>Loading active campaigns...</span>
          </div>
        ) : campaigns.length === 0 ? (
          <div className="py-8 text-center text-slate-500 text-xs">
            No active drop campaigns found currently on Twitch.
          </div>
        ) : (
          campaigns.map((camp) => (
            <div
              key={camp.id}
              className="p-3 bg-slate-950/40 border border-slate-800/80 rounded-xl hover:border-slate-700 transition-colors flex items-center justify-between"
            >
              <div className="flex items-center space-x-3 min-w-0">
                {camp.game?.box_art_url ? (
                  <img
                    src={camp.game.box_art_url}
                    alt={camp.game?.name}
                    className="w-10 h-12 object-cover rounded shadow border border-slate-800"
                  />
                ) : (
                  <div className="w-10 h-12 bg-slate-800 rounded flex items-center justify-center text-[10px] text-slate-500">
                    N/A
                  </div>
                )}
                <div className="min-w-0">
                  <span className="text-[10px] uppercase font-bold tracking-wider text-purple-400">
                    {camp.game?.name || 'Twitch Game'}
                  </span>
                  <h4 className="text-sm font-bold text-white truncate">{camp.name}</h4>
                  <div className="flex items-center space-x-2 text-[11px] text-slate-400 mt-0.5">
                    <Calendar className="w-3 h-3 text-slate-500" />
                    <span>
                      {camp.end_at ? `Ends ${new Date(camp.end_at).toLocaleDateString()}` : 'Active'}
                    </span>
                  </div>
                </div>
              </div>

              <div className="flex items-center space-x-2">
                <span className="text-[10px] font-semibold px-2 py-1 rounded-full bg-emerald-950/40 text-emerald-400 border border-emerald-500/30">
                  ACTIVE
                </span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
