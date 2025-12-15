/**
 * API client for communicating with the Python backend.
 */

// Use the same hostname as the frontend but on port 8000 for API calls
// This allows the app to work from any device on the network
const getApiBase = () => {
  if (typeof window === 'undefined') {
    return 'http://localhost:8000/api';
  }
  const hostname = window.location.hostname;
  return `http://${hostname}:8000/api`;
};

const API_BASE = getApiBase();

export interface Index {
  id: number;
  name: string;
  slug: string;
  description: string | null;
  ranking_config: RankingConfig;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  source_count: number;
  document_count: number;
}

export interface RankingConfig {
  domain_boosts: Record<string, number>;
  recency_weight: number;
  custom_weights: Record<string, number>;
}

export interface Source {
  id: number;
  index_id: number;
  url: string;
  source_type: 'domain' | 'url' | 'sitemap';
  name: string | null;
  crawl_depth: number;
  crawl_frequency: 'hourly' | 'daily' | 'weekly' | 'monthly';
  crawl_mode: 'text_only' | 'images_only' | 'videos_only' | 'text_images' | 'text_videos' | 'images_videos' | 'all';
  max_pages: number;
  include_patterns: string[];
  exclude_patterns: string[];
  respect_robots: boolean;
  use_tor: boolean;
  is_active: boolean;
  last_crawl_at: string | null;
  page_count: number;
  error_count: number;
  last_error: string | null;
  created_at: string;
  updated_at: string;
  domain: string;
  display_name: string;
}

export interface SearchResult {
  source: string;
  index: string | null;
  url: string;
  title: string;
  snippet: string;
  domain: string;
  published_at: string | null;
  score: number;
}

export interface SearchResponse {
  query: string;
  total_results: number;
  page: number;
  per_page: number;
  results: SearchResult[];
  facets: Record<string, Array<{ value: string; count: number }>>;
  timing: {
    local_ms: number;
    external_ms: number;
    total_ms: number;
  };
}

export interface ImageSearchResult {
  image_url: string;
  image_alt: string;
  page_url: string;
  page_title: string;
  domain: string;
  score: number;
}

export interface ImageSearchResponse {
  query: string;
  total_results: number;
  page: number;
  per_page: number;
  results: ImageSearchResult[];
  timing_ms: number;
}

export interface ImageSearchStatus {
  enabled: boolean;
  model_loaded: boolean;
  model_name: string;
  embedding_dimensions: number;
}

export interface VideoSearchResult {
  video_url: string;
  thumbnail_url: string;
  embed_type: 'direct' | 'youtube' | 'vimeo' | 'page_link';
  video_id: string | null;
  video_title: string;
  page_url: string;
  page_title: string;
  domain: string;
  score: number;
}

export interface VideoSearchResponse {
  query: string;
  total_results: number;
  page: number;
  per_page: number;
  results: VideoSearchResult[];
  timing_ms: number;
}

export interface CrawlJob {
  id: number;
  source_id: number;
  source_url: string | null;
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled';
  trigger: 'manual' | 'scheduled';
  pages_crawled: number;
  pages_indexed: number;
  pages_failed: number;
  started_at: string | null;
  completed_at: string | null;
  error_message: string | null;
  is_active?: boolean;
}

export interface CollectionItem {
  id: number;
  item_type: 'image' | 'video';
  url: string;
  thumbnail_url: string | null;
  title: string | null;
  source_url: string | null;
  domain: string | null;
  embed_type: string | null;
  video_id: string | null;
  sort_order: number;
  added_at: string;
}

export interface Collection {
  id: number;
  name: string;
  slug: string;
  description: string | null;
  cover_url: string | null;
  sort_order: number;
  item_count: number;
  created_at: string;
  updated_at: string;
}

export interface CollectionWithItems extends Collection {
  items: CollectionItem[];
}

export interface CollectionItemCreate {
  item_type: 'image' | 'video';
  url: string;
  thumbnail_url?: string | null;
  title?: string | null;
  source_url?: string | null;
  domain?: string | null;
  embed_type?: string | null;
  video_id?: string | null;
}

// Channel/Feed types
export interface Channel {
  id: number;
  platform: 'youtube' | 'rumble' | 'podcast';
  platform_channel_id: string;
  channel_url: string;
  name: string;
  description: string | null;
  avatar_url: string | null;
  banner_url: string | null;
  subscriber_count: number | null;
  is_active: boolean;
  last_synced_at: string | null;
  last_sync_error: string | null;
  consecutive_errors: number;
  import_source: string | null;
  created_at: string;
  updated_at: string;
  display_name: string;
  video_count: number;
  unwatched_count: number;
}

