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
  platform: 'youtube' | 'rumble';
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
  platform: 'youtube' | 'rumble';
  video_id: string;
  video_url: string;
  title: string;
  description: string | null;
  thumbnail_url: string | null;
  duration_seconds: number | null;
  view_count: number | null;
  upload_date: string;
  is_watched: boolean;
  watched_at: string | null;
  watch_progress_seconds: number | null;
  discovered_at: string;
  duration_formatted: string;
  is_recent: boolean;
  channel_name: string;
  channel_avatar_url: string | null;
}

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
  platform: 'youtube' | 'rumble';
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

class ApiClient {
  private baseUrl: string;

  constructor(baseUrl: string = API_BASE) {
    this.baseUrl = baseUrl;
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
  async getSettings(): Promise<Record<string, unknown>> {
    return this.request('/settings');
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
    platform?: 'youtube' | 'rumble';
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
    platform?: 'youtube' | 'rumble';
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
      body: JSON.stringify({ url }),
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
    platform?: 'youtube' | 'rumble';
    channel_id?: number;
    page?: number;
    per_page?: number;
  }): Promise<FeedResponse> {
    const searchParams = new URLSearchParams();
    if (params?.filter) searchParams.set('filter', params.filter);
    if (params?.platform) searchParams.set('platform', params.platform);
    if (params?.channel_id) searchParams.set('channel_ids', String(params.channel_id));
    if (params?.page) searchParams.set('page', String(params.page));
    if (params?.per_page) searchParams.set('per_page', String(params.per_page));
    const query = searchParams.toString();
    return this.request(`/feed${query ? `?${query}` : ''}`);
  }

  async getFeedByChannel(params?: {
    filter?: 'all' | 'unwatched' | 'watched';
    platform?: 'youtube' | 'rumble';
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

  async syncAllFeeds(): Promise<SyncResult[]> {
    return this.request('/feed/sync', { method: 'POST' });
  }

  async getFeedStats(): Promise<FeedStats> {
    return this.request('/feed/stats');
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
}

export const api = new ApiClient();
