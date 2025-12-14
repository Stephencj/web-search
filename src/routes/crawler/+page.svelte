<script lang="ts">
  import { api, type SearchResponse, type SearchResult, type CrawlJob, type Index, type Source } from '$lib/api/client';
  import { onMount } from 'svelte';

  type Tab = 'search' | 'crawl' | 'indexes';
  let activeTab = $state<Tab>('search');

  // Search state
  let query = $state('');
  let results = $state<SearchResult[]>([]);
  let totalResults = $state(0);
  let searching = $state(false);
  let searchError = $state<string | null>(null);
  let timing = $state({ local_ms: 0, external_ms: 0, total_ms: 0 });
  let availableIndexes = $state<Index[]>([]);
  let selectedIndex = $state<string>('');

  // Crawl status state
  let jobs = $state<CrawlJob[]>([]);
  let loadingJobs = $state(false);
  let crawlError = $state<string | null>(null);
  let activeCount = $state(0);

  // Indexes state
  let indexes = $state<Index[]>([]);
  let loadingIndexes = $state(false);
  let indexError = $state<string | null>(null);

  onMount(() => {
    loadIndexes();
    loadJobs();
    // Auto-refresh crawl jobs every 5 seconds if there are active jobs
    const interval = setInterval(() => {
      if (activeCount > 0) {
        loadJobs();
      }
    }, 5000);
    return () => clearInterval(interval);
  });

  // Search functions
  async function handleSearch() {
    if (!query.trim()) return;
    searching = true;
    searchError = null;
    try {
      const response = await api.search({
        query: query.trim(),
        page: 1,
        per_page: 50,
        index: selectedIndex || undefined,
      });
      results = response.results;
      totalResults = response.total_results;
      timing = response.timing;
    } catch (e) {
      searchError = e instanceof Error ? e.message : 'Search failed';
      results = [];
    } finally {
      searching = false;
    }
  }

  function handleKeydown(event: KeyboardEvent) {
    if (event.key === 'Enter') {
      handleSearch();
    }
  }

  // Crawl functions
  async function loadJobs() {
    loadingJobs = true;
    crawlError = null;
    try {
      const response = await api.getCrawlStatus(undefined, 50);
      jobs = response.jobs;
      activeCount = response.active_count || 0;
    } catch (e) {
      crawlError = e instanceof Error ? e.message : 'Failed to load crawl status';
    } finally {
      loadingJobs = false;
    }
  }

  async function stopJob(jobId: number) {
    try {
      await api.stopCrawl([jobId]);
      await loadJobs();
    } catch (e) {
      crawlError = e instanceof Error ? e.message : 'Failed to stop crawl';
    }
  }

  async function stopAllJobs() {
    try {
      await api.stopCrawl();
      await loadJobs();
    } catch (e) {
      crawlError = e instanceof Error ? e.message : 'Failed to stop crawls';
    }
  }

  // Index functions
  async function loadIndexes() {
    loadingIndexes = true;
    indexError = null;
    try {
      const response = await api.listIndexes();
      indexes = response.items;
      availableIndexes = response.items;
    } catch (e) {
      indexError = e instanceof Error ? e.message : 'Failed to load indexes';
    } finally {
      loadingIndexes = false;
    }
  }

  async function deleteIndex(id: number) {
    if (!confirm('Delete this index and all its sources?')) return;
    try {
      await api.deleteIndex(id);
      indexes = indexes.filter(i => i.id !== id);
    } catch (e) {
      indexError = e instanceof Error ? e.message : 'Failed to delete index';
    }
  }

  function getStatusColor(status: string): string {
    switch (status) {
      case 'completed': return 'var(--color-success)';
      case 'running': return 'var(--color-warning)';
      case 'failed': return 'var(--color-error)';
      case 'cancelled': return 'var(--color-text-secondary)';
      case 'pending': return 'var(--color-primary)';
      default: return 'var(--color-text-secondary)';
    }
  }

  function formatDate(dateStr: string | null): string {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleString();
  }

  function isRunning(job: CrawlJob): boolean {
    return job.status === 'running' || job.status === 'pending';
  }
