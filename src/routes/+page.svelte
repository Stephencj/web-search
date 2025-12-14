<script lang="ts">
  import { api, type SearchResponse, type SearchResult, type ImageSearchResponse, type ImageSearchResult, type VideoSearchResult, type ImageSearchStatus, type Index } from '$lib/api/client';
  import { onMount } from 'svelte';
  import { MediaViewer } from '$lib/components/MediaViewer';
  import { mediaViewer, type MediaItem } from '$lib/stores/mediaViewer.svelte';
  import { MediaContextMenu } from '$lib/components/ContextMenu';
  import { SaveButton } from '$lib/components/SaveButton';

  type SearchMode = 'web' | 'images' | 'videos';

  let query = $state('');
  let searchMode = $state<SearchMode>('web');
  let results = $state<SearchResult[]>([]);
  let imageResults = $state<ImageSearchResult[]>([]);
  let videoResults = $state<VideoSearchResult[]>([]);
  let totalResults = $state(0);
  let searching = $state(false);
  let loadingMore = $state(false);
  let searchError = $state<string | null>(null);
  let timing = $state({ local_ms: 0, external_ms: 0, total_ms: 0 });
  let imageTiming = $state(0);
  let videoTiming = $state(0);
  let imageSearchStatus = $state<ImageSearchStatus | null>(null);

  // Index filter state
  let availableIndexes = $state<Index[]>([]);
  let selectedIndex = $state<string>(''); // Empty string means "all indexes"

  // Pagination state
  let currentPage = $state(1);
  let perPage = 50;
  let hasMore = $derived(
    searchMode === 'images'
      ? imageResults.length < totalResults
      : searchMode === 'videos'
        ? videoResults.length < totalResults
        : false
  );

  // Live refresh state
  let autoRefresh = $state(false);
  let refreshInterval: ReturnType<typeof setInterval> | null = null;
  let lastRefreshTime = $state<Date | null>(null);
  let refreshing = $state(false);
  const REFRESH_INTERVAL_MS = 5000; // Refresh every 5 seconds

  // Sentinel element for infinite scroll
  let sentinelEl: HTMLDivElement | undefined = $state();
  let observer: IntersectionObserver | null = null;

  // Context menu state
  let contextMenuVisible = $state(false);
  let contextMenuX = $state(0);
  let contextMenuY = $state(0);
  let contextMenuMediaType = $state<'image' | 'video'>('image');
  let contextMenuMediaUrl = $state('');
  let contextMenuThumbnailUrl = $state<string | null>(null);
  let contextMenuTitle = $state<string | null>(null);
  let contextMenuSourceUrl = $state<string | null>(null);
  let contextMenuDomain = $state<string | null>(null);
  let contextMenuEmbedType = $state<string | null>(null);
  let contextMenuVideoId = $state<string | null>(null);

  function showImageContextMenu(e: MouseEvent, image: ImageSearchResult) {
    e.preventDefault();
    contextMenuX = e.clientX;
    contextMenuY = e.clientY;
    contextMenuMediaType = 'image';
    contextMenuMediaUrl = image.image_url;
    contextMenuThumbnailUrl = image.image_url;
    contextMenuTitle = image.page_title;
    contextMenuSourceUrl = image.page_url;
    contextMenuDomain = image.domain;
    contextMenuEmbedType = null;
    contextMenuVideoId = null;
    contextMenuVisible = true;
  }

  function showVideoContextMenu(e: MouseEvent, video: VideoSearchResult) {
    e.preventDefault();
    contextMenuX = e.clientX;
    contextMenuY = e.clientY;
    contextMenuMediaType = 'video';
    contextMenuMediaUrl = video.video_url;
    contextMenuThumbnailUrl = video.thumbnail_url;
    contextMenuTitle = video.video_title || video.page_title;
    contextMenuSourceUrl = video.page_url;
    contextMenuDomain = video.domain;
    contextMenuEmbedType = video.embed_type;
    contextMenuVideoId = video.video_id;
    contextMenuVisible = true;
  }

  // Effect to manage auto-refresh interval
  $effect(() => {
    if (autoRefresh && query.trim() && !searching) {
      refreshInterval = setInterval(() => {
        silentRefresh();
      }, REFRESH_INTERVAL_MS);

      return () => {
        if (refreshInterval) {
          clearInterval(refreshInterval);
          refreshInterval = null;
        }
      };
    } else if (refreshInterval) {
      clearInterval(refreshInterval);
      refreshInterval = null;
    }
  });

  async function silentRefresh() {
    if (refreshing || searching || !query.trim()) return;

    refreshing = true;
    try {
      const indexFilter = selectedIndex ? [selectedIndex] : undefined;
      if (searchMode === 'images') {
        // For images, fetch all pages we've loaded so far to check for new results
        const response = await api.searchImages({
          query: query.trim(),
          indexes: indexFilter,
          per_page: Math.max(imageResults.length, perPage),
          page: 1
        });

        // Only update if we have new results
        if (response.total_results !== totalResults || response.results.length !== imageResults.length) {
          imageResults = response.results;
          totalResults = response.total_results;
          imageTiming = response.timing_ms;
        }
      } else if (searchMode === 'videos') {
        const response = await api.searchVideos({
          query: query.trim(),
          indexes: indexFilter,
          per_page: Math.max(videoResults.length, perPage),
          page: 1
        });

        if (response.total_results !== totalResults || response.results.length !== videoResults.length) {
          videoResults = response.results;
          totalResults = response.total_results;
          videoTiming = response.timing_ms;
        }
      } else {
        const response = await api.search({ query: query.trim(), indexes: indexFilter });
        if (response.total_results !== totalResults) {
          results = response.results;
          totalResults = response.total_results;
          timing = response.timing;
        }
      }
      lastRefreshTime = new Date();
    } catch (e) {
      // Silent fail on refresh errors
      console.error('Refresh failed:', e);
    } finally {
      refreshing = false;
    }
  }

  onMount(() => {
    // Fetch available indexes
    (async () => {
      try {
        const response = await api.listIndexes();
        availableIndexes = response.items.filter(idx => idx.is_active);
      } catch (e) {
        console.error('Failed to fetch indexes:', e);
      }

      try {
        imageSearchStatus = await api.getImageSearchStatus();
      } catch (e) {
        // Image search not available
        imageSearchStatus = { enabled: false, model_loaded: false, model_name: '', embedding_dimensions: 0 };
      }
    })();

    // Set up intersection observer for infinite scroll
    observer = new IntersectionObserver(
      (entries) => {
        if (entries[0].isIntersecting && hasMore && !loadingMore && !searching) {
          if (searchMode === 'images') {
            loadMoreImages();
          } else if (searchMode === 'videos') {
            loadMoreVideos();
          }
        }
      },
      { rootMargin: '200px' }
    );

    return () => {
      observer?.disconnect();
      if (refreshInterval) {
        clearInterval(refreshInterval);
      }
    };
  });

  // Watch sentinel element and observe it
  $effect(() => {
    if (sentinelEl && observer) {
      observer.observe(sentinelEl);
      return () => observer?.unobserve(sentinelEl!);
    }
  });

  async function handleSearch(event: Event) {
    event.preventDefault();
    if (!query.trim()) return;

    searching = true;
    searchError = null;
    currentPage = 1;

    try {
      const indexFilter = selectedIndex ? [selectedIndex] : undefined;
      if (searchMode === 'web') {
        const response = await api.search({ query: query.trim(), indexes: indexFilter });
        results = response.results;
        totalResults = response.total_results;
        timing = response.timing;
        imageResults = [];
        videoResults = [];
      } else if (searchMode === 'images') {
        const response = await api.searchImages({ query: query.trim(), indexes: indexFilter, per_page: perPage, page: 1 });
        imageResults = response.results;
        totalResults = response.total_results;
        imageTiming = response.timing_ms;
        results = [];
        videoResults = [];
      } else {
        const response = await api.searchVideos({ query: query.trim(), indexes: indexFilter, per_page: perPage, page: 1 });
        videoResults = response.results;
        totalResults = response.total_results;
        videoTiming = response.timing_ms;
        results = [];
        imageResults = [];
      }
    } catch (e) {
      searchError = e instanceof Error ? e.message : 'Search failed';
      results = [];
      imageResults = [];
      videoResults = [];
      totalResults = 0;
    } finally {
      searching = false;
    }
  }

  async function loadMoreImages() {
    if (loadingMore || !hasMore || !query.trim()) return;

    loadingMore = true;
    currentPage++;

    try {
      const indexFilter = selectedIndex ? [selectedIndex] : undefined;
      const response = await api.searchImages({
        query: query.trim(),
        indexes: indexFilter,
        per_page: perPage,
        page: currentPage
      });
      imageResults = [...imageResults, ...response.results];
    } catch (e) {
      currentPage--; // Revert on error
      console.error('Failed to load more images:', e);
    } finally {
      loadingMore = false;
    }
  }

  async function loadMoreVideos() {
    if (loadingMore || !hasMore || !query.trim()) return;

    loadingMore = true;
    currentPage++;

    try {
      const indexFilter = selectedIndex ? [selectedIndex] : undefined;
      const response = await api.searchVideos({
        query: query.trim(),
        indexes: indexFilter,
        per_page: perPage,
        page: currentPage
      });
      videoResults = [...videoResults, ...response.results];
    } catch (e) {
      currentPage--;
      console.error('Failed to load more videos:', e);
    } finally {
      loadingMore = false;
    }
  }

  function switchMode(mode: SearchMode) {
    searchMode = mode;
    currentPage = 1;
    // Re-run search if we have a query
    if (query.trim()) {
      handleSearch(new Event('submit'));
    }
  }

  // Convert image results to MediaItem format for the viewer
  function openImageViewer(index: number) {
    const items: MediaItem[] = imageResults.map(img => ({
      type: 'image',
      url: img.image_url,
      alt: img.image_alt,
      title: img.page_title,
      pageUrl: img.page_url,
      domain: img.domain,
    }));
    mediaViewer.open(items, index);
  }

  // Convert video results to MediaItem format for the viewer
  function openVideoViewer(index: number) {
    const items: MediaItem[] = videoResults.map(vid => ({
      type: 'video',
      url: vid.video_url,
      thumbnailUrl: vid.thumbnail_url,
      title: vid.video_title || vid.page_title,
      pageUrl: vid.page_url,
      pageTitle: vid.page_title,
      domain: vid.domain,
      embedType: vid.embed_type as 'direct' | 'youtube' | 'vimeo' | 'page_link',
      videoId: vid.video_id || undefined,
    }));
    mediaViewer.open(items, index);
  }
