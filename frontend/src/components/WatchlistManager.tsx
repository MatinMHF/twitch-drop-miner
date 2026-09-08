import React, { useState, useEffect, useRef } from 'react';
import { api } from '../services/api';
import { WatchlistItem, GameSearchResult } from '../services/types';
import {
  Search,
  Plus,
  Trash2,
  ChevronUp,
  ChevronDown,
  Flame,
  CheckCircle2,
  Sparkles,
  Loader2,
  Power,
  Download,
  Upload,
} from 'lucide-react';

interface WatchlistManagerProps {
  onWatchlistChanged?: () => void;
}

export const WatchlistManager: React.FC<WatchlistManagerProps> = ({ onWatchlistChanged }) => {
  const [items, setItems] = useState<WatchlistItem[]>([]);
  const [searchQuery, setSearchQuery] = useState('');
  const [searchResults, setSearchResults] = useState<GameSearchResult[]>([]);
  const [isSearching, setIsSearching] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [isBackingUp, setIsBackingUp] = useState(false);
  const [isRestoring, setIsRestoring] = useState(false);

  const [isDropdownOpen, setIsDropdownOpen] = useState(false);
  const searchContainerRef = useRef<HTMLDivElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);


  const fetchWatchlist = async () => {
    try {
      const data = await api.getWatchlist();
      setItems(data);
      if (onWatchlistChanged) onWatchlistChanged();
    } catch (err) {
      console.error('Failed to load watchlist', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchWatchlist();
  }, []);

  // Close dropdown on click outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (searchContainerRef.current && !searchContainerRef.current.contains(event.target as Node)) {
        setIsDropdownOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  // Fast Debounced game search
  useEffect(() => {
    if (!searchQuery.trim()) {
      setSearchResults([]);
      setIsDropdownOpen(false);
      setIsSearching(false);
      return;
    }

    setIsSearching(true);
    setIsDropdownOpen(true);

    const timer = setTimeout(async () => {
      try {
        const results = await api.searchGames(searchQuery.trim());
        setSearchResults(results);
        setIsDropdownOpen(true);
      } catch (err) {
        console.error('Search error', err);
      } finally {
        setIsSearching(false);
      }
    }, 250);

    return () => clearTimeout(timer);
  }, [searchQuery]);

  const handleAddGame = async (game: GameSearchResult) => {
    try {
      await api.addToWatchlist({
        game_id: game.id,
        game_name: game.name,
        box_art_url: game.box_art_url,
        priority: items.length,
        auto_mine: true,
      });
      setSearchQuery('');
      setSearchResults([]);
      setIsDropdownOpen(false);
      await fetchWatchlist();
    } catch (err: any) {
      alert(`Could not add game: ${err.message}`);
    }
  };

  const handleRemove = async (gameId: string) => {
    try {
      await api.removeFromWatchlist(gameId);
      await fetchWatchlist();
    } catch (err: any) {
      alert(`Could not remove game: ${err.message}`);
    }
  };

  const handleToggleAutoMine = async (item: WatchlistItem) => {
    try {
      await api.updateWatchlistItem(item.game_id, {
        priority: item.priority,
        auto_mine: !item.auto_mine,
      });
      await fetchWatchlist();
    } catch (err: any) {
      alert(`Toggle failed: ${err.message}`);
    }
  };

  const handleMove = async (index: number, direction: 'up' | 'down') => {
    const targetIndex = direction === 'up' ? index - 1 : index + 1;
    if (targetIndex < 0 || targetIndex >= items.length) return;

    const newItems = [...items];
    const temp = newItems[index];
    newItems[index] = newItems[targetIndex];
    newItems[targetIndex] = temp;

    setItems(newItems);
    try {
      await api.reorderWatchlist(newItems.map((i) => i.game_id));
    } catch (err: any) {
      console.error('Failed to save priority order', err);
      await fetchWatchlist();
    }
  };

  const handleBackup = async () => {
    try {
      setIsBackingUp(true);
      const data = await api.backupWatchlist();
      const jsonString = `data:text/json;charset=utf-8,${encodeURIComponent(
        JSON.stringify(data, null, 2)
      )}`;
      const downloadAnchor = document.createElement('a');
      const dateStr = new Date().toISOString().slice(0, 10);
      downloadAnchor.setAttribute('href', jsonString);
      downloadAnchor.setAttribute('download', `twitch_watchlist_backup_${dateStr}.json`);
      document.body.appendChild(downloadAnchor);
      downloadAnchor.click();
      downloadAnchor.remove();
    } catch (err: any) {
      alert(`Backup failed: ${err.message}`);
    } finally {
      setIsBackingUp(false);
    }
  };

  const handleRestoreFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = async (event) => {
      try {
        const text = event.target?.result as string;
        const parsed = JSON.parse(text);
        const games = Array.isArray(parsed) ? parsed : parsed.games;
        if (!games || !Array.isArray(games) || games.length === 0) {
          throw new Error('Invalid backup file format: missing games array');
        }

        setIsRestoring(true);
        const restored = await api.restoreWatchlist({ games, replace_existing: true });
        setItems(restored);
        if (onWatchlistChanged) onWatchlistChanged();
        alert(`Successfully restored ${restored.length} games and their priority order!`);
      } catch (err: any) {
        alert(`Failed to restore backup: ${err.message}`);
      } finally {
        setIsRestoring(false);
        if (fileInputRef.current) fileInputRef.current.value = '';
      }
    };
    reader.readAsText(file);
  };

  return (
    <div className="bg-slate-900/80 backdrop-blur-md border border-slate-800 rounded-2xl p-6 shadow-xl relative">
      {/* Hidden file input for restore */}
      <input
        type="file"
        ref={fileInputRef}
        onChange={handleRestoreFile}
        accept=".json,application/json"
        className="hidden"
      />

      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-5 border-b border-slate-800/80">
        <div>
          <div className="flex items-center space-x-3">
            <h2 className="text-xl font-bold text-white tracking-tight flex items-center space-x-2">
              <span>Game Watchlist</span>
              <span className="text-xs font-normal text-slate-400 bg-slate-800 px-2 py-0.5 rounded-full border border-slate-700">
                {items.length}
              </span>
            </h2>

            {/* Backup & Restore Buttons */}
            <div className="flex items-center space-x-1.5">
              <button
                onClick={handleBackup}
                disabled={isBackingUp || items.length === 0}
                className="px-2.5 py-1 rounded-lg text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 hover:text-white border border-slate-700/60 transition-all flex items-center space-x-1.5 shadow-sm disabled:opacity-40 disabled:cursor-not-allowed"
                title="Download backup file of selected games & priority order"
              >
                {isBackingUp ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin text-purple-400" />
                ) : (
                  <Download className="w-3.5 h-3.5 text-purple-400" />
                )}
                <span>Backup</span>
              </button>

              <button
                onClick={() => fileInputRef.current?.click()}
                disabled={isRestoring}
                className="px-2.5 py-1 rounded-lg text-xs font-semibold bg-slate-800 hover:bg-slate-700 text-slate-200 hover:text-white border border-slate-700/60 transition-all flex items-center space-x-1.5 shadow-sm disabled:opacity-40"
                title="Restore games and priority order from a backup JSON file"
              >
                {isRestoring ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin text-emerald-400" />
                ) : (
                  <Upload className="w-3.5 h-3.5 text-emerald-400" />
                )}
                <span>Restore</span>
              </button>
            </div>
          </div>
          <p className="text-xs text-slate-400 mt-0.5">
            Mines drops in order of priority (top to bottom).
          </p>
        </div>

        {/* Search & Add Input */}
        <div ref={searchContainerRef} className="relative w-full sm:w-72">
          <div className="relative">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              type="text"
              placeholder="Search games (e.g. Delta Force)..."
              value={searchQuery}
              onFocus={() => {
                if (searchQuery.trim()) setIsDropdownOpen(true);
              }}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="w-full pl-9 pr-9 py-2 text-xs rounded-xl bg-slate-950 border border-slate-700/80 text-white placeholder-slate-500 focus:outline-none focus:border-purple-500 focus:ring-1 focus:ring-purple-500 transition-all"
            />

            {isSearching ? (
              <Loader2 className="w-4 h-4 text-purple-400 animate-spin absolute right-3 top-1/2 -translate-y-1/2" />
            ) : searchQuery.trim() ? (
              <button
                type="button"
                onClick={() => {
                  setSearchQuery('');
                  setSearchResults([]);
                  setIsDropdownOpen(false);
                }}
                className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300 text-xs font-bold"
              >
                ×
              </button>
            ) : null}
          </div>

          {/* Search Results Dropdown */}
          {isDropdownOpen && searchQuery.trim().length > 0 && (
            <div className="absolute top-full left-0 right-0 mt-2 bg-slate-900 border border-slate-700 rounded-xl shadow-2xl z-50 max-h-72 overflow-y-auto divide-y divide-slate-800">
              {isSearching && searchResults.length === 0 ? (
                <div className="p-4 text-center text-slate-400 text-xs flex items-center justify-center space-x-2">
                  <Loader2 className="w-3.5 h-3.5 animate-spin text-purple-400" />
                  <span>Searching Twitch directory...</span>
                </div>
              ) : searchResults.length === 0 ? (
                <div className="p-4 text-center text-slate-400 text-xs">
                  No games found matching "{searchQuery}"
                </div>
              ) : (
                searchResults.map((game) => {
                  const isAdded = items.some((i) => i.game_id === game.id);
                  return (
                    <div
                      key={game.id}
                      className="p-2.5 flex items-center justify-between hover:bg-slate-800/60 transition-colors"
                    >
                      <div className="flex items-center space-x-2.5 min-w-0">
                        {game.box_art_url ? (
                          <img
                            src={game.box_art_url}
                            alt={game.name}
                            className="w-8 h-10 object-cover rounded shadow border border-slate-800 shrink-0"
                          />
                        ) : (
                          <div className="w-8 h-10 bg-slate-800 rounded flex items-center justify-center text-[10px] text-slate-500 shrink-0">
                            N/A
                          </div>
                        )}
                        <div className="min-w-0">
                          <p className="text-xs font-bold text-white truncate">{game.name}</p>
                          {game.has_active_drops ? (
                            <span className="inline-flex items-center space-x-1 text-[10px] text-purple-400 font-medium">
                              <Sparkles className="w-2.5 h-2.5 text-purple-400" />
                              <span>Active Drops Available</span>
                            </span>
                          ) : (
                            <span className="text-[10px] text-slate-500">
                              Twitch Game
                            </span>
                          )}
                        </div>
                      </div>

                      <button
                        onClick={() => handleAddGame(game)}
                        disabled={isAdded}
                        className={`ml-2 px-2.5 py-1 rounded-lg text-xs font-semibold flex items-center space-x-1 transition-all shrink-0 ${
                          isAdded
                            ? 'bg-slate-800 text-slate-500 cursor-not-allowed'
                            : 'bg-purple-600 hover:bg-purple-500 text-white shadow-sm shadow-purple-600/30'
                        }`}
                      >
                        {isAdded ? (
                          <>
                            <CheckCircle2 className="w-3 h-3 text-emerald-400" />
                            <span>Added</span>
                          </>
                        ) : (
                          <>
                            <Plus className="w-3 h-3" />
                            <span>Add</span>
                          </>
                        )}
                      </button>
                    </div>
                  );
                })
              )}
            </div>
          )}
        </div>
      </div>

      {/* Watchlist Items */}
      <div className="mt-4 space-y-2">
        {isLoading ? (
          <div className="py-12 text-center text-slate-500 text-xs flex items-center justify-center space-x-2">
            <Loader2 className="w-4 h-4 animate-spin text-purple-400" />
            <span>Loading watchlist...</span>
          </div>
        ) : items.length === 0 ? (
          <div className="py-10 text-center border border-dashed border-slate-800 rounded-xl">
            <Flame className="w-8 h-8 text-slate-600 mx-auto mb-2" />
            <p className="text-xs text-slate-400">Your watchlist is empty.</p>
            <p className="text-[11px] text-slate-500 mt-0.5">
              Search for your favorite games above to prioritize them for drop rewards.
            </p>
          </div>
        ) : (
          items.map((item, index) => (
            <div
              key={item.game_id}
              className={`flex items-center justify-between p-3 rounded-xl border transition-all ${
                item.is_currently_mining
                  ? 'bg-purple-950/30 border-purple-500/50 shadow-md shadow-purple-500/5'
                  : 'bg-slate-950/40 border-slate-800/80 hover:border-slate-700'
              }`}
            >
              {/* Game Info */}
              <div className="flex items-center space-x-3 min-w-0">
                <span className="text-xs font-mono font-bold text-slate-500 w-4 text-center">
                  #{index + 1}
                </span>

                {item.box_art_url ? (
                  <img
                    src={item.box_art_url}
                    alt={item.game_name}
                    className="w-8 h-10 object-cover rounded shadow border border-slate-800"
                  />
                ) : (
                  <div className="w-8 h-10 bg-slate-800 rounded flex items-center justify-center text-[10px] text-slate-500 font-mono">
                    N/A
                  </div>
                )}

                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-1.5">
                    <p className="text-sm font-bold text-white truncate">{item.game_name}</p>
                    {item.is_currently_mining ? (
                      <span className="text-[10px] font-semibold uppercase bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 px-2 py-0.5 rounded-full animate-pulse">
                        Mining Now
                      </span>
                    ) : (item.active_drops_count ?? item.active_campaigns_count) > 0 ? (
                      <span className="text-[10px] font-medium bg-purple-500/20 text-purple-300 border border-purple-500/30 px-2 py-0.5 rounded-full flex items-center space-x-1">
                        <Sparkles className="w-2.5 h-2.5 text-purple-400" />
                        <span>Active Drops ({item.active_drops_count ?? item.active_campaigns_count})</span>
                      </span>
                    ) : item.is_completed ? (
                      <span
                        className="text-[10px] font-medium bg-emerald-500/10 text-emerald-400/90 border border-emerald-500/20 px-2 py-0.5 rounded-full flex items-center space-x-1"
                        title="All available drops for this game have been earned and claimed!"
                      >
                        <CheckCircle2 className="w-2.5 h-2.5 text-emerald-400" />
                        <span>All Drops Claimed</span>
                      </span>
                    ) : (
                      <span
                        className="text-[10px] font-medium bg-amber-500/10 text-amber-400/90 border border-amber-500/20 px-2 py-0.5 rounded-full flex items-center space-x-1"
                        title="No active Twitch drop campaign currently. Miner will auto-start as soon as Twitch launches drops for this game!"
                      >
                        <span>⏳ Waiting for Drops (Auto-start)</span>
                      </span>
                    )}
                  </div>
                  <p className="text-[11px] text-slate-400">
                    Added: {new Date(item.created_at).toLocaleDateString()}
                  </p>
                </div>
              </div>

              {/* Controls */}
              <div className="flex items-center space-x-2">
                {/* Auto-Mine Toggle */}
                <button
                  onClick={() => handleToggleAutoMine(item)}
                  className={`p-1.5 rounded-lg border text-xs transition-colors ${
                    item.auto_mine
                      ? 'bg-emerald-950/40 text-emerald-400 border-emerald-500/30 hover:bg-emerald-900/40'
                      : 'bg-slate-900 text-slate-500 border-slate-800 hover:text-slate-400'
                  }`}
                  title={item.auto_mine ? 'Auto-mine enabled' : 'Auto-mine disabled'}
                >
                  <Power className="w-3.5 h-3.5" />
                </button>

                {/* Priority Up / Down */}
                <div className="flex flex-col space-y-0.5">
                  <button
                    onClick={() => handleMove(index, 'up')}
                    disabled={index === 0}
                    className="p-1 rounded bg-slate-800/80 hover:bg-slate-700 text-slate-400 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed"
                    title="Move up"
                  >
                    <ChevronUp className="w-3 h-3" />
                  </button>
                  <button
                    onClick={() => handleMove(index, 'down')}
                    disabled={index === items.length - 1}
                    className="p-1 rounded bg-slate-800/80 hover:bg-slate-700 text-slate-400 hover:text-white disabled:opacity-30 disabled:cursor-not-allowed"
                    title="Move down"
                  >
                    <ChevronDown className="w-3 h-3" />
                  </button>
                </div>

                {/* Delete */}
                <button
                  onClick={() => handleRemove(item.game_id)}
                  className="p-1.5 rounded-lg bg-slate-800/80 hover:bg-rose-950/60 text-slate-400 hover:text-rose-400 border border-slate-700/50 hover:border-rose-500/30 transition-colors"
                  title="Remove from watchlist"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
};
