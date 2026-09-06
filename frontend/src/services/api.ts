import {
  UserProfile,
  TwitchAccount,
  DeviceCodeInit,
  DeviceCodeStatus,
  GameSearchResult,
  WatchlistItem,
  MinerStatus,
  ClaimedDrop,
  AppSettings,
} from './types';

// Helper to get CSRF token from cookie
function getCsrfToken(): string | null {
  const match = document.cookie.match(new RegExp('(^| )csrf_token=([^;]+)'));
  return match ? match[2] : null;
}

async function request<T>(endpoint: string, options: RequestInit = {}): Promise<T> {
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(options.headers as Record<string, string>),
  };

  const csrf = getCsrfToken();
  if (csrf) {
    headers['X-CSRF-Token'] = csrf;
  }

  const response = await fetch(endpoint, {
    ...options,
    headers,
    credentials: 'include', // send cookies
  });

  if (response.status === 401 && !endpoint.includes('/api/auth/login') && !endpoint.includes('/api/auth/status')) {
    // Attempt token refresh
    try {
      const refreshRes = await fetch('/api/auth/refresh', {
        method: 'POST',
        credentials: 'include',
      });
      if (refreshRes.ok) {
        // Retry original request once
        const retryRes = await fetch(endpoint, {
          ...options,
          headers,
          credentials: 'include',
        });
        if (!retryRes.ok) {
          throw new Error(`HTTP error ${retryRes.status}`);
        }
        return retryRes.json();
      }
    } catch {
      // Refresh failed
    }
  }

  if (!response.ok) {
    const errorData = await response.json().catch(() => ({ detail: response.statusText }));
    throw new Error(errorData.detail || `Request failed with status ${response.status}`);
  }

  return response.json();
}

export const api = {
  // Auth
  getAuthStatus: () => request<UserProfile>('/api/auth/status'),
  setupAdmin: (data: { username: string; password: string }) =>
    request<UserProfile>('/api/auth/setup', { method: 'POST', body: JSON.stringify(data) }),
  login: (data: { username: string; password: string }) =>
    request<UserProfile>('/api/auth/login', { method: 'POST', body: JSON.stringify(data) }),
  logout: () => request<{ message: string }>('/api/auth/logout', { method: 'POST' }),

  // Twitch Account & Device Flow
  getTwitchAccount: () => request<TwitchAccount>('/api/auth/twitch/account'),
  disconnectTwitch: () => request<{ message: string }>('/api/auth/twitch/account', { method: 'DELETE' }),
  initDeviceCode: () => request<DeviceCodeInit>('/api/auth/twitch/device-code/init', { method: 'POST' }),
  checkDeviceCodeStatus: (deviceCode: string) =>
    request<DeviceCodeStatus>(`/api/auth/twitch/device-code/status?device_code=${encodeURIComponent(deviceCode)}`),

  // Games & Watchlist
  searchGames: (query: string) =>
    request<GameSearchResult[]>(`/api/games/search?query=${encodeURIComponent(query)}`),
  getWatchlist: () => request<WatchlistItem[]>('/api/games/watchlist'),
  addToWatchlist: (data: { game_id: string; game_name: string; box_art_url?: string; priority?: number; auto_mine?: boolean }) =>
    request<WatchlistItem>('/api/games/watchlist', { method: 'POST', body: JSON.stringify(data) }),
  updateWatchlistItem: (gameId: string, data: { priority: number; auto_mine?: boolean }) =>
    request<WatchlistItem>(`/api/games/watchlist/${gameId}`, { method: 'PUT', body: JSON.stringify(data) }),
  removeFromWatchlist: (gameId: string) =>
    request<{ message: string }>(`/api/games/watchlist/${gameId}`, { method: 'DELETE' }),
  reorderWatchlist: (gameIds: string[]) =>
    request<{ message: string }>('/api/games/watchlist/reorder', { method: 'POST', body: JSON.stringify({ game_ids: gameIds }) }),

  // Campaigns & Claims
  getActiveCampaigns: () => request<any[]>('/api/campaigns/active'),
  getClaimedDrops: (limit = 50) => request<ClaimedDrop[]>(`/api/campaigns/history?limit=${limit}`),

  // Miner Control
  getMinerStatus: () => request<MinerStatus>('/api/miner/status'),
  controlMiner: (action: 'start' | 'stop' | 'pause' | 'resume' | 'force_check') =>
    request<{ action: string; status: MinerStatus; message: string }>('/api/miner/control', {
      method: 'POST',
      body: JSON.stringify({ action }),
    }),

  // Settings
  getSettings: () => request<AppSettings>('/api/settings'),
  updateSettings: (data: Partial<AppSettings>) =>
    request<AppSettings>('/api/settings', { method: 'PUT', body: JSON.stringify(data) }),
};
