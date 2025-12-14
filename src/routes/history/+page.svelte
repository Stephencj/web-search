<script lang="ts">
  import { onMount } from 'svelte';
  import { api, type FeedItem } from '$lib/api/client';
  import { videoPlayer, feedItemToVideoItem, formatDuration, openFeedVideo } from '$lib/stores/videoPlayer.svelte';
  import SaveButton from '$lib/components/SaveButton/SaveButton.svelte';

  let items = $state<FeedItem[]>([]);
  let loading = $state(true);
  let error = $state<string | null>(null);
  let total = $state(0);
  let showCompleted = $state(true);

  onMount(() => {
    loadHistory();
  });

  async function loadHistory() {
    loading = true;
    error = null;
    try {
      const response = await api.getWatchHistory({
        per_page: 100,
        include_completed: showCompleted,
      });
      items = response.items;
      total = response.total;
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to load history';
    } finally {
      loading = false;
    }
  }

  function toggleShowCompleted() {
    showCompleted = !showCompleted;
    loadHistory();
  }

  function playVideo(item: FeedItem) {
    openFeedVideo(item);
  }

  function formatProgress(item: FeedItem): string {
    if (!item.watch_progress_seconds) return '';
    const progress = formatDuration(item.watch_progress_seconds);
    const total = item.duration_seconds ? formatDuration(item.duration_seconds) : '??:??';
    return `${progress} / ${total}`;
  }

  function getProgressPercent(item: FeedItem): number {
    if (!item.watch_progress_seconds || !item.duration_seconds) return 0;
    return Math.min(100, (item.watch_progress_seconds / item.duration_seconds) * 100);
  }

  function formatTimeAgo(dateStr: string): string {
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now.getTime() - date.getTime();
    const diffMins = Math.floor(diffMs / 60000);
    const diffHours = Math.floor(diffMs / 3600000);
    const diffDays = Math.floor(diffMs / 86400000);

    if (diffMins < 1) return 'Just now';
    if (diffMins < 60) return `${diffMins}m ago`;
    if (diffHours < 24) return `${diffHours}h ago`;
    if (diffDays < 7) return `${diffDays}d ago`;
    return date.toLocaleDateString();
  }
</script>

