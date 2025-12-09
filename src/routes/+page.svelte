<script lang="ts">
  import { api, type SearchResponse, type SearchResult } from '$lib/api/client';

  let query = $state('');
  let results = $state<SearchResult[]>([]);
  let totalResults = $state(0);
  let searching = $state(false);
  let searchError = $state<string | null>(null);
  let timing = $state({ local_ms: 0, external_ms: 0, total_ms: 0 });

  async function handleSearch(event: Event) {
    event.preventDefault();
    if (!query.trim()) return;

    searching = true;
    searchError = null;

    try {
      const response = await api.search({ query: query.trim() });
      results = response.results;
      totalResults = response.total_results;
      timing = response.timing;
    } catch (e) {
      searchError = e instanceof Error ? e.message : 'Search failed';
      results = [];
      totalResults = 0;
    } finally {
      searching = false;
    }
  }
</script>

<div class="search-page">
  <header class="search-header">
    <h1>Search</h1>
    <p class="subtitle">Search across your indexed sources and external APIs</p>
  </header>

  <form class="search-form" onsubmit={handleSearch}>
    <div class="search-input-wrapper">
      <input
        type="text"
        class="input input-lg search-input"
        placeholder="Enter your search query..."
        bind:value={query}
        disabled={searching}
      />
      <button type="submit" class="btn btn-primary search-btn" disabled={searching || !query.trim()}>
        {searching ? 'Searching...' : 'Search'}
      </button>
    </div>
  </form>

  {#if searchError}
    <div class="error-message">
      {searchError}
    </div>
  {/if}

  {#if results.length > 0}
    <div class="results-header">
      <span class="results-count">{totalResults} results</span>
      <span class="results-timing">({timing.total_ms}ms)</span>
    </div>

    <div class="results-list">
      {#each results as result}
        <article class="result-card card">
          <a href={result.url} target="_blank" class="result-title">
            {result.title}
          </a>
          <div class="result-url">{result.url}</div>
          <p class="result-snippet">{result.snippet}</p>
          <div class="result-meta">
            <span class="result-source">{result.source}</span>
            {#if result.index}
              <span class="result-index">{result.index}</span>
            {/if}
            <span class="result-domain">{result.domain}</span>
          </div>
        </article>
      {/each}
    </div>
  {:else if query && !searching && !searchError}
    <div class="no-results">
      <p>No results found for "{query}"</p>
      <p class="hint">Try different keywords or check your index sources</p>
    </div>
  {:else if !query}
    <div class="search-empty">
      <div class="empty-icon">🔍</div>
      <h2>Start Searching</h2>
      <p>Enter a query above to search your indexes and external sources</p>
      <div class="quick-tips">
        <h3>Quick Tips</h3>
        <ul>
          <li>Use quotes for exact phrases: "machine learning"</li>
          <li>Search specific domains with site:example.com</li>
          <li>Exclude words with minus: python -snake</li>
        </ul>
      </div>
    </div>
  {/if}
</div>

<style>
  .search-page {
    max-width: 800px;
    margin: 0 auto;
  }

  .search-header {
    text-align: center;
    margin-bottom: var(--spacing-xl);
  }

  .search-header h1 {
    font-size: 2rem;
    margin-bottom: var(--spacing-sm);
  }

  .subtitle {
    color: var(--color-text-secondary);
  }

  .search-form {
    margin-bottom: var(--spacing-xl);
  }

  .search-input-wrapper {
    display: flex;
    gap: var(--spacing-sm);
  }

  .search-input {
    flex: 1;
  }

  .search-btn {
    padding: var(--spacing-md) var(--spacing-xl);
  }

  .error-message {
    background: #fef2f2;
    color: var(--color-error);
    padding: var(--spacing-md);
    border-radius: var(--radius-md);
    margin-bottom: var(--spacing-lg);
  }

  .results-header {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    margin-bottom: var(--spacing-md);
    color: var(--color-text-secondary);
  }

  .results-count {
    font-weight: 500;
  }

  .results-timing {
    font-size: 0.85rem;
  }

  .results-list {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-md);
  }

  .result-card {
    padding: var(--spacing-lg);
  }

  .result-title {
    font-size: 1.1rem;
    font-weight: 600;
    color: var(--color-primary);
    display: block;
    margin-bottom: var(--spacing-xs);
  }

  .result-title:hover {
    text-decoration: underline;
  }

  .result-url {
    font-size: 0.85rem;
    color: var(--color-success);
    margin-bottom: var(--spacing-sm);
    word-break: break-all;
  }

  .result-snippet {
    color: var(--color-text-secondary);
    margin-bottom: var(--spacing-sm);
    line-height: 1.6;
  }

  .result-meta {
    display: flex;
    gap: var(--spacing-md);
    font-size: 0.8rem;
  }

  .result-source,
  .result-index,
  .result-domain {
    background: var(--color-bg);
    padding: var(--spacing-xs) var(--spacing-sm);
    border-radius: var(--radius-sm);
    color: var(--color-text-secondary);
  }

  .no-results {
    text-align: center;
    padding: var(--spacing-xl);
    color: var(--color-text-secondary);
  }

  .hint {
    font-size: 0.9rem;
    margin-top: var(--spacing-sm);
  }

  .search-empty {
    text-align: center;
    padding: var(--spacing-xl) * 2;
  }

  .empty-icon {
    font-size: 4rem;
    margin-bottom: var(--spacing-md);
  }

  .search-empty h2 {
    margin-bottom: var(--spacing-sm);
  }

  .search-empty p {
    color: var(--color-text-secondary);
  }

  .quick-tips {
    margin-top: var(--spacing-xl);
    text-align: left;
    max-width: 400px;
    margin-left: auto;
    margin-right: auto;
  }

  .quick-tips h3 {
    font-size: 0.9rem;
    color: var(--color-text-secondary);
    margin-bottom: var(--spacing-sm);
  }

  .quick-tips ul {
    list-style: none;
    padding: 0;
  }

  .quick-tips li {
    padding: var(--spacing-xs) 0;
    font-size: 0.9rem;
    color: var(--color-text-secondary);
  }

  .quick-tips li::before {
    content: '→ ';
    color: var(--color-primary);
  }
</style>
