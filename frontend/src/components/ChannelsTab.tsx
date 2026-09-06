import React, { useEffect, useState } from 'react';
import { api } from '../services/api';
import {
  Tv,
  Users,
  ExternalLink,
  Search,
  RotateCw,
  Radio,
} from 'lucide-react';

export const ChannelsTab: React.FC = () => {
  const [channels, setChannels] = useState<any[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');

  const fetchChannels = async () => {
    try {
      setIsLoading(true);
      const data = await api.getEligibleChannels();
      setChannels(data || []);
    } catch (err) {
      console.error('Failed to load eligible channels', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchChannels();
  }, []);

  const filteredChannels = channels.filter((ch) => {
    const q = searchQuery.toLowerCase();
    return (
      ch.channel_display_name?.toLowerCase().includes(q) ||
      ch.channel_login?.toLowerCase().includes(q) ||
      ch.game_name?.toLowerCase().includes(q) ||
      ch.title?.toLowerCase().includes(q)
    );
  });

  return (
    <div className="bg-slate-900/80 backdrop-blur-md border border-slate-800 rounded-2xl p-6 shadow-xl space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-slate-800/80">
        <div>
          <div className="flex items-center space-x-2">
            <Radio className="w-5 h-5 text-purple-600 dark:text-purple-400" />
            <h2 className="text-xl font-bold text-white tracking-tight flex items-center space-x-2">
              <span>Drop-Eligible Channels</span>
              <span className="text-xs font-semibold text-purple-600 dark:text-purple-300 bg-purple-500/10 px-2.5 py-0.5 rounded-full border border-purple-500/20">
                {channels.length} Live
              </span>
            </h2>
          </div>
          <p className="text-xs text-slate-400 mt-1">
            Live Twitch broadcasters streaming watchlisted games with active drop campaigns.
          </p>
        </div>

        <div className="flex items-center space-x-2">
          <div className="relative">
            <Search className="w-3.5 h-3.5 text-slate-500 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Filter channels or games..."
              className="pl-8 pr-3 py-1.5 text-xs rounded-xl bg-slate-950 border border-slate-800 text-white placeholder-slate-500 focus:outline-none focus:border-purple-500 w-48 sm:w-60"
            />
          </div>

          <button
            onClick={fetchChannels}
            disabled={isLoading}
            className="p-2 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white border border-slate-700/60 transition-all disabled:opacity-50"
            title="Refresh Channels"
          >
            <RotateCw className={`w-4 h-4 ${isLoading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {isLoading ? (
        <div className="py-16 text-center text-slate-400 text-xs flex flex-col items-center justify-center space-y-3">
          <RotateCw className="w-6 h-6 animate-spin text-purple-600 dark:text-purple-400" />
          <span>Scanning Twitch directory for live drop streams...</span>
        </div>
      ) : filteredChannels.length === 0 ? (
        <div className="py-12 text-center border border-dashed border-slate-800 rounded-xl bg-slate-950/30">
          <Tv className="w-10 h-10 text-slate-600 mx-auto mb-2" />
          <p className="text-sm font-medium text-slate-300">
            {searchQuery ? 'No matching live channels found.' : 'No live channels currently broadcasting your watchlisted games.'}
          </p>
          <p className="text-xs text-slate-500 mt-1">
            Add more games to your Priority Watchlist to discover additional live channels.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filteredChannels.map((ch) => (
            <div
              key={ch.channel_id || ch.channel_login}
              className="p-4 bg-slate-950/60 border border-slate-800/80 rounded-xl hover:border-slate-700 transition-all flex flex-col justify-between space-y-3 group"
            >
              <div>
                <div className="flex items-start justify-between gap-2 mb-2">
                  <span className="text-[10px] font-bold uppercase tracking-wider text-purple-600 dark:text-purple-400 bg-purple-500/10 px-2 py-0.5 rounded border border-purple-500/20 truncate">
                    {ch.game_name}
                  </span>
                  <span className="flex items-center space-x-1 text-[10px] font-semibold px-2 py-0.5 rounded-full bg-emerald-950/40 text-emerald-600 dark:text-emerald-400 border border-emerald-500/30 shrink-0">
                    <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse" />
                    <span>LIVE</span>
                  </span>
                </div>

                <div className="flex items-center space-x-2.5">
                  <div className="w-9 h-9 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center font-bold text-xs text-purple-600 dark:text-purple-300 uppercase shrink-0">
                    {ch.channel_display_name?.[0] || 'T'}
                  </div>
                  <div className="min-w-0">
                    <h3 className="text-sm font-bold text-white truncate group-hover:text-purple-600 dark:group-hover:text-purple-300 transition-colors">
                      {ch.channel_display_name}
                    </h3>
                    <p className="text-[11px] text-slate-400 font-mono">@{ch.channel_login}</p>
                  </div>
                </div>

                <p className="text-xs text-slate-400 mt-2 line-clamp-2" title={ch.title}>
                  {ch.title || 'Drops Enabled Live Stream'}
                </p>
              </div>

              <div className="flex items-center justify-between pt-3 border-t border-slate-800/60 text-xs">
                <div className="flex items-center space-x-1 text-slate-400">
                  <Users className="w-3.5 h-3.5 text-slate-500" />
                  <span>{ch.viewers_count?.toLocaleString() || 0} viewers</span>
                </div>

                <a
                  href={`https://twitch.tv/${ch.channel_login}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="flex items-center space-x-1 text-purple-600 dark:text-purple-400 hover:text-purple-500 dark:hover:text-purple-300 font-medium text-[11px] transition-colors"
                >
                  <span>Open Twitch</span>
                  <ExternalLink className="w-3 h-3" />
                </a>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