</script>

<MediaViewer />

<MediaContextMenu
  x={contextMenuX}
  y={contextMenuY}
  visible={contextMenuVisible}
  mediaType={contextMenuMediaType}
  mediaUrl={contextMenuMediaUrl}
  thumbnailUrl={contextMenuThumbnailUrl}
  title={contextMenuTitle}
  sourceUrl={contextMenuSourceUrl}
  domain={contextMenuDomain}
  embedType={contextMenuEmbedType}
  videoId={contextMenuVideoId}
  on:close={() => (contextMenuVisible = false)}
/>

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
        placeholder={searchMode === 'images' ? 'Describe the image you\'re looking for...' : searchMode === 'videos' ? 'Describe the video you\'re looking for...' : 'Enter your search query...'}
        bind:value={query}
        disabled={searching}
      />
      <button type="submit" class="btn btn-primary search-btn" disabled={searching || !query.trim()}>
        {searching ? 'Searching...' : 'Search'}
      </button>
    </div>
  </form>

  <!-- Search mode tabs and filters -->
  <div class="search-controls">
    <div class="search-tabs">
      <button
        class="tab-btn"
        class:active={searchMode === 'web'}
        onclick={() => switchMode('web')}
      >
        Web
      </button>
      <button
        class="tab-btn"
        class:active={searchMode === 'images'}
        onclick={() => switchMode('images')}
        disabled={!imageSearchStatus?.enabled}
        title={!imageSearchStatus?.enabled ? 'Image search is not enabled' : ''}
      >
        Images
        {#if imageSearchStatus?.enabled && imageSearchStatus?.model_loaded}
          <span class="status-dot active"></span>
        {:else if imageSearchStatus?.enabled}
          <span class="status-dot loading"></span>
        {/if}
      </button>
      <button
        class="tab-btn"
        class:active={searchMode === 'videos'}
        onclick={() => switchMode('videos')}
        disabled={!imageSearchStatus?.enabled}
        title={!imageSearchStatus?.enabled ? 'Video search is not enabled' : ''}
      >
        Videos
        {#if imageSearchStatus?.enabled && imageSearchStatus?.model_loaded}
          <span class="status-dot active"></span>
        {:else if imageSearchStatus?.enabled}
          <span class="status-dot loading"></span>
        {/if}
      </button>
    </div>

    {#if availableIndexes.length > 0}
      <div class="index-filter">
        <label for="index-select">Source:</label>
        <select
          id="index-select"
          bind:value={selectedIndex}
          onchange={() => query.trim() && handleSearch(new Event('submit'))}
        >
          <option value="">All indexes</option>
          {#each availableIndexes as idx}
            <option value={idx.slug}>{idx.name}</option>
          {/each}
        </select>
      </div>
    {/if}
  </div>

  {#if searchError}
    <div class="error-message">
      {searchError}
    </div>
  {/if}

  <!-- Web Results -->
  {#if searchMode === 'web' && results.length > 0}
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
  {/if}

  <!-- Image Results -->
  {#if searchMode === 'images' && imageResults.length > 0}
    <div class="results-header">
      <span class="results-count">{imageResults.length} of {totalResults} images</span>
      <span class="results-timing">({imageTiming}ms)</span>
      <div class="refresh-controls">
        <label class="auto-refresh-toggle">
          <input type="checkbox" bind:checked={autoRefresh} />
          <span class="toggle-label">Live refresh</span>
          {#if autoRefresh}
            <span class="refresh-indicator" class:refreshing></span>
          {/if}
        </label>
        <button class="btn btn-sm refresh-btn" onclick={() => silentRefresh()} disabled={refreshing}>
          {refreshing ? 'Refreshing...' : 'Refresh'}
        </button>
      </div>
    </div>

    <div class="image-grid">
      {#each imageResults as image, index}
        <button
          type="button"
          class="image-card"
          onclick={() => openImageViewer(index)}
          oncontextmenu={(e) => showImageContextMenu(e, image)}
          title="Click to view. Right-click for options."
        >
          <div class="image-container">
            <SaveButton
              mediaType="image"
              mediaUrl={image.image_url}
              thumbnailUrl={image.image_url}
              title={image.page_title}
              sourceUrl={image.page_url}
              domain={image.domain}
            />
            <img
              src={image.image_url}
              alt={image.image_alt || 'Image result'}
              loading="lazy"
              onerror={(e) => {
                const target = e.target as HTMLImageElement;
                target.style.display = 'none';
                target.parentElement!.classList.add('image-error');
              }}
            />
          </div>
          <div class="image-info">
            <div class="image-title">{image.page_title}</div>
            <div class="image-domain">{image.domain}</div>
          </div>
        </button>
      {/each}
    </div>

    <!-- Infinite scroll sentinel and loading indicator -->
    {#if hasMore}
      <div class="load-more-sentinel" bind:this={sentinelEl}>
        {#if loadingMore}
          <div class="loading-spinner">
            <span class="spinner"></span>
            Loading more images...
          </div>
        {/if}
      </div>
    {:else if imageResults.length > 0}
      <div class="end-of-results">
        All {totalResults} images loaded
      </div>
    {/if}
  {/if}

  <!-- Video Results -->
  {#if searchMode === 'videos' && videoResults.length > 0}
    <div class="results-header">
      <span class="results-count">{videoResults.length} of {totalResults} videos</span>
      <span class="results-timing">({videoTiming}ms)</span>
      <div class="refresh-controls">
        <label class="auto-refresh-toggle">
          <input type="checkbox" bind:checked={autoRefresh} />
          <span class="toggle-label">Live refresh</span>
          {#if autoRefresh}
            <span class="refresh-indicator" class:refreshing></span>
          {/if}
        </label>
        <button class="btn btn-sm refresh-btn" onclick={() => silentRefresh()} disabled={refreshing}>
          {refreshing ? 'Refreshing...' : 'Refresh'}
        </button>
      </div>
    </div>

    <div class="video-grid">
      {#each videoResults as video, index}
        <button
          type="button"
          class="video-card"
          onclick={() => openVideoViewer(index)}
          oncontextmenu={(e) => showVideoContextMenu(e, video)}
          title="Click to play. Right-click for options."
        >
          <div class="video-container">
            <SaveButton
              mediaType="video"
              mediaUrl={video.video_url || video.page_url}
              thumbnailUrl={video.thumbnail_url}
              title={video.video_title || video.page_title}
              sourceUrl={video.page_url}
              domain={video.domain}
              embedType={video.embed_type}
              videoId={video.video_id}
            />
            {#if video.thumbnail_url}
              <img
                src={video.thumbnail_url}
                alt={video.video_title || 'Video thumbnail'}
                loading="lazy"
                onerror={(e) => {
                  const target = e.target as HTMLImageElement;
                  target.style.display = 'none';
                  target.parentElement!.classList.add('video-error');
                }}
              />
            {:else}
              <div class="no-thumbnail"></div>
            {/if}
            <div class="play-overlay">
              <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="white">
                <polygon points="5 3 19 12 5 21 5 3"></polygon>
              </svg>
            </div>
            {#if video.embed_type !== 'direct'}
              <span class="video-badge">{video.embed_type}</span>
            {/if}
          </div>
          <div class="video-info">
            <div class="video-title">{video.video_title || video.page_title}</div>
            <div class="video-domain">{video.domain}</div>
          </div>
        </button>
      {/each}
    </div>

    <!-- Infinite scroll sentinel and loading indicator -->
    {#if hasMore}
      <div class="load-more-sentinel" bind:this={sentinelEl}>
        {#if loadingMore}
          <div class="loading-spinner">
            <span class="spinner"></span>
            Loading more videos...
          </div>
        {/if}
      </div>
    {:else if videoResults.length > 0}
      <div class="end-of-results">
        All {totalResults} videos loaded
      </div>
    {/if}
  {/if}

  <!-- No results -->
  {#if query && !searching && !searchError && ((searchMode === 'web' && results.length === 0) || (searchMode === 'images' && imageResults.length === 0) || (searchMode === 'videos' && videoResults.length === 0))}
    <div class="no-results">
      <p>No {searchMode === 'images' ? 'images' : searchMode === 'videos' ? 'videos' : 'results'} found for "{query}"</p>
      <p class="hint">
        {#if searchMode === 'images'}
          Try different descriptions or crawl some pages with images first
        {:else if searchMode === 'videos'}
          Try different descriptions or crawl some pages with videos first
        {:else}
          Try different keywords or check your index sources
        {/if}
      </p>
      {#if searchMode === 'images' || searchMode === 'videos'}
        <div class="refresh-controls-standalone">
          <label class="auto-refresh-toggle">
            <input type="checkbox" bind:checked={autoRefresh} />
            <span class="toggle-label">Live refresh while crawling</span>
            {#if autoRefresh}
              <span class="refresh-indicator" class:refreshing></span>
            {/if}
          </label>
          <button class="btn btn-sm refresh-btn" onclick={() => silentRefresh()} disabled={refreshing}>
            {refreshing ? 'Checking...' : `Check for new ${searchMode}`}
          </button>
        </div>
      {/if}
    </div>
  {/if}

  <!-- Empty state -->
  {#if !query}
    <div class="search-empty">
      <div class="empty-icon">{searchMode === 'images' ? '🖼️' : searchMode === 'videos' ? '🎬' : '🔍'}</div>
      <h2>Start Searching</h2>
      <p>
        {#if searchMode === 'images'}
          Describe the image you're looking for using natural language
        {:else if searchMode === 'videos'}
          Describe the video you're looking for using natural language
        {:else}
          Enter a query above to search your indexes and external sources
        {/if}
      </p>
      {#if searchMode === 'web'}
        <div class="quick-tips">
          <h3>Quick Tips</h3>
          <ul>
            <li>Use quotes for exact phrases: "machine learning"</li>
            <li>Search specific domains with site:example.com</li>
            <li>Exclude words with minus: python -snake</li>
          </ul>
        </div>
      {:else if searchMode === 'images'}
        <div class="quick-tips">
          <h3>Image Search Tips</h3>
          <ul>
            <li>Describe what you see: "sunset over mountains"</li>
            <li>Include colors and objects: "red sports car"</li>
            <li>Be specific: "diagram of neural network architecture"</li>
          </ul>
        </div>
      {:else}
        <div class="quick-tips">
          <h3>Video Search Tips</h3>
          <ul>
            <li>Describe the video content: "cooking tutorial"</li>
            <li>Include platform hints: "youtube tech review"</li>
            <li>Be specific: "how to fix a flat tire"</li>
          </ul>
        </div>
      {/if}
    </div>
  {/if}
</div>

<style>
  .search-page {
    max-width: 1000px;
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
    margin-bottom: var(--spacing-md);
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

  .search-controls {
    display: flex;
    justify-content: space-between;
    align-items: flex-end;
    margin-bottom: var(--spacing-xl);
    border-bottom: 1px solid var(--color-border);
    padding-bottom: var(--spacing-sm);
    flex-wrap: wrap;
    gap: var(--spacing-md);
  }

  .search-tabs {
    display: flex;
    gap: var(--spacing-sm);
  }

  .index-filter {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    font-size: 0.9rem;
  }

  .index-filter label {
    color: var(--color-text-secondary);
  }

  .index-filter select {
    padding: var(--spacing-xs) var(--spacing-sm);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-sm);
    background: var(--color-surface);
    color: var(--color-text);
    font-size: 0.9rem;
    cursor: pointer;
  }

  .index-filter select:hover {
    border-color: var(--color-primary);
  }

  .index-filter select:focus {
    outline: none;
    border-color: var(--color-primary);
    box-shadow: 0 0 0 2px rgba(var(--color-primary-rgb, 59, 130, 246), 0.2);
  }

  .tab-btn {
    padding: var(--spacing-sm) var(--spacing-lg);
    border: none;
    background: none;
    cursor: pointer;
    font-size: 1rem;
    color: var(--color-text-secondary);
    border-radius: var(--radius-md) var(--radius-md) 0 0;
    display: flex;
    align-items: center;
    gap: var(--spacing-xs);
    transition: all 0.2s;
  }

  .tab-btn:hover:not(:disabled) {
    color: var(--color-text);
    background: var(--color-bg);
  }

  .tab-btn.active {
    color: var(--color-primary);
    border-bottom: 2px solid var(--color-primary);
    margin-bottom: -1px;
  }

  .tab-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
  }

  .status-dot.active {
    background: var(--color-success);
  }

  .status-dot.loading {
    background: var(--color-warning);
    animation: pulse 1.5s infinite;
  }

  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
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
    flex-wrap: wrap;
  }

  .results-count {
    font-weight: 500;
  }

  .results-timing {
    font-size: 0.85rem;
  }

  .refresh-controls {
    margin-left: auto;
    display: flex;
    align-items: center;
    gap: var(--spacing-md);
  }

  .auto-refresh-toggle {
    display: flex;
    align-items: center;
    gap: var(--spacing-xs);
    cursor: pointer;
    user-select: none;
  }

  .auto-refresh-toggle input[type="checkbox"] {
    width: 16px;
    height: 16px;
    cursor: pointer;
  }

  .toggle-label {
    font-size: 0.85rem;
  }

  .refresh-indicator {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--color-success);
    animation: pulse 1.5s infinite;
  }

  .refresh-indicator.refreshing {
    background: var(--color-warning);
    animation: pulse 0.5s infinite;
  }

  .refresh-btn {
    padding: var(--spacing-xs) var(--spacing-sm);
    font-size: 0.8rem;
  }

  .btn-sm {
    padding: var(--spacing-xs) var(--spacing-md);
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

  /* Image Grid Styles */
  .image-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: var(--spacing-md);
  }

  .image-card {
    background: var(--color-surface);
    border-radius: var(--radius-md);
    overflow: hidden;
    text-decoration: none;
    color: inherit;
    transition: transform 0.2s, box-shadow 0.2s;
    border: 1px solid var(--color-border);
    cursor: pointer;
    text-align: left;
    padding: 0;
  }

  .image-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  }

  .image-container {
    aspect-ratio: 1;
    overflow: hidden;
    background: var(--color-bg);
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .image-container img {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }

  .image-container.image-error {
    background: var(--color-bg);
  }

  .image-container.image-error::after {
    content: 'Image not available';
    color: var(--color-text-secondary);
    font-size: 0.8rem;
  }

  .image-info {
    padding: var(--spacing-sm);
  }

  .image-title {
    font-size: 0.85rem;
    font-weight: 500;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    margin-bottom: var(--spacing-xs);
  }

  .image-domain {
    font-size: 0.75rem;
    color: var(--color-text-secondary);
  }

  /* Video Grid Styles */
  .video-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: var(--spacing-md);
  }

  .video-card {
    background: var(--color-surface);
    border-radius: var(--radius-md);
    overflow: hidden;
    text-decoration: none;
    color: inherit;
    transition: transform 0.2s, box-shadow 0.2s;
    border: 1px solid var(--color-border);
    cursor: pointer;
    text-align: left;
    padding: 0;
  }

  .video-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  }

  .video-card:hover .play-overlay {
    opacity: 1;
  }

  .video-container {
    aspect-ratio: 16/9;
    overflow: hidden;
    background: #000;
    display: flex;
    align-items: center;
    justify-content: center;
    position: relative;
  }

  .video-container img {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }

  .video-container.video-error {
    background: var(--color-bg);
  }

  .video-container.video-error::after {
    content: 'Thumbnail not available';
    color: var(--color-text-secondary);
    font-size: 0.8rem;
  }

  .no-thumbnail {
    width: 100%;
    height: 100%;
    background: linear-gradient(135deg, #1a1a1a 0%, #333 100%);
  }

  .play-overlay {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(0, 0, 0, 0.3);
    opacity: 0.8;
    transition: opacity 0.2s;
  }

  .play-overlay svg {
    filter: drop-shadow(0 2px 4px rgba(0,0,0,0.3));
  }

  .video-badge {
    position: absolute;
    top: 8px;
    right: 8px;
    background: rgba(0, 0, 0, 0.7);
    color: white;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 0.7rem;
    text-transform: uppercase;
    font-weight: 600;
  }

  .video-info {
    padding: var(--spacing-sm);
  }

  .video-title {
    font-size: 0.9rem;
    font-weight: 500;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    margin-bottom: var(--spacing-xs);
  }

  .video-domain {
    font-size: 0.75rem;
    color: var(--color-text-secondary);
  }

  /* Infinite scroll loading */
  .load-more-sentinel {
    padding: var(--spacing-xl);
    min-height: 100px;
  }

  .loading-spinner {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: var(--spacing-sm);
    color: var(--color-text-secondary);
  }

  .spinner {
    width: 20px;
    height: 20px;
    border: 2px solid var(--color-border);
    border-top-color: var(--color-primary);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  .end-of-results {
    text-align: center;
    padding: var(--spacing-xl);
    color: var(--color-text-secondary);
    font-size: 0.9rem;
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

  .refresh-controls-standalone {
    margin-top: var(--spacing-lg);
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: var(--spacing-md);
    padding: var(--spacing-lg);
    background: var(--color-surface);
    border-radius: var(--radius-md);
    border: 1px solid var(--color-border);
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
    content: '-> ';
    color: var(--color-primary);
  }

  /* Mobile styles */
  @media (max-width: 768px) {
    .search-header {
      display: none; /* Hide header on mobile - using mobile header from layout */
    }

    .search-input-wrapper {
      flex-direction: column;
    }

    .search-input {
      width: 100%;
      min-height: var(--touch-target-min);
      font-size: 16px; /* Prevents iOS zoom */
    }

    .search-btn {
      width: 100%;
      min-height: var(--touch-target-min);
    }

    .search-controls {
      flex-direction: column;
      gap: var(--spacing-sm);
    }

    .search-tabs {
      width: 100%;
      justify-content: stretch;
    }

    .tab-btn {
      flex: 1;
      padding: var(--spacing-md) var(--spacing-xs);
      font-size: 0.9rem;
      min-height: var(--touch-target-min);
    }

    .index-filter {
      width: 100%;
    }

    .index-filter select {
      width: 100%;
      min-height: var(--touch-target-min);
      font-size: 16px;
    }

    .results-header {
      flex-direction: column;
      align-items: flex-start;
      gap: var(--spacing-sm);
    }

    .refresh-controls {
      width: 100%;
      justify-content: space-between;
      flex-wrap: wrap;
    }

    .refresh-btn {
      min-height: var(--touch-target-min);
      padding: var(--spacing-sm) var(--spacing-md);
    }

    /* Image grid - 2 columns on mobile */
    .image-grid {
      grid-template-columns: repeat(2, 1fr);
      gap: var(--spacing-sm);
    }

    .image-card {
      min-height: var(--touch-target-min);
    }

    .image-info {
      padding: var(--spacing-sm);
    }

    .image-title {
      font-size: 0.8rem;
    }

    .image-domain {
      font-size: 0.7rem;
    }

    /* Video grid - single column on mobile */
    .video-grid {
      grid-template-columns: 1fr;
      gap: var(--spacing-md);
    }

    .video-card {
      min-height: var(--touch-target-min);
    }

    .video-info {
      padding: var(--spacing-sm);
    }

    .video-title {
      font-size: 0.95rem;
    }

    .video-domain {
      font-size: 0.8rem;
    }

    /* Result cards */
    .result-card {
      padding: var(--spacing-md);
    }

    .result-title {
      font-size: 1rem;
      padding: var(--spacing-xs) 0;
    }

    .result-url {
      font-size: 0.75rem;
    }

    .result-snippet {
      font-size: 0.9rem;
      line-height: 1.5;
    }

    .result-meta {
      flex-wrap: wrap;
      gap: var(--spacing-xs);
    }

    .result-source,
    .result-index,
    .result-domain {
      font-size: 0.75rem;
      padding: var(--spacing-xs) var(--spacing-sm);
    }

    /* Auto-refresh toggle - larger touch target */
    .auto-refresh-toggle {
      font-size: 0.85rem;
      padding: var(--spacing-xs);
      min-height: var(--touch-target-min);
    }

    .auto-refresh-toggle input[type="checkbox"] {
      width: 20px;
      height: 20px;
    }

    .toggle-label {
      font-size: 0.8rem;
    }

    /* Empty state */
    .search-empty {
      padding: var(--spacing-lg);
    }

    .empty-icon {
      font-size: 3rem;
    }

    .quick-tips {
      max-width: 100%;
    }

    .quick-tips li {
      padding: var(--spacing-sm) 0;
    }
  }

  /* Small phones */
  @media (max-width: 480px) {
    .image-grid {
      grid-template-columns: repeat(2, 1fr);
      gap: var(--spacing-xs);
    }

    .image-info {
      padding: var(--spacing-xs);
    }

    .image-title {
      font-size: 0.75rem;
    }

    .tab-btn {
      font-size: 0.8rem;
      padding: var(--spacing-sm) var(--spacing-xs);
    }

    .refresh-controls {
      flex-direction: column;
      gap: var(--spacing-sm);
    }

    .refresh-btn {
      width: 100%;
    }
  }
</style>