export interface FeedItem {
  id: number;
  channel_id: number;
  platform: 'youtube' | 'rumble' | 'podcast';
  video_id: string;
  video_url: string;
  title: string;
  description: string | null;
  thumbnail_url: string | null;
  duration_seconds: number | null;
  view_count: number | null;
  upload_date: string;
  categories: string[] | null;
  is_watched: boolean;
  watched_at: string | null;
  watch_progress_seconds: number | null;
  discovered_at: string;
  duration_formatted: string;
  is_recent: boolean;
  channel_name: string;
  channel_avatar_url: string | null;
}

// Feed mode types
export type FeedMode =
  | 'newest' | 'oldest' | 'most_viewed' | 'shortest' | 'longest' | 'random'
  | 'catch_up' | 'quick_watch' | 'deep_dive'
  | 'focus_learning' | 'stay_positive' | 'music_mode' | 'news_politics' | 'gaming';

export interface FeedResponse {
  items: FeedItem[];
  total: number;
  page: number;
  per_page: number;
  has_more: boolean;
}

export interface ChannelGroupedFeed {
  channel_id: number;
  channel_name: string;
  channel_avatar_url: string | null;
  platform: string;
  items: FeedItem[];
  total_items: number;
  unwatched_count: number;
}

export interface ImportResult {
  imported: number;
  skipped: number;
  failed: number;
  channels: Channel[];
  errors: string[];
}

export interface SyncResult {
  channel_id: number;
  channel_name: string;
  success: boolean;
  new_videos: number;
  error: string | null;
}

export interface ChannelSearchResult {
  platform: 'youtube' | 'rumble' | 'podcast';
  channel_id: string;
  channel_url: string;
  name: string;
  description: string | null;
  avatar_url: string | null;
  subscriber_count: number | null;
  video_count: number | null;
}

export interface ChannelSearchResponse {
  query: string;
  platform: string;
  results: ChannelSearchResult[];
  total: number;
}

export interface FeedStats {
  total_videos: number;
  unwatched_videos: number;
  watched_videos: number;
  total_channels: number;
  by_platform: Record<string, number>;
}

// Discover (Federated Search) types
export interface PlatformInfo {
  id: string;
  name: string;
  icon: string;
  color: string;
  supports_search: boolean;
  supports_channel_feed: boolean;
  supports_playlists: boolean;
}

export interface DiscoverVideoResult {
  platform: string;
  video_id: string;
  video_url: string;
  title: string;
  description: string | null;
  thumbnail_url: string | null;
  duration_seconds: number | null;
  view_count: number | null;
  upload_date: string | null;
  channel_name: string | null;
  channel_id: string | null;
  channel_url: string | null;
  channel_avatar_url: string | null;
  like_count: number | null;
  tags: string[];
}

export interface DiscoverChannelResult {
  platform: string;
  channel_id: string;
  channel_url: string;
  name: string;
  description: string | null;
  avatar_url: string | null;
  banner_url: string | null;
  subscriber_count: number | null;
  video_count: number | null;
}

export interface DiscoverPlaylistResult {
  platform: string;
  playlist_id: string;
  playlist_url: string;
  name: string;
  description: string | null;
  thumbnail_url: string | null;
  video_count: number | null;
  channel_name: string | null;
  channel_url: string | null;
}

export interface SearchTiming {
  platform: string;
  duration_ms: number;
  success: boolean;
  error: string | null;
}

export interface DiscoverSearchResponse<T> {
  query: string;
  search_type: string;
  total_results: number;
  results: T[];
  by_platform: Record<string, T[]>;
  timings: SearchTiming[];
  total_duration_ms: number;
  platforms_searched: string[];
  platforms_failed: string[];
}

export interface QuickSaveResponse {
  type: 'video' | 'channel' | 'playlist';
  platform: string;
  saved: DiscoverVideoResult | DiscoverChannelResult | DiscoverPlaylistResult;
  message: string;
}