</script>

<div class="crawler-page">
  <header class="page-header">
    <h1>Web Crawler</h1>
    <p class="subtitle">Search, crawl, and manage your indexed content</p>
  </header>

  <!-- Tab Navigation -->
  <div class="tabs">
    <button
      class="tab"
      class:active={activeTab === 'search'}
      onclick={() => activeTab = 'search'}
    >
      🔍 Search
    </button>
    <button
      class="tab"
      class:active={activeTab === 'crawl'}
      onclick={() => activeTab = 'crawl'}
    >
      🔄 Crawl Status
      {#if activeCount > 0}
        <span class="tab-badge">{activeCount}</span>
      {/if}
    </button>
    <button
      class="tab"
      class:active={activeTab === 'indexes'}
      onclick={() => activeTab = 'indexes'}
    >
      📚 Indexes
    </button>
  </div>

  <!-- Tab Content -->
  <div class="tab-content">
    {#if activeTab === 'search'}
      <!-- Search Tab -->
      <div class="search-section">
        <div class="search-bar">
          <input
            type="text"
            bind:value={query}
            onkeydown={handleKeydown}
            placeholder="Search your indexed content..."
            class="search-input"
          />
          {#if availableIndexes.length > 1}
            <select bind:value={selectedIndex} class="index-select">
              <option value="">All Indexes</option>
              {#each availableIndexes as index}
                <option value={index.slug}>{index.name}</option>
              {/each}
            </select>
          {/if}
          <button
            onclick={handleSearch}
            disabled={searching || !query.trim()}
            class="search-btn"
          >
            {searching ? 'Searching...' : 'Search'}
          </button>
        </div>

        {#if searchError}
          <div class="error">{searchError}</div>
        {/if}

        {#if results.length > 0}
          <div class="results-info">
            Found {totalResults} results ({timing.total_ms}ms)
          </div>
          <div class="results">
            {#each results as result}
              <div class="result-card">
                <a href={result.url} target="_blank" rel="noopener" class="result-title">
                  {result.title || 'Untitled'}
                </a>
                <div class="result-url">{result.url}</div>
                {#if result.snippet}
                  <p class="result-snippet">{result.snippet}</p>
                {/if}
                <div class="result-meta">
                  <span class="result-domain">{result.domain}</span>
                  {#if result.published_at}
                    <span>{formatDate(result.published_at)}</span>
                  {/if}
                </div>
              </div>
            {/each}
          </div>
        {:else if query && !searching}
          <div class="empty-state">
            <p>No results found for "{query}"</p>
            <p class="hint">Try different keywords or check that content has been crawled</p>
          </div>
        {:else if !query}
          <div class="empty-state">
            <p>Search your locally crawled and indexed content</p>
            <p class="hint">Enter a search query above</p>
          </div>
        {/if}
      </div>

    {:else if activeTab === 'crawl'}
      <!-- Crawl Status Tab -->
      <div class="crawl-section">
        <div class="crawl-header">
          <button onclick={loadJobs} class="btn btn-secondary" disabled={loadingJobs}>
            {loadingJobs ? 'Loading...' : 'Refresh'}
          </button>
          {#if activeCount > 0}
            <button onclick={stopAllJobs} class="btn btn-danger">
              Stop All
            </button>
          {/if}
        </div>

        {#if crawlError}
          <div class="error">{crawlError}</div>
        {/if}

        {#if jobs.length > 0}
          <div class="jobs-list">
            {#each jobs as job}
              <div class="job-card">
                <div class="job-header">
                  <span class="job-status" style="color: {getStatusColor(job.status)}">
                    {job.status.toUpperCase()}
                  </span>
                  <span class="job-source">{job.source_url}</span>
                </div>
                <div class="job-stats">
                  <span>Pages: {job.pages_crawled}/{job.total_pages || '?'}</span>
                  <span>Errors: {job.error_count}</span>
                  <span>Started: {formatDate(job.started_at)}</span>
                </div>
                {#if job.last_error}
                  <div class="job-error">{job.last_error}</div>
                {/if}
                {#if isRunning(job)}
                  <button onclick={() => stopJob(job.id)} class="btn btn-small btn-danger">
                    Stop
                  </button>
                {/if}
              </div>
            {/each}
          </div>
        {:else if !loadingJobs}
          <div class="empty-state">
            <p>No crawl jobs found</p>
            <p class="hint">Start a crawl from the Indexes tab</p>
          </div>
        {/if}
      </div>

    {:else if activeTab === 'indexes'}
      <!-- Indexes Tab -->
      <div class="indexes-section">
        <div class="indexes-header">
          <a href="/indexes" class="btn btn-primary">Manage Indexes</a>
        </div>

        {#if indexError}
          <div class="error">{indexError}</div>
        {/if}

        {#if indexes.length > 0}
          <div class="indexes-grid">
            {#each indexes as index}
              <div class="index-card">
                <h3>{index.name}</h3>
                {#if index.description}
                  <p class="index-desc">{index.description}</p>
                {/if}
                <div class="index-stats">
                  <span>{index.source_count} sources</span>
                  <span>{index.document_count} documents</span>
                </div>
                <div class="index-actions">
                  <a href="/indexes/{index.id}" class="btn btn-small btn-secondary">View</a>
                </div>
              </div>
            {/each}
          </div>
        {:else if !loadingIndexes}
          <div class="empty-state">
            <p>No indexes created yet</p>
            <p class="hint">Create an index to start crawling content</p>
            <a href="/indexes" class="btn btn-primary">Create Index</a>
          </div>
        {/if}
      </div>
    {/if}
  </div>
</div>

<style>
  .crawler-page {
    max-width: 1200px;
    margin: 0 auto;
  }

  .page-header {
    margin-bottom: var(--spacing-lg);
  }

  .page-header h1 {
    margin: 0 0 var(--spacing-xs);
    font-size: 2rem;
  }

  .subtitle {
    color: var(--color-text-secondary);
    margin: 0;
  }

  /* Tabs */
  .tabs {
    display: flex;
    gap: var(--spacing-xs);
    border-bottom: 1px solid var(--color-border);
    margin-bottom: var(--spacing-lg);
  }

  .tab {
    padding: var(--spacing-sm) var(--spacing-lg);
    background: none;
    border: none;
    border-bottom: 2px solid transparent;
    color: var(--color-text-secondary);
    font-size: 1rem;
    font-weight: 500;
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: var(--spacing-xs);
    transition: all 0.2s;
  }

  .tab:hover {
    color: var(--color-text);
  }

  .tab.active {
    color: var(--color-primary);
    border-bottom-color: var(--color-primary);
  }

  .tab-badge {
    background: var(--color-warning);
    color: white;
    padding: 2px 6px;
    border-radius: var(--radius-full);
    font-size: 0.75rem;
  }

  .tab-content {
    min-height: 400px;
  }

  /* Search */
  .search-bar {
    display: flex;
    gap: var(--spacing-sm);
    margin-bottom: var(--spacing-lg);
  }

  .search-input {
    flex: 1;
    padding: var(--spacing-md);
    font-size: 1rem;
    border: 2px solid var(--color-border);
    border-radius: var(--radius-md);
    background: var(--color-bg);
    color: var(--color-text);
  }

  .search-input:focus {
    outline: none;
    border-color: var(--color-primary);
  }

  .index-select {
    padding: var(--spacing-sm) var(--spacing-md);
    border: 2px solid var(--color-border);
    border-radius: var(--radius-md);
    background: var(--color-bg);
    color: var(--color-text);
  }

  .search-btn {
    padding: var(--spacing-md) var(--spacing-xl);
    background: var(--color-primary);
    color: white;
    border: none;
    border-radius: var(--radius-md);
    font-weight: 600;
    cursor: pointer;
  }

  .search-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .results-info {
    color: var(--color-text-secondary);
    margin-bottom: var(--spacing-md);
  }

  .results {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-md);
  }

  .result-card {
    padding: var(--spacing-md);
    background: var(--color-bg-secondary);
    border-radius: var(--radius-md);
  }

  .result-title {
    font-size: 1.1rem;
    font-weight: 500;
    color: var(--color-primary);
    text-decoration: none;
    display: block;
    margin-bottom: var(--spacing-xs);
  }

  .result-title:hover {
    text-decoration: underline;
  }

  .result-url {
    font-size: 0.85rem;
    color: var(--color-success);
    margin-bottom: var(--spacing-xs);
  }

  .result-snippet {
    color: var(--color-text-secondary);
    font-size: 0.9rem;
    margin: var(--spacing-xs) 0;
  }

  .result-meta {
    display: flex;
    gap: var(--spacing-md);
    font-size: 0.8rem;
    color: var(--color-text-secondary);
  }

  .result-domain {
    font-weight: 500;
  }

  /* Crawl Status */
  .crawl-header, .indexes-header {
    display: flex;
    gap: var(--spacing-sm);
    margin-bottom: var(--spacing-lg);
  }

  .jobs-list {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-md);
  }

  .job-card {
    padding: var(--spacing-md);
    background: var(--color-bg-secondary);
    border-radius: var(--radius-md);
  }

  .job-header {
    display: flex;
    align-items: center;
    gap: var(--spacing-md);
    margin-bottom: var(--spacing-sm);
  }

  .job-status {
    font-weight: 600;
    font-size: 0.8rem;
  }

  .job-source {
    font-weight: 500;
    word-break: break-all;
  }

  .job-stats {
    display: flex;
    gap: var(--spacing-lg);
    font-size: 0.85rem;
    color: var(--color-text-secondary);
    margin-bottom: var(--spacing-sm);
  }

  .job-error {
    font-size: 0.85rem;
    color: var(--color-error);
    margin-bottom: var(--spacing-sm);
  }

  /* Indexes */
  .indexes-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: var(--spacing-md);
  }

  .index-card {
    padding: var(--spacing-md);
    background: var(--color-bg-secondary);
    border-radius: var(--radius-md);
  }

  .index-card h3 {
    margin: 0 0 var(--spacing-xs);
    font-size: 1.1rem;
  }

  .index-desc {
    color: var(--color-text-secondary);
    font-size: 0.9rem;
    margin: 0 0 var(--spacing-sm);
  }

  .index-stats {
    display: flex;
    gap: var(--spacing-md);
    font-size: 0.85rem;
    color: var(--color-text-secondary);
    margin-bottom: var(--spacing-sm);
  }

  .index-actions {
    display: flex;
    gap: var(--spacing-sm);
  }

  /* Shared */
  .error {
    padding: var(--spacing-md);
    background: rgba(239, 68, 68, 0.1);
    color: var(--color-error);
    border-radius: var(--radius-md);
    margin-bottom: var(--spacing-md);
  }

  .empty-state {
    text-align: center;
    padding: var(--spacing-xxl);
    color: var(--color-text-secondary);
  }

  .empty-state p {
    margin: 0 0 var(--spacing-sm);
  }

  .hint {
    font-size: 0.9rem;
    opacity: 0.7;
  }

  .btn {
    padding: var(--spacing-sm) var(--spacing-md);
    border: none;
    border-radius: var(--radius-md);
    font-weight: 500;
    cursor: pointer;
    text-decoration: none;
    display: inline-block;
  }

  .btn-primary {
    background: var(--color-primary);
    color: white;
  }

  .btn-secondary {
    background: var(--color-bg);
    color: var(--color-text);
    border: 1px solid var(--color-border);
  }

  .btn-danger {
    background: var(--color-error);
    color: white;
  }

  .btn-small {
    padding: var(--spacing-xs) var(--spacing-sm);
    font-size: 0.85rem;
  }

  .btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  @media (max-width: 768px) {
    .tabs {
      overflow-x: auto;
    }

    .search-bar {
      flex-direction: column;
    }

    .search-btn {
      width: 100%;
    }

    .index-select {
      width: 100%;
    }
  }
</style>
