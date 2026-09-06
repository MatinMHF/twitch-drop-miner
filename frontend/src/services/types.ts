export interface UserProfile {
  id: string;
  username: string;
  is_active: boolean;
  is_setup_completed: boolean;
}

export interface TwitchAccount {
  connected: boolean;
  twitch_user_id?: string;
  twitch_username?: string;
  connected_at?: string;
}

export interface DeviceCodeInit {
  device_code: string;
  user_code: string;
  verification_uri: string;
  expires_in: number;
  interval: number;
}

export interface DeviceCodeStatus {
  status: 'pending' | 'success' | 'expired' | 'failed';
  message: string;
  twitch_username?: string;
}

export interface GameSearchResult {
  id: string;
  name: string;
  box_art_url?: string;
  has_active_drops: boolean;
  active_campaign_count: number;
}

export interface WatchlistItem {
  id: string;
  game_id: string;
  game_name: string;
  box_art_url?: string;
  priority: number;
  is_active: boolean;
  auto_mine: boolean;
  created_at: string;
  active_campaigns_count: number;
  is_currently_mining: boolean;
}

export interface WatchlistBackupItem {
  game_id: string;
  game_name: string;
  box_art_url?: string;
  priority: number;
  auto_mine: boolean;
  is_active: boolean;
}

export interface WatchlistBackupData {
  app: string;
  version: string;
  exported_at: string;
  total_games: number;
  games: WatchlistBackupItem[];
}


export interface ChannelStreamInfo {
  channel_id: string;
  channel_login: string;
  channel_display_name: string;
  title: string;
  viewers_count: number;
  game_name: string;
  is_live: boolean;
  stream_id?: string;
}

export interface ActiveMiningTarget {
  game_id: string;
  game_name: string;
  campaign_id: string;
  campaign_name: string;
  drop_id: string;
  drop_instance_id?: string;
  drop_name: string;
  required_minutes: number;
  current_minutes: number;
  progress_percent: number;
  channel?: ChannelStreamInfo;
}

export interface MinerStatus {
  state: 'IDLE' | 'MINING' | 'PAUSED' | 'ERROR' | 'NO_ACCOUNT';
  active_targets?: ActiveMiningTarget[];
  active_game_id?: string;
  active_game_name?: string;
  active_campaign_id?: string;
  active_campaign_name?: string;
  active_channel?: ChannelStreamInfo;
  current_drop_id?: string;
  current_drop_name?: string;
  current_drop_progress_percent: number;
  current_drop_minutes_watched: number;
  current_drop_required_minutes: number;
  total_drops_claimed_session: number;
  last_heartbeat_at?: string;
  next_poll_at?: string;
  error_message?: string;
  is_paused: boolean;
}

export interface ClaimedDrop {
  id: string;
  drop_id: string;
  drop_name: string;
  campaign_id: string;
  campaign_name: string;
  game_id: string;
  game_name: string;
  channel_name?: string;
  claimed_at: string;
  benefit_id?: string;
}

export interface AppSettings {
  poll_interval_minutes: number;
  watch_heartbeat_seconds: number;
  auto_claim_drops: boolean;
  auto_failover_streamers: boolean;
  timezone: string;
  custom_spade_url?: string;
  custom_query_hashes?: Record<string, string>;
}