// Saved Videos types
export interface SavedVideo {
  id: number;
  platform: string;
  video_id: string;
  video_url: string;
  title: string;
  description: string | null;
  thumbnail_url: string | null;
  duration_seconds: number | null;
  view_count: number | null;
  upload_date: string | null;
  channel_name: string | null;
  channel_id: string | null;
  channel_url: string | null;
  is_watched: boolean;
  watched_at: string | null;
  watch_progress_seconds: number | null;
  notes: string | null;
  saved_at: string;
  updated_at: string;
  duration_formatted: string;
}

export interface SavedVideoCreate {
  platform: string;
  video_id: string;
  video_url: string;
  title: string;
  description?: string | null;
  thumbnail_url?: string | null;
  duration_seconds?: number | null;
  view_count?: number | null;
  upload_date?: string | null;
  channel_name?: string | null;
  channel_id?: string | null;
  channel_url?: string | null;
  notes?: string | null;
}

export interface SavedVideoListResponse {
  items: SavedVideo[];
  total: number;
}

export interface SavedVideoStats {
  total_videos: number;
  watched_videos: number;
  unwatched_videos: number;
  by_platform: Record<string, number>;
}

// Hidden Channel types
export interface HiddenChannel {
  id: number;
  platform: string;
  channel_id: string;
  channel_name: string;
  channel_avatar_url: string | null;
  hidden_at: string;
}

export interface HiddenChannelCreate {
  platform: string;
  channel_id: string;
  channel_name: string;
  channel_avatar_url?: string | null;
}

export interface HiddenChannelListResponse {
  items: HiddenChannel[];
  total: number;
}

// Watch State types for Discover
export interface VideoIdentifier {
  platform: string;
  video_id: string;
}

export interface WatchStateItem {
  platform: string;
  video_id: string;
  is_watched: boolean;
  is_partially_watched: boolean;
  watch_progress_seconds: number | null;
  duration_seconds: number | null;
}

export interface WatchStateCheckResponse {
  states: WatchStateItem[];
}

// Playlist types
export interface FollowedPlaylist {
  id: number;
  platform: string;
  playlist_id: string;
  playlist_url: string;
  name: string;
  description: string | null;
  thumbnail_url: string | null;
  video_count: number | null;
  channel_name: string | null;
  channel_url: string | null;
  is_active: boolean;
  last_synced_at: string | null;
  last_sync_error: string | null;
  consecutive_errors: number;
  created_at: string;
  updated_at: string;
  display_name: string;
}

export interface PlaylistListResponse {
  items: FollowedPlaylist[];
  total: number;
}

export interface PlaylistSyncResult {
  playlist_id: number;
  playlist_name: string;
  success: boolean;
  new_videos: number;
  error: string | null;
}

// Platform Account types
export interface PlatformAccount {
  id: number;
  platform: string;
  account_email: string;
  account_name: string;
  is_active: boolean;
  is_premium: boolean;
  scopes: string | null;
  token_expires_at: string | null;
  last_used_at: string | null;
  last_error: string | null;
  created_at: string;
}

export interface OAuthConfigStatus {
  youtube: boolean;
}

export interface ImportSubscriptionsResult {
  imported: number;
  skipped: number;
  failed: number;
  total_found: number;
}

// Red Bar Radio auth types
export interface RedBarLoginResponse {
  success: boolean;
  message: string;
  account_id?: number;
  username?: string;
}

export interface RedBarStatusResponse {
  logged_in: boolean;
  username?: string;
  expires_at?: string;
  is_premium?: boolean;
  last_used?: string;
  error?: string;
}

// Settings types
export interface SettingValue<T = unknown> {
  value: T;
  source: 'env' | 'db' | 'default';
  editable: boolean;
}

export interface CrawlerSettings {
  user_agent: SettingValue<string>;
  concurrent_requests: SettingValue<number>;
  request_delay_ms: SettingValue<number>;
  timeout_seconds: SettingValue<number>;
  max_retries: SettingValue<number>;
  respect_robots_txt: SettingValue<boolean>;
  max_pages_per_source: SettingValue<number>;
  max_page_size_mb: SettingValue<number>;
  raw_html_enabled: SettingValue<boolean>;
  image_embeddings_enabled: SettingValue<boolean>;
  youtube_fetch_transcripts: SettingValue<boolean>;
  youtube_transcript_languages: SettingValue<string[]>;
  youtube_max_videos_per_source: SettingValue<number>;
  youtube_rate_limit_delay_ms: SettingValue<number>;
}

