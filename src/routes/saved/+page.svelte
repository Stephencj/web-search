<script lang="ts">
  import { api, type SavedVideo, type SavedVideoStats } from '$lib/api/client';
  import { videoPlayer, savedVideoToVideoItem, formatDuration } from '$lib/stores/videoPlayer.svelte';

  // State
  let savedVideos = $state<SavedVideo[]>([]);
  let stats = $state<SavedVideoStats | null>(null);
  let loading = $state(true);
  let error = $state<string | null>(null);
  let platformFilter = $state<string>('all');
  let watchedFilter = $state<string>('all');
  let page = $state(1);
  let total = $state(0);
  let perPage = 24;
  let deletingId = $state<number | null>(null);

  // Load saved videos on mount
  $effect(() => {
    loadSavedVideos();
    loadStats();
  });

  // Reload when filters change
  $effect(() => {
    // Track dependencies
    platformFilter;
    watchedFilter;
    page;
    // Reload
    loadSavedVideos();
  });

  async function loadSavedVideos() {
    loading = true;
    error = null;
    try {
      const params: Parameters<typeof api.listSavedVideos>[0] = {
        limit: perPage,
        offset: (page - 1) * perPage,
      };
      if (platformFilter !== 'all') {
        params.platform = platformFilter;
      }
      if (watchedFilter !== 'all') {
        params.is_watched = watchedFilter === 'watched';
      }
      const response = await api.listSavedVideos(params);
      savedVideos = response.items;
      total = response.total;
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to load saved videos';
    } finally {
      loading = false;
    }
  }

  async function loadStats() {
    try {
      stats = await api.getSavedVideoStats();
    } catch (e) {
      console.error('Failed to load stats:', e);
    }
  }

  async function toggleWatched(video: SavedVideo) {
    try {
      if (video.is_watched) {
        await api.markSavedVideoUnwatched(video.id);
      } else {
        await api.markSavedVideoWatched(video.id);
      }
      // Update local state
      savedVideos = savedVideos.map(v =>
        v.id === video.id ? { ...v, is_watched: !v.is_watched } : v
      );
      loadStats();
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to update watch status';
    }
  }

  async function deleteVideo(id: number) {
    deletingId = id;
    try {
      await api.deleteSavedVideo(id);
      savedVideos = savedVideos.filter(v => v.id !== id);
      total -= 1;
      loadStats();
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to delete video';
    } finally {
      deletingId = null;
    }
  }

  function playVideo(video: SavedVideo) {
    // Find index of selected video in the current list
    const index = savedVideos.findIndex(v => v.id === video.id);
    // Convert all videos to VideoItems for the queue
    const queue = savedVideos.map(v => savedVideoToVideoItem(v));
    // Open with queue for playlist auto-advance
    videoPlayer.openWithQueue(queue, index >= 0 ? index : 0);
    // Mark as watched when playing
    if (!video.is_watched) {
      toggleWatched(video);
    }
  }

  function formatCount(count: number | null): string {
    if (!count) return '';
    if (count >= 1_000_000_000) return `${(count / 1_000_000_000).toFixed(1)}B`;
    if (count >= 1_000_000) return `${(count / 1_000_000).toFixed(1)}M`;
    if (count >= 1_000) return `${(count / 1_000).toFixed(1)}K`;
    return count.toString();
  }

  function formatDate(dateStr: string | null): string {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    return date.toLocaleDateString();
  }

  function getPlatformColor(platform: string): string {
    const colors: Record<string, string> = {
      youtube: '#FF0000',
      rumble: '#85C742',
      odysee: '#F2685C',
      bitchute: '#EF4136',
      dailymotion: '#0066DC',
    };
    return colors[platform] || '#666';
  }

  const totalPages = $derived(Math.ceil(total / perPage));
  const platforms = $derived(stats ? Object.keys(stats.by_platform) : []);
</script>