<div class="history-page">
  <header class="page-header">
    <div class="header-content">
      <h1>Watch History</h1>
      <p class="subtitle">Videos you've played or started watching</p>
    </div>
    <div class="header-actions">
      <label class="filter-toggle">
        <input type="checkbox" bind:checked={showCompleted} onchange={toggleShowCompleted} />
        <span>Show completed</span>
      </label>
    </div>
  </header>

  {#if loading}
    <div class="loading">
      <div class="spinner"></div>
      <span>Loading history...</span>
    </div>
  {:else if error}
    <div class="error">{error}</div>
  {:else if items.length === 0}
    <div class="empty-state">
      <div class="empty-icon">📺</div>
      <h2>No watch history yet</h2>
      <p>Videos you play will appear here so you can easily find them again.</p>
    </div>
  {:else}
    <div class="history-stats">
      {total} video{total !== 1 ? 's' : ''} in history
    </div>

    <div class="history-list">
      {#each items as item}
        <div class="history-item" class:watched={item.is_watched}>
          <button class="thumbnail" onclick={() => playVideo(item)}>
            {#if item.thumbnail_url}
              <img src={item.thumbnail_url} alt={item.title} loading="lazy" />
            {:else}
              <div class="no-thumbnail">No Thumbnail</div>
            {/if}
            <div class="play-overlay">
              <svg viewBox="0 0 24 24" fill="currentColor" width="40" height="40">
                <path d="M8 5v14l11-7z" />
              </svg>
            </div>
            {#if item.duration_seconds}
              <span class="duration">{formatDuration(item.duration_seconds)}</span>
            {/if}
            {#if item.watch_progress_seconds && !item.is_watched}
              <div class="progress-bar">
                <div class="progress-fill" style="width: {getProgressPercent(item)}%"></div>
              </div>
            {/if}
            {#if item.is_watched}
              <span class="watched-badge">Watched</span>
            {/if}
          </button>

          <div class="item-info">
            <h3 class="item-title" title={item.title}>{item.title}</h3>
            {#if item.description}
              <p class="item-description">{item.description.slice(0, 100)}{item.description.length > 100 ? '...' : ''}</p>
            {/if}
            <div class="item-meta">
              <span class="channel-name">{item.channel_name}</span>
              <span class="separator">·</span>
              <span class="platform">{item.platform}</span>
              {#if item.watched_at}
                <span class="separator">·</span>
                <span class="watched-time">{formatTimeAgo(item.watched_at)}</span>
              {/if}
            </div>
            {#if item.watch_progress_seconds && !item.is_watched}
              <div class="progress-info">
                <svg viewBox="0 0 24 24" fill="currentColor" width="14" height="14">
                  <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
                </svg>
                <span>{formatProgress(item)}</span>
              </div>
            {/if}
          </div>

          <div class="item-actions">
            <button class="action-btn play" onclick={() => playVideo(item)}>
              {item.watch_progress_seconds && !item.is_watched ? 'Resume' : 'Play'}
            </button>
            <SaveButton
              mediaType="video"
              mediaUrl={item.video_url}
              thumbnailUrl={item.thumbnail_url}
              title={item.title}
              sourceUrl={item.video_url}
              domain={item.platform}
              embedType={item.platform}
              videoId={item.video_id}
            />
          </div>
        </div>
      {/each}
    </div>
  {/if}
</div>

<style>
  .history-page {
    max-width: 1000px;
    margin: 0 auto;
  }

  .page-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: var(--spacing-xl);
    gap: var(--spacing-lg);
  }

  .page-header h1 {
    font-size: 2rem;
    margin: 0 0 var(--spacing-xs) 0;
  }

  .subtitle {
    color: var(--color-text-secondary);
    margin: 0;
  }

  .filter-toggle {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    cursor: pointer;
    font-size: 0.9rem;
    color: var(--color-text-secondary);
  }

  .filter-toggle input {
    cursor: pointer;
  }

  .history-stats {
    color: var(--color-text-secondary);
    font-size: 0.9rem;
    margin-bottom: var(--spacing-md);
  }

  .loading {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: var(--spacing-md);
    padding: var(--spacing-xxl);
    color: var(--color-text-secondary);
  }

  .spinner {
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

  .error {
    padding: var(--spacing-lg);
    background: rgba(239, 68, 68, 0.1);
    color: var(--color-error);
    border-radius: var(--radius-md);
  }

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

  .history-list {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-md);
  }

  .history-item {
    display: flex;
    gap: var(--spacing-md);
    padding: var(--spacing-md);
    background: var(--color-bg-secondary);
    border-radius: var(--radius-lg);
    transition: background 0.2s ease;
  }

  .history-item:hover {
    background: var(--color-bg);
  }

  .history-item.watched {
    opacity: 0.7;
  }

  .history-item.watched:hover {
    opacity: 1;
  }

  .thumbnail {
    position: relative;
    flex-shrink: 0;
    width: 180px;
    aspect-ratio: 16 / 9;
    border-radius: var(--radius-md);
    overflow: hidden;
    background: var(--color-bg);
    border: none;
    padding: 0;
    cursor: pointer;
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
    font-size: 0.8rem;
  }

  .play-overlay {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(0, 0, 0, 0.4);
    color: white;
    opacity: 0;
    transition: opacity 0.2s ease;
  }

  .thumbnail:hover .play-overlay {
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

  .progress-bar {
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    height: 4px;
    background: rgba(255, 255, 255, 0.3);
  }

  .progress-fill {
    height: 100%;
    background: var(--color-primary);
  }

  .watched-badge {
    position: absolute;
    top: var(--spacing-xs);
    left: var(--spacing-xs);
    background: var(--color-success);
    color: white;
    padding: 2px 6px;
    border-radius: var(--radius-sm);
    font-size: 0.65rem;
    font-weight: 600;
    text-transform: uppercase;
  }

  .item-info {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: var(--spacing-xs);
  }

  .item-title {
    font-size: 1rem;
    font-weight: 600;
    margin: 0;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
    line-height: 1.4;
  }

  .item-description {
    font-size: 0.8rem;
    color: var(--color-text-secondary);
    margin: 0;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
    line-height: 1.4;
  }

  .item-meta {
    display: flex;
    align-items: center;
    flex-wrap: wrap;
    gap: var(--spacing-xs);
    font-size: 0.8rem;
    color: var(--color-text-secondary);
  }

  .channel-name {
    font-weight: 500;
  }

  .separator {
    opacity: 0.5;
  }

  .progress-info {
    display: flex;
    align-items: center;
    gap: var(--spacing-xs);
    font-size: 0.8rem;
    color: var(--color-primary);
    margin-top: var(--spacing-xs);
  }

  .item-actions {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-sm);
    align-items: flex-end;
  }

  .action-btn {
    padding: var(--spacing-sm) var(--spacing-md);
    border: none;
    border-radius: var(--radius-md);
    font-size: 0.85rem;
    font-weight: 500;
    cursor: pointer;
    transition: opacity 0.2s ease;
  }

  .action-btn.play {
    background: var(--color-primary);
    color: white;
  }

  .action-btn.play:hover {
    opacity: 0.9;
  }

  /* Mobile */
  @media (max-width: 768px) {
    .page-header {
      flex-direction: column;
      gap: var(--spacing-md);
    }

    .page-header h1 {
      font-size: 1.5rem;
    }

    .history-item {
      flex-direction: column;
    }

    .thumbnail {
      width: 100%;
    }

    .item-actions {
      flex-direction: row;
      width: 100%;
    }

    .action-btn {
      flex: 1;
    }
  }
</style>