export interface CrawlerSettingsUpdate {
  user_agent?: string;
  concurrent_requests?: number;
  request_delay_ms?: number;
  timeout_seconds?: number;
  max_retries?: number;
  respect_robots_txt?: boolean;
  max_pages_per_source?: number;
}

export interface AppSettings {
  app_name: string;
  debug: boolean;
  data_dir: string;
  crawler: CrawlerSettings;
  meilisearch: {
    host: string;
    index_prefix: string;
  };
}

export interface ApiKey {
  provider: string;
  masked_key: string;
  is_active: boolean;
  daily_limit: number | null;
  daily_usage: number;
  remaining_quota: number | null;
}

export interface ApiKeyCreate {
  provider: string;
  api_key: string;
  extra_config?: string | null;
  daily_limit?: number | null;
}

export interface SettingsUpdateResponse {
  success: boolean;
  message: string;
  settings: CrawlerSettings;
}

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE) {
    this.baseUrl = baseUrl;
  }

  private getAuthHeaders(): Record<string, string> {
    // Get auth token from localStorage for authenticated requests
    if (typeof window !== 'undefined') {
      const token = localStorage.getItem('session_token');
      if (token) {
        return { 'Authorization': `Bearer ${token}` };
      }
    }
    return {};
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`;
    const response = await fetch(url, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...this.getAuthHeaders(),
        ...options.headers,
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || `HTTP ${response.status}`);
    }

    if (response.status === 204) {
      return undefined as T;
    }

    return response.json();
  }

  // Health check
  async healthCheck(): Promise<{ status: string; version: string }> {
    return this.request('/health'.replace('/api', ''));
  }

  // Indexes
  async listIndexes(): Promise<{ items: Index[]; total: number }> {
    return this.request('/indexes');
  }

  async getIndex(id: number): Promise<Index> {
    return this.request(`/indexes/${id}`);
  }

  async createIndex(data: {
    name: string;
    description?: string;
    ranking_config?: Partial<RankingConfig>;
  }): Promise<Index> {
    return this.request('/indexes', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateIndex(
    id: number,
    data: Partial<{
      name: string;
      description: string;
      ranking_config: Partial<RankingConfig>;
      is_active: boolean;
    }>
  ): Promise<Index> {
    return this.request(`/indexes/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deleteIndex(id: number): Promise<void> {
    return this.request(`/indexes/${id}`, { method: 'DELETE' });
  }

  // Sources
  async listSources(indexId: number): Promise<Source[]> {
    return this.request(`/sources/by-index/${indexId}`);
  }

  async getSource(id: number): Promise<Source> {
    return this.request(`/sources/${id}`);
  }

  async createSource(
    indexId: number,
    data: {
      url: string;
      source_type?: 'domain' | 'url' | 'sitemap';
      name?: string;
      crawl_depth?: number;
      crawl_frequency?: 'hourly' | 'daily' | 'weekly' | 'monthly';
      crawl_mode?: 'text_only' | 'images_only' | 'videos_only' | 'text_images' | 'text_videos' | 'images_videos' | 'all';
      max_pages?: number;
      include_patterns?: string[];
      exclude_patterns?: string[];
      respect_robots?: boolean;
      use_tor?: boolean;
    }
  ): Promise<Source> {
    return this.request(`/sources/by-index/${indexId}`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async updateSource(
    id: number,
    data: Partial<Source>
  ): Promise<Source> {
    return this.request(`/sources/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deleteSource(id: number): Promise<void> {
    return this.request(`/sources/${id}`, { method: 'DELETE' });
  }

  // Search
  async search(params: {
    query: string;
    indexes?: string[];
    external_apis?: string[];
    sort?: 'relevance' | 'date';
    page?: number;
    per_page?: number;
  }): Promise<SearchResponse> {
    return this.request('/search', {
      method: 'POST',
      body: JSON.stringify(params),
    });
  }

  // Image Search
  async searchImages(params: {
    query: string;
    indexes?: string[];
    page?: number;
    per_page?: number;
  }): Promise<ImageSearchResponse> {
    return this.request('/search/images', {
      method: 'POST',
      body: JSON.stringify(params),
    });
  }

  async getImageSearchStatus(): Promise<ImageSearchStatus> {
    return this.request('/search/images/status');
  }

  // Video Search
  async searchVideos(params: {
    query: string;
    indexes?: string[];
    page?: number;
    per_page?: number;
  }): Promise<VideoSearchResponse> {
    return this.request('/search/videos', {
      method: 'POST',
      body: JSON.stringify(params),
    });
  }

  // Crawl
  async startCrawl(sourceIds: number[]): Promise<{
    status: string;
    jobs: Array<{ id: number; source_id: number }>;
    message: string;
  }> {
    return this.request('/crawl/start', {
      method: 'POST',
      body: JSON.stringify(sourceIds),
    });
  }

  async getCrawlStatus(status?: string, limit?: number): Promise<{
    jobs: CrawlJob[];
    total: number;
    active_count: number;
  }> {
    const params = new URLSearchParams();
    if (status) params.set('status', status);
    if (limit) params.set('limit', limit.toString());
    const query = params.toString();
    return this.request(`/crawl/status${query ? `?${query}` : ''}`);
  }

  async getCrawlJob(id: number): Promise<CrawlJob> {
    return this.request(`/crawl/jobs/${id}`);
  }

  async stopCrawl(jobIds?: number[]): Promise<{
    status: string;
    stopped: number[];
    not_running: number[];
    message: string;
  }> {
    return this.request('/crawl/stop', {
      method: 'POST',
      body: JSON.stringify(jobIds || null),
    });
  }

  async deleteCrawlJob(id: number): Promise<void> {
    return this.request(`/crawl/jobs/${id}`, { method: 'DELETE' });
  }

  // Settings
  async getSettings(): Promise<AppSettings> {
    return this.request('/settings');
  }

  async getCrawlerSettings(): Promise<CrawlerSettings> {
    return this.request('/settings/crawler');
  }

  async updateCrawlerSettings(data: CrawlerSettingsUpdate): Promise<SettingsUpdateResponse> {
    return this.request('/settings/crawler', {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async resetCrawlerSetting(key: string): Promise<SettingsUpdateResponse> {
    return this.request(`/settings/crawler/${key}`, {
      method: 'DELETE',
    });
  }

  // API Keys
  async listApiKeys(): Promise<ApiKey[]> {
    return this.request('/settings/api-keys');
  }

  async createApiKey(data: ApiKeyCreate): Promise<ApiKey> {
    return this.request('/settings/api-keys', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async deleteApiKey(provider: string): Promise<void> {
    return this.request(`/settings/api-keys/${encodeURIComponent(provider)}`, {
      method: 'DELETE',
    });
  }

  // Collections
  async listCollections(): Promise<{ items: Collection[]; total: number }> {
    return this.request('/collections');
  }

  async createCollection(data: {
    name: string;
    description?: string;
  }): Promise<Collection> {
    return this.request('/collections', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async getCollection(id: number): Promise<CollectionWithItems> {
    return this.request(`/collections/${id}`);
  }

  async updateCollection(
    id: number,
    data: Partial<{
      name: string;
      description: string;
      sort_order: number;
    }>
  ): Promise<Collection> {
    return this.request(`/collections/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deleteCollection(id: number): Promise<void> {
    return this.request(`/collections/${id}`, { method: 'DELETE' });
  }

  async addItemToCollection(
    collectionId: number,
    data: CollectionItemCreate
  ): Promise<CollectionItem> {
    return this.request(`/collections/${collectionId}/items`, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async removeItemFromCollection(
    collectionId: number,
    itemId: number
  ): Promise<void> {
    return this.request(`/collections/${collectionId}/items/${itemId}`, {
      method: 'DELETE',
    });
  }

  async reorderCollectionItems(
    collectionId: number,
    itemIds: number[]
  ): Promise<void> {
    return this.request(`/collections/${collectionId}/items/reorder`, {
      method: 'POST',
      body: JSON.stringify({ item_ids: itemIds }),
    });
  }

  async quickAddToFavorites(data: CollectionItemCreate): Promise<CollectionItem> {
    return this.request('/collections/quick-add', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async exportCollection(id: number): Promise<Blob> {
    const url = `${this.baseUrl}/collections/export/${id}`;
    const response = await fetch(url);
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}`);
    }
    return response.blob();
  }

  // Channels (Video Subscriptions)
  async listChannels(params?: {
    platform?: 'youtube' | 'rumble' | 'podcast';
    is_active?: boolean;
  }): Promise<{ items: Channel[]; total: number }> {
    const searchParams = new URLSearchParams();
    if (params?.platform) searchParams.set('platform', params.platform);
    if (params?.is_active !== undefined) searchParams.set('is_active', String(params.is_active));
    const query = searchParams.toString();
    return this.request(`/channels${query ? `?${query}` : ''}`);
  }

  async searchChannels(params: {
    query: string;
    platform?: 'youtube' | 'rumble' | 'podcast';
    limit?: number;
  }): Promise<ChannelSearchResponse> {
    const searchParams = new URLSearchParams();
    searchParams.set('query', params.query);
    if (params.platform) searchParams.set('platform', params.platform);
    if (params.limit) searchParams.set('limit', String(params.limit));
    return this.request(`/channels/search?${searchParams.toString()}`);
  }

  async addChannel(url: string): Promise<Channel> {
    return this.request('/channels', {
      method: 'POST',
      body: JSON.stringify({ channel_url: url }),
    });
  }

  async getChannel(id: number): Promise<Channel> {
    return this.request(`/channels/${id}`);
  }

  async updateChannel(
    id: number,
    data: Partial<{ is_active: boolean }>
  ): Promise<Channel> {
    return this.request(`/channels/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async deleteChannel(id: number): Promise<void> {
    return this.request(`/channels/${id}`, { method: 'DELETE' });
  }

  async syncChannel(id: number): Promise<SyncResult> {
    return this.request(`/channels/${id}/sync`, { method: 'POST' });
  }

  async importChannelsFromUrls(urls: string[]): Promise<ImportResult> {
    return this.request('/channels/import/urls', {
      method: 'POST',
      body: JSON.stringify({ urls }),
    });
  }

  async importChannelsFromTakeout(subscriptions: Array<{
    snippet: {
      resourceId: { channelId: string };
      title: string;
    };
  }>): Promise<ImportResult> {
    return this.request('/channels/import/takeout', {
      method: 'POST',
      body: JSON.stringify({ subscriptions }),
    });
  }

  // Feed (Video Feed)
  async getFeed(params?: {
    filter?: 'all' | 'unwatched' | 'watched';
    platform?: 'youtube' | 'rumble' | 'podcast';
    channel_id?: number;
    page?: number;
    per_page?: number;
    // New feed mode parameters
    mode?: FeedMode;
    sort_by?: 'newest' | 'oldest' | 'views' | 'duration_asc' | 'duration_desc' | 'random';
    category?: string;
    duration_min?: number;
    duration_max?: number;
  }): Promise<FeedResponse> {
    const searchParams = new URLSearchParams();
    if (params?.filter) searchParams.set('filter', params.filter);
    if (params?.platform) searchParams.set('platform', params.platform);
    if (params?.channel_id) searchParams.set('channel_ids', String(params.channel_id));
    if (params?.page) searchParams.set('page', String(params.page));
    if (params?.per_page) searchParams.set('per_page', String(params.per_page));
    // New feed mode parameters
    if (params?.mode) searchParams.set('mode', params.mode);
    if (params?.sort_by) searchParams.set('sort_by', params.sort_by);
    if (params?.category) searchParams.set('category', params.category);
    if (params?.duration_min) searchParams.set('duration_min', String(params.duration_min));
    if (params?.duration_max) searchParams.set('duration_max', String(params.duration_max));
    const query = searchParams.toString();
    return this.request(`/feed${query ? `?${query}` : ''}`);
  }

  async getFeedByChannel(params?: {
    filter?: 'all' | 'unwatched' | 'watched';
    platform?: 'youtube' | 'rumble' | 'podcast';
  }): Promise<{ channels: ChannelGroupedFeed[]; total_channels: number; total_items: number }> {
    const searchParams = new URLSearchParams();
    if (params?.filter) searchParams.set('filter', params.filter);
    if (params?.platform) searchParams.set('platform', params.platform);
    const query = searchParams.toString();
    return this.request(`/feed/by-channel${query ? `?${query}` : ''}`);
  }

  async markFeedItemWatched(id: number, progress_seconds?: number): Promise<FeedItem> {
    return this.request(`/feed/items/${id}/watched`, {
      method: 'PUT',
      body: JSON.stringify({ progress_seconds }),
    });
  }

  async markFeedItemUnwatched(id: number): Promise<FeedItem> {
    return this.request(`/feed/items/${id}/unwatched`, { method: 'PUT' });
  }

  async updateFeedItemProgress(id: number, progressSeconds: number): Promise<FeedItem> {
    return this.request(`/feed/items/${id}/progress?progress_seconds=${progressSeconds}`, { method: 'PUT' });
  }

  async getFeedItem(id: number): Promise<FeedItem> {
    return this.request(`/feed/items/${id}`);
  }

  async syncAllFeeds(): Promise<SyncResult[]> {
    return this.request('/feed/sync', { method: 'POST' });
  }

  async getFeedStats(): Promise<FeedStats> {
    return this.request('/feed/stats');
  }

  async fixFeedMetadata(limit: number = 100): Promise<{ status: string; message: string }> {
    return this.request(`/feed/fix-metadata?limit=${limit}`, { method: 'POST' });
  }

  async getWatchHistory(params?: {
    page?: number;
    per_page?: number;
    include_completed?: boolean;
  }): Promise<FeedResponse> {
    const searchParams = new URLSearchParams();
    if (params?.page) searchParams.set('page', params.page.toString());
    if (params?.per_page) searchParams.set('per_page', params.per_page.toString());
    if (params?.include_completed !== undefined) {
      searchParams.set('include_completed', params.include_completed.toString());
    }
    const query = searchParams.toString();
    return this.request(`/feed/history${query ? `?${query}` : ''}`);
  }

  // Discover (Federated Search)
  async listPlatforms(): Promise<{ platforms: PlatformInfo[]; total: number }> {
    return this.request('/discover/platforms');
  }

  async discoverVideos(params: {
    query: string;
    platforms?: string[];
    max_per_platform?: number;
  }): Promise<DiscoverSearchResponse<DiscoverVideoResult>> {
    return this.request('/discover/search', {
      method: 'POST',
      body: JSON.stringify({
        query: params.query,
        platforms: params.platforms,
        type: 'videos',
        max_per_platform: params.max_per_platform || 10,
      }),
    });
  }

  async discoverChannels(params: {
    query: string;
    platforms?: string[];
    max_per_platform?: number;
  }): Promise<DiscoverSearchResponse<DiscoverChannelResult>> {
    return this.request('/discover/search', {
      method: 'POST',
      body: JSON.stringify({
        query: params.query,
        platforms: params.platforms,
        type: 'channels',
        max_per_platform: params.max_per_platform || 10,
      }),
    });
  }

  async discoverPlaylists(params: {
    query: string;
    platforms?: string[];
    max_per_platform?: number;
  }): Promise<DiscoverSearchResponse<DiscoverPlaylistResult>> {
    return this.request('/discover/search', {
      method: 'POST',
      body: JSON.stringify({
        query: params.query,
        platforms: params.platforms,
        type: 'playlists',
        max_per_platform: params.max_per_platform || 10,
      }),
    });
  }

  async quickSave(url: string): Promise<QuickSaveResponse> {
    return this.request('/discover/quick-save', {
      method: 'POST',
      body: JSON.stringify({ url }),
    });
  }

  // Saved Videos
  async listSavedVideos(params?: {
    platform?: string;
    is_watched?: boolean;
    limit?: number;
    offset?: number;
  }): Promise<SavedVideoListResponse> {
    const searchParams = new URLSearchParams();
    if (params?.platform) searchParams.set('platform', params.platform);
    if (params?.is_watched !== undefined) searchParams.set('is_watched', String(params.is_watched));
    if (params?.limit) searchParams.set('limit', String(params.limit));
    if (params?.offset) searchParams.set('offset', String(params.offset));
    const query = searchParams.toString();
    return this.request(`/saved-videos${query ? `?${query}` : ''}`);
  }

  async getSavedVideoStats(): Promise<SavedVideoStats> {
    return this.request('/saved-videos/stats');
  }

  async saveVideo(data: SavedVideoCreate): Promise<SavedVideo> {
    return this.request('/saved-videos', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async saveVideoFromUrl(url: string, notes?: string): Promise<SavedVideo> {
    return this.request('/saved-videos/from-url', {
      method: 'POST',
      body: JSON.stringify({ url, notes }),
    });
  }

  async checkIfVideoSaved(platform: string, videoId: string): Promise<{ is_saved: boolean }> {
    return this.request(`/saved-videos/check?platform=${encodeURIComponent(platform)}&video_id=${encodeURIComponent(videoId)}`);
  }

  async getSavedVideo(id: number): Promise<SavedVideo> {
    return this.request(`/saved-videos/${id}`);
  }

  async updateSavedVideo(id: number, data: Partial<{ notes: string; is_watched: boolean; watch_progress_seconds: number }>): Promise<SavedVideo> {
    return this.request(`/saved-videos/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async markSavedVideoWatched(id: number, progressSeconds?: number): Promise<SavedVideo> {
    const params = progressSeconds ? `?progress_seconds=${progressSeconds}` : '';
    return this.request(`/saved-videos/${id}/watched${params}`, { method: 'PUT' });
  }

  async markSavedVideoUnwatched(id: number): Promise<SavedVideo> {
    return this.request(`/saved-videos/${id}/unwatched`, { method: 'PUT' });
  }

  async updateSavedVideoProgress(id: number, progressSeconds: number): Promise<SavedVideo> {
    return this.request(`/saved-videos/${id}/progress?progress_seconds=${progressSeconds}`, { method: 'PUT' });
  }

  async deleteSavedVideo(id: number): Promise<void> {
    return this.request(`/saved-videos/${id}`, { method: 'DELETE' });
  }

  // Playlists
  async listPlaylists(params?: {
    platform?: string;
    is_active?: boolean;
  }): Promise<PlaylistListResponse> {
    const searchParams = new URLSearchParams();
    if (params?.platform) searchParams.set('platform', params.platform);
    if (params?.is_active !== undefined) searchParams.set('is_active', String(params.is_active));
    const query = searchParams.toString();
    return this.request(`/playlists${query ? `?${query}` : ''}`);
  }

  async followPlaylist(data: {
    platform: string;
    playlist_id: string;
    playlist_url: string;
    name: string;
    description?: string | null;
    thumbnail_url?: string | null;
    video_count?: number | null;
    channel_name?: string | null;
    channel_url?: string | null;
  }): Promise<FollowedPlaylist> {
    return this.request('/playlists', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async followPlaylistFromUrl(url: string): Promise<FollowedPlaylist> {
    return this.request('/playlists/from-url', {
      method: 'POST',
      body: JSON.stringify({ url }),
    });
  }

  async getPlaylist(id: number): Promise<FollowedPlaylist> {
    return this.request(`/playlists/${id}`);
  }

  async updatePlaylist(id: number, data: Partial<{ name: string; is_active: boolean }>): Promise<FollowedPlaylist> {
    return this.request(`/playlists/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  async syncPlaylist(id: number): Promise<PlaylistSyncResult> {
    return this.request(`/playlists/${id}/sync`, { method: 'POST' });
  }

  async unfollowPlaylist(id: number): Promise<void> {
    return this.request(`/playlists/${id}`, { method: 'DELETE' });
  }

  // Platform Accounts (OAuth)
  async listAccounts(): Promise<PlatformAccount[]> {
    return this.request('/accounts');
  }

  async getOAuthConfigStatus(): Promise<OAuthConfigStatus> {
    return this.request('/accounts/config-status');
  }

  async importSubscriptionsFromAccount(accountId: number): Promise<ImportSubscriptionsResult> {
    return this.request(`/accounts/${accountId}/import-subscriptions`, { method: 'POST' });
  }

  // Red Bar Radio (session-based auth)
  async redbarLogin(username: string, password: string): Promise<RedBarLoginResponse> {
    return this.request('/accounts/redbar/login', {
      method: 'POST',
      body: JSON.stringify({ username, password }),
    });
  }

  async getRedbarStatus(): Promise<RedBarStatusResponse> {
    return this.request('/accounts/redbar/status');
  }

  async redbarLogout(): Promise<{ success: boolean; message: string }> {
    return this.request('/accounts/redbar', { method: 'DELETE' });
  }

  async validateRedbarSession(): Promise<{ valid: boolean }> {
    return this.request('/accounts/redbar/validate', { method: 'POST' });
  }

  // Hidden Channels
  async listHiddenChannels(): Promise<HiddenChannelListResponse> {
    return this.request('/hidden-channels');
  }

  async hideChannel(data: HiddenChannelCreate): Promise<HiddenChannel> {
    return this.request('/hidden-channels', {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  async unhideChannel(platform: string, channelId: string): Promise<void> {
    return this.request(`/hidden-channels/${encodeURIComponent(platform)}/${encodeURIComponent(channelId)}`, {
      method: 'DELETE',
    });
  }

  // Watch States (for Discover filtering)
  async checkWatchStates(videos: VideoIdentifier[]): Promise<WatchStateCheckResponse> {
    return this.request('/discover/watch-states', {
      method: 'POST',
      body: JSON.stringify({ videos }),
    });
  }
}

export const api = new ApiClient();