<div class="saved-page">
  <header class="page-header">
    <div class="header-content">
      <h1>Saved Videos</h1>
      <p class="subtitle">Your bookmarked videos from all platforms</p>
    </div>
    {#if stats}
      <div class="stats-cards">
        <div class="stat-card">
          <span class="stat-value">{stats.total_videos}</span>
          <span class="stat-label">Total</span>
        </div>
        <div class="stat-card">
          <span class="stat-value">{stats.unwatched_videos}</span>
          <span class="stat-label">Unwatched</span>
        </div>
        <div class="stat-card">
          <span class="stat-value">{stats.watched_videos}</span>
          <span class="stat-label">Watched</span>
        </div>
      </div>
    {/if}
  </header>

  <!-- Filters -->
  <div class="filters">
    <div class="filter-group">
      <label>Platform:</label>
      <select bind:value={platformFilter} class="select">
        <option value="all">All Platforms</option>
        {#each platforms as platform}
          <option value={platform}>{platform.charAt(0).toUpperCase() + platform.slice(1)}</option>
        {/each}
      </select>
    </div>
    <div class="filter-group">
      <label>Status:</label>
      <select bind:value={watchedFilter} class="select">
        <option value="all">All</option>
        <option value="unwatched">Unwatched</option>
        <option value="watched">Watched</option>
      </select>
    </div>
  </div>

  <!-- Error -->
  {#if error}
    <div class="error-message">{error}</div>
  {/if}

  <!-- Content -->
  {#if loading}
    <div class="loading">
      <div class="loading-spinner"></div>
      <span>Loading saved videos...</span>
    </div>
  {:else if savedVideos.length === 0}
    <div class="empty-state">
      <div class="empty-icon">📚</div>
      <h2>No Saved Videos</h2>
      <p>Save videos from the Discover page to see them here.</p>
      <a href="/discover" class="btn-primary">Go to Discover</a>
    </div>
  {:else}
    <div class="results-info">
      <span>Showing {savedVideos.length} of {total} videos</span>
    </div>

    <div class="video-grid">
      {#each savedVideos as video}
        <div class="video-card" class:watched={video.is_watched}>
          <button class="thumbnail-btn" onclick={() => playVideo(video)}>
            <div class="thumbnail">
              {#if video.thumbnail_url}
                <img src={video.thumbnail_url} alt={video.title} loading="lazy" />
              {:else}
                <div class="no-thumbnail">No Thumbnail</div>
              {/if}
              <div class="play-overlay">
                <svg viewBox="0 0 24 24" fill="currentColor" width="48" height="48">
                  <path d="M8 5v14l11-7z" />
                </svg>
              </div>
              {#if video.duration_seconds}
                <span class="duration">{formatDuration(video.duration_seconds)}</span>
              {/if}
              <span class="platform-badge" style="background-color: {getPlatformColor(video.platform)}">
                {video.platform}
              </span>
              {#if video.is_watched}
                <span class="watched-badge">Watched</span>
              {/if}
            </div>
          </button>
          <div class="video-info">
            <a href={video.video_url} target="_blank" rel="noopener noreferrer" class="video-title">
              {video.title}
            </a>
            <div class="video-meta">
              {#if video.channel_name}
                <span class="channel-name">{video.channel_name}</span>
              {/if}
              {#if video.view_count}
                <span class="view-count">{formatCount(video.view_count)} views</span>
              {/if}
            </div>
            <div class="video-date">
              Saved {formatDate(video.saved_at)}
            </div>
            <div class="video-actions">
              <button
                class="action-btn watch-toggle"
                onclick={() => toggleWatched(video)}
                title={video.is_watched ? 'Mark as unwatched' : 'Mark as watched'}
              >
                {video.is_watched ? 'Unwatch' : 'Watched'}
              </button>
              <button
                class="action-btn delete"
                onclick={() => deleteVideo(video.id)}
                disabled={deletingId === video.id}
                title="Remove from saved"
              >
                {deletingId === video.id ? '...' : 'Remove'}
              </button>
              <button class="action-btn play" onclick={() => playVideo(video)}>
                Play
              </button>
            </div>
          </div>
        </div>
      {/each}
    </div>

    <!-- Pagination -->
    {#if totalPages > 1}
      <div class="pagination">
        <button
          class="page-btn"
          onclick={() => page = Math.max(1, page - 1)}
          disabled={page === 1}
        >
          Previous
        </button>
        <span class="page-info">Page {page} of {totalPages}</span>
        <button
          class="page-btn"
          onclick={() => page = Math.min(totalPages, page + 1)}
          disabled={page === totalPages}
        >
          Next
        </button>
      </div>
    {/if}
  {/if}
</div>

<style>
  .saved-page {
    max-width: 1400px;
    margin: 0 auto;
  }

  .page-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    flex-wrap: wrap;
    gap: var(--spacing-lg);
    margin-bottom: var(--spacing-xl);
  }

  .page-header h1 {
    font-size: 2rem;
    margin: 0 0 var(--spacing-xs) 0;
  }

  .subtitle {
    color: var(--color-text-secondary);
    margin: 0;
  }

  .stats-cards {
    display: flex;
    gap: var(--spacing-md);
  }

  .stat-card {
    background: var(--color-bg-secondary);
    padding: var(--spacing-md) var(--spacing-lg);
    border-radius: var(--radius-md);
    text-align: center;
    min-width: 80px;
  }

  .stat-value {
    display: block;
    font-size: 1.5rem;
    font-weight: 600;
    color: var(--color-primary);
  }

  .stat-label {
    font-size: 0.75rem;
    color: var(--color-text-secondary);
  }

  /* Filters */
  .filters {
    display: flex;
    gap: var(--spacing-lg);
    flex-wrap: wrap;
    margin-bottom: var(--spacing-lg);
  }

  .filter-group {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
  }

  .filter-group label {
    font-size: 0.9rem;
    color: var(--color-text-secondary);
  }

  .select {
    padding: var(--spacing-sm) var(--spacing-md);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    background: var(--color-bg);
    color: var(--color-text);
    font-size: 0.9rem;
    min-width: 150px;
  }

  /* Messages */
  .error-message {
    padding: var(--spacing-md);
    background: rgba(239, 68, 68, 0.1);
    color: var(--color-error);
    border-radius: var(--radius-md);
    margin-bottom: var(--spacing-md);
  }

  /* Loading */
  .loading {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: var(--spacing-md);
    padding: var(--spacing-xxl);
    color: var(--color-text-secondary);
  }

  .loading-spinner {
    width: 40px;
    height: 40px;
    border: 3px solid var(--color-border);
    border-top-color: var(--color-primary);
    border-radius: 50%;
    animation: spin 1s linear infinite;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  /* Empty State */
  .empty-state {
    text-align: center;
    padding: var(--spacing-xxl);
    color: var(--color-text-secondary);
  }

  .empty-icon {
    font-size: 4rem;
    margin-bottom: var(--spacing-md);
  }

  .empty-state h2 {
    color: var(--color-text);
    margin: 0 0 var(--spacing-sm) 0;
  }

  .btn-primary {
    display: inline-block;
    margin-top: var(--spacing-md);
    padding: var(--spacing-sm) var(--spacing-lg);
    background: var(--color-primary);
    color: white;
    text-decoration: none;
    border-radius: var(--radius-md);
    font-weight: 500;
  }

  .btn-primary:hover {
    opacity: 0.9;
  }

  /* Results */
  .results-info {
    color: var(--color-text-secondary);
    margin-bottom: var(--spacing-md);
    font-size: 0.9rem;
  }

  /* Video Grid */
  .video-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: var(--spacing-lg);
  }

  .video-card {
    background: var(--color-bg-secondary);
    border-radius: var(--radius-lg);
    overflow: hidden;
    transition: transform 0.2s ease, box-shadow 0.2s ease;
  }

  .video-card:hover {
    transform: translateY(-2px);
    box-shadow: var(--shadow-md);
  }

  .video-card.watched {
    opacity: 0.7;
  }

  .thumbnail-btn {
    display: block;
    width: 100%;
    padding: 0;
    border: none;
    background: none;
    cursor: pointer;
  }

  .thumbnail {
    position: relative;
    aspect-ratio: 16 / 9;
    background: var(--color-bg);
    overflow: hidden;
  }

  .thumbnail img {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }

  .no-thumbnail {
    width: 100%;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--color-text-secondary);
  }

  .play-overlay {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(0, 0, 0, 0.3);
    opacity: 0;
    transition: opacity 0.2s;
    color: white;
  }

  .thumbnail-btn:hover .play-overlay {
    opacity: 1;
  }

  .duration {
    position: absolute;
    bottom: var(--spacing-xs);
    right: var(--spacing-xs);
    background: rgba(0, 0, 0, 0.8);
    color: white;
    padding: 2px 6px;
    border-radius: var(--radius-sm);
    font-size: 0.75rem;
    font-weight: 500;
  }

  .platform-badge {
    position: absolute;
    top: var(--spacing-xs);
    left: var(--spacing-xs);
    color: white;
    padding: 2px 8px;
    border-radius: var(--radius-sm);
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
  }

  .watched-badge {
    position: absolute;
    top: var(--spacing-xs);
    right: var(--spacing-xs);
    background: rgba(0, 0, 0, 0.7);
    color: white;
    padding: 2px 8px;
    border-radius: var(--radius-sm);
    font-size: 0.7rem;
  }

  .video-info {
    padding: var(--spacing-md);
  }

  .video-title {
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
    font-weight: 500;
    color: var(--color-text);
    text-decoration: none;
    line-height: 1.4;
    margin-bottom: var(--spacing-xs);
  }

  .video-title:hover {
    color: var(--color-primary);
  }

  .video-meta {
    display: flex;
    flex-wrap: wrap;
    gap: var(--spacing-sm);
    font-size: 0.85rem;
    color: var(--color-text-secondary);
    margin-bottom: var(--spacing-xs);
  }

  .channel-name {
    font-weight: 500;
  }

  .video-date {
    font-size: 0.8rem;
    color: var(--color-text-secondary);
    margin-bottom: var(--spacing-sm);
  }

  .video-actions {
    display: flex;
    gap: var(--spacing-sm);
    flex-wrap: wrap;
  }

  .action-btn {
    padding: var(--spacing-xs) var(--spacing-sm);
    border: none;
    border-radius: var(--radius-sm);
    font-size: 0.8rem;
    font-weight: 500;
    cursor: pointer;
    text-decoration: none;
    display: inline-flex;
    align-items: center;
  }

  .action-btn.watch-toggle {
    background: var(--color-bg);
    color: var(--color-text);
    border: 1px solid var(--color-border);
  }

  .action-btn.watch-toggle:hover {
    background: var(--color-bg-secondary);
  }

  .action-btn.delete {
    background: transparent;
    color: var(--color-error);
    border: 1px solid var(--color-error);
  }

  .action-btn.delete:hover:not(:disabled) {
    background: var(--color-error);
    color: white;
  }

  .action-btn.delete:disabled {
    opacity: 0.5;
  }

  .action-btn.play {
    background: var(--color-primary);
    color: white;
  }

  .action-btn.play:hover {
    opacity: 0.9;
  }

  /* Pagination */
  .pagination {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: var(--spacing-lg);
    margin-top: var(--spacing-xl);
    padding: var(--spacing-lg);
  }

  .page-btn {
    padding: var(--spacing-sm) var(--spacing-lg);
    background: var(--color-bg-secondary);
    color: var(--color-text);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    cursor: pointer;
  }

  .page-btn:hover:not(:disabled) {
    background: var(--color-bg);
  }

  .page-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .page-info {
    color: var(--color-text-secondary);
  }

  /* Mobile */
  @media (max-width: 768px) {
    .page-header {
      flex-direction: column;
    }

    .stats-cards {
      width: 100%;
      justify-content: space-between;
    }

    .filters {
      flex-direction: column;
      gap: var(--spacing-md);
    }

    .filter-group {
      width: 100%;
    }

    .select {
      flex: 1;
    }

    .video-grid {
      grid-template-columns: 1fr;
    }

    .video-actions {
      flex-direction: column;
    }

    .action-btn {
      width: 100%;
      justify-content: center;
    }
  }
</style>
