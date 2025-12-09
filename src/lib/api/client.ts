/**
 * API client for communicating with the Python backend.
 */

const API_BASE = 'http://localhost:8000/api';

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
  max_pages: number;
  include_patterns: string[];
  exclude_patterns: string[];
  respect_robots: boolean;
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
      max_pages?: number;
      include_patterns?: string[];
      exclude_patterns?: string[];
      respect_robots?: boolean;
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
}

export const api = new ApiClient();
