<script lang="ts">
  import { onMount } from 'svelte';
  import { downloadManager } from '$lib/stores/downloadManager.svelte';
  import {
    listDownloadedVideos,
    deleteVideo,
    clearAllVideos,
    getStorageBreakdown,
    getStorageQuota,
    formatBytes,
    getVideoUrl,
    type DownloadMetadata
  } from '$lib/stores/offlineStorage';
  import { videoPlayer, formatDuration, createOfflineVideoItem } from '$lib/stores/videoPlayer.svelte';

  // State
  let downloads = $state<DownloadMetadata[]>([]);
  let loading = $state(true);
  let storageBreakdown = $state<Awaited<ReturnType<typeof getStorageBreakdown>> | null>(null);
  let storageQuota = $state<Awaited<ReturnType<typeof getStorageQuota>>>(null);
  let filter = $state<'all' | 'videos' | 'podcasts'>('all');
  let confirmClearAll = $state(false);
  let deleting = $state<string | null>(null);

  // Filtered downloads
  let filteredDownloads = $derived(
    downloads.filter(d => {
      if (filter === 'all') return true;
      if (filter === 'podcasts') return d.mediaType === 'podcast_episode' || d.platform === 'podcast';
      return d.mediaType !== 'podcast_episode' && d.platform !== 'podcast';
    })
  );

  onMount(async () => {
    await loadDownloads();
  });

  async function loadDownloads() {
    loading = true;
    try {
      downloads = await listDownloadedVideos();
      storageBreakdown = await getStorageBreakdown();
      storageQuota = await getStorageQuota();
    } catch (e) {
      console.error('Failed to load downloads:', e);
    } finally {
      loading = false;
    }
  }

  async function handleDelete(platform: string, videoId: string) {
    const key = `${platform}:${videoId}`;
    deleting = key;
    try {
      await deleteVideo(platform, videoId);
      downloads = downloads.filter(d => !(d.platform === platform && d.videoId === videoId));
      storageBreakdown = await getStorageBreakdown();
    } catch (e) {
      console.error('Failed to delete:', e);
    } finally {
      deleting = null;
    }
  }

  async function handleClearAll() {
    if (!confirmClearAll) {
      confirmClearAll = true;
      setTimeout(() => confirmClearAll = false, 5000);
      return;
    }

    try {
      await clearAllVideos();
      downloads = [];
      storageBreakdown = await getStorageBreakdown();
      confirmClearAll = false;
    } catch (e) {
      console.error('Failed to clear all:', e);
    }
  }

  async function playOffline(download: DownloadMetadata) {
    try {
      const url = await getVideoUrl(download.platform, download.videoId);
      if (!url) {
        console.error('Could not get video URL');
        return;
      }

      // Create a VideoItem for offline playback
      const videoItem = createOfflineVideoItem(
        download.platform,
        download.videoId,
        download.title,
        download.thumbnailUrl,
        download.duration,
        url,
        download.mediaType
      );

      // Open in the video player
      videoPlayer.openModal(videoItem);
    } catch (e) {
      console.error('Failed to play offline:', e);
    }
  }

  function formatDate(timestamp: number): string {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));

    if (days === 0) return 'Today';
    if (days === 1) return 'Yesterday';
    if (days < 7) return `${days} days ago`;
    return date.toLocaleDateString();
  }

  function getPlatformIcon(platform: string): string {
    switch (platform) {
      case 'youtube': return '📺';
      case 'rumble': return '🎬';
      case 'podcast': return '🎙️';
      default: return '📹';
    }
  }
</script>

<div class="downloads-page">
  <header class="page-header">
    <div class="header-content">
      <h1>Downloads</h1>
      <p class="subtitle">
        {#if storageBreakdown}
          {storageBreakdown.total.count} items using {formatBytes(storageBreakdown.total.size)}
        {:else}
          Your offline content
        {/if}
      </p>
    </div>
    <div class="header-actions">
      {#if downloads.length > 0}
        <button
          class="btn btn-danger"
          class:confirming={confirmClearAll}
          onclick={handleClearAll}
        >
          {confirmClearAll ? 'Click again to confirm' : 'Clear All'}
        </button>
      {/if}
    </div>
  </header>

  <!-- Storage Info -->
  {#if storageBreakdown && storageBreakdown.total.count > 0}
    <div class="storage-info">
      <div class="storage-bar-container">
        <div class="storage-bar">
          {#if storageBreakdown.videos.size > 0}
            <div
              class="storage-segment videos"
              style="width: {(storageBreakdown.videos.size / storageBreakdown.total.size) * 100}%"
              title="{storageBreakdown.videos.count} videos ({formatBytes(storageBreakdown.videos.size)})"
            ></div>
          {/if}
          {#if storageBreakdown.podcasts.size > 0}
            <div
              class="storage-segment podcasts"
              style="width: {(storageBreakdown.podcasts.size / storageBreakdown.total.size) * 100}%"
              title="{storageBreakdown.podcasts.count} podcasts ({formatBytes(storageBreakdown.podcasts.size)})"
            ></div>
          {/if}
        </div>
        {#if storageQuota}
          <div class="quota-info">
            {formatBytes(storageBreakdown.total.size)} / {formatBytes(storageQuota.quota)} available
          </div>
        {/if}
      </div>
      <div class="storage-legend">
        <span class="legend-item videos">
          <span class="legend-color"></span>
          Videos ({storageBreakdown.videos.count})
        </span>
        <span class="legend-item podcasts">
          <span class="legend-color"></span>
          Podcasts ({storageBreakdown.podcasts.count})
        </span>
      </div>
    </div>
  {/if}

  <!-- Filters -->
  {#if downloads.length > 0}
    <div class="filters">
      <button
        class="filter-btn"
        class:active={filter === 'all'}
        onclick={() => filter = 'all'}
      >
        All ({downloads.length})
      </button>
      <button
        class="filter-btn"
        class:active={filter === 'videos'}
        onclick={() => filter = 'videos'}
      >
        Videos ({storageBreakdown?.videos.count ?? 0})
      </button>
      <button
        class="filter-btn"
        class:active={filter === 'podcasts'}
        onclick={() => filter = 'podcasts'}
      >
        Podcasts ({storageBreakdown?.podcasts.count ?? 0})
      </button>
    </div>
  {/if}

  <!-- Content -->
  {#if loading}
    <div class="loading-state">
      <div class="spinner"></div>
      <p>Loading downloads...</p>
    </div>
  {:else if downloads.length === 0}
    <div class="empty-state">
      <div class="empty-icon">📥</div>
      <h2>No Downloads Yet</h2>
      <p>Download videos and podcasts for offline viewing.</p>
      <p class="hint">Look for the download button on video cards in your Feed or Discover.</p>
      <div class="empty-actions">
        <a href="/feed" class="btn btn-primary">Go to Feed</a>
        <a href="/discover" class="btn btn-secondary">Discover Content</a>
      </div>
    </div>
  {:else}
    <div class="downloads-grid">
      {#each filteredDownloads as download}
        {@const key = `${download.platform}:${download.videoId}`}
        <div class="download-card">
          <div class="thumbnail-wrapper">
            <button class="thumbnail" onclick={() => playOffline(download)}>
              {#if download.thumbnailUrl}
                <img src={download.thumbnailUrl} alt={download.title} loading="lazy" />
              {:else}
                <div class="no-thumbnail">
                  <span class="platform-icon">{getPlatformIcon(download.platform)}</span>
                </div>
              {/if}
              <div class="play-overlay">
                <svg viewBox="0 0 24 24" fill="currentColor" width="48" height="48">
                  <path d="M8 5v14l11-7z" />
                </svg>
              </div>
              {#if download.duration}
                <span class="duration">{formatDuration(download.duration)}</span>
              {/if}
              <span class="offline-badge">Offline</span>
            </button>
            <button
              class="delete-btn"
              onclick={() => handleDelete(download.platform, download.videoId)}
              disabled={deleting === key}
              title="Delete download"
            >
              {#if deleting === key}
                <div class="mini-spinner"></div>
              {:else}
                <svg viewBox="0 0 24 24" fill="currentColor" width="16" height="16">
                  <path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z" />
                </svg>
              {/if}
            </button>
          </div>
          <div class="card-content">
            <h3 class="title" title={download.title}>{download.title}</h3>
            <div class="meta">
              <span class="platform">
                {getPlatformIcon(download.platform)} {download.platform}
              </span>
              <span class="separator">·</span>
              <span class="size">{formatBytes(download.fileSize)}</span>
              {#if download.quality}
                <span class="separator">·</span>
                <span class="quality">{download.quality}</span>
              {/if}
            </div>
            <div class="download-date">
              Downloaded {formatDate(download.downloadedAt)}
            </div>
          </div>
        </div>
      {/each}
    </div>
  {/if}

  <!-- Active Downloads -->
  {#if downloadManager.downloads.size > 0}
    <div class="active-downloads">
      <h2>Downloading</h2>
      <div class="active-list">
        {#each [...downloadManager.downloads.values()] as state}
          <div class="active-item">
            <div class="active-info">
              <span class="active-title">{state.title}</span>
              <span class="active-status">
                {#if state.status === 'downloading'}
                  {state.progress}% - {formatBytes(state.downloadedBytes)} / {formatBytes(state.totalBytes)}
                {:else if state.status === 'queued'}
                  Queued...
                {:else if state.status === 'failed'}
                  Failed: {state.error}
                {/if}
              </span>
            </div>
            {#if state.status === 'downloading'}
              <div class="progress-bar">
                <div class="progress-fill" style="width: {state.progress}%"></div>
              </div>
            {/if}
            <button
              class="cancel-btn"
              onclick={() => downloadManager.cancelDownload(state.platform, state.videoId)}
            >
              Cancel
            </button>
          </div>
        {/each}
      </div>
    </div>
  {/if}
</div>

<style>
  .downloads-page {
    max-width: 1400px;
    margin: 0 auto;
  }

  .page-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: var(--spacing-lg);
    flex-wrap: wrap;
    gap: var(--spacing-md);
  }

  .header-content h1 {
    font-size: 2rem;
    margin-bottom: var(--spacing-xs);
  }

  .subtitle {
    color: var(--color-text-secondary);
  }

  .header-actions {
    display: flex;
    gap: var(--spacing-sm);
  }

  .btn {
    padding: var(--spacing-sm) var(--spacing-md);
    border-radius: var(--radius-md);
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s;
    text-decoration: none;
    display: inline-flex;
    align-items: center;
    gap: var(--spacing-xs);
    border: none;
  }

  .btn-primary {
    background: var(--color-primary);
    color: white;
  }

  .btn-primary:hover {
    opacity: 0.9;
  }

  .btn-secondary {
    background: var(--color-bg);
    color: var(--color-text);
    border: 1px solid var(--color-border);
  }

  .btn-secondary:hover {
    background: var(--color-surface);
  }

  .btn-danger {
    background: var(--color-error);
    color: white;
  }

  .btn-danger:hover {
    opacity: 0.9;
  }

  .btn-danger.confirming {
    background: #dc2626;
    animation: pulse 1s infinite;
  }

  @keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.7; }
  }

  /* Storage Info */
  .storage-info {
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-lg);
    padding: var(--spacing-md);
    margin-bottom: var(--spacing-lg);
  }

  .storage-bar-container {
    margin-bottom: var(--spacing-sm);
  }

  .storage-bar {
    height: 8px;
    background: var(--color-bg);
    border-radius: var(--radius-full);
    overflow: hidden;
    display: flex;
  }

  .storage-segment {
    height: 100%;
    transition: width 0.3s ease;
  }

  .storage-segment.videos {
    background: var(--color-primary);
  }

  .storage-segment.podcasts {
    background: #10b981;
  }

  .quota-info {
    font-size: 0.8rem;
    color: var(--color-text-secondary);
    margin-top: var(--spacing-xs);
    text-align: right;
  }

  .storage-legend {
    display: flex;
    gap: var(--spacing-md);
    font-size: 0.85rem;
  }

  .legend-item {
    display: flex;
    align-items: center;
    gap: var(--spacing-xs);
  }

  .legend-color {
    width: 12px;
    height: 12px;
    border-radius: 2px;
  }

  .legend-item.videos .legend-color {
    background: var(--color-primary);
  }

  .legend-item.podcasts .legend-color {
    background: #10b981;
  }

  /* Filters */
  .filters {
    display: flex;
    gap: var(--spacing-xs);
    margin-bottom: var(--spacing-lg);
  }

  .filter-btn {
    padding: var(--spacing-xs) var(--spacing-md);
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    color: var(--color-text-secondary);
    cursor: pointer;
    font-size: 0.9rem;
    transition: all 0.2s;
  }

  .filter-btn:hover {
    border-color: var(--color-primary);
    color: var(--color-text);
  }

  .filter-btn.active {
    background: var(--color-primary);
    border-color: var(--color-primary);
    color: white;
  }

  /* Loading & Empty */
  .loading-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: calc(var(--spacing-xl) * 2);
    color: var(--color-text-secondary);
  }

  .spinner {
    width: 32px;
    height: 32px;
    border: 3px solid var(--color-border);
    border-top-color: var(--color-primary);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
    margin-bottom: var(--spacing-md);
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  .empty-state {
    text-align: center;
    padding: calc(var(--spacing-xl) * 2);
  }

  .empty-icon {
    font-size: 4rem;
    margin-bottom: var(--spacing-md);
  }

  .empty-state h2 {
    margin-bottom: var(--spacing-sm);
  }

  .empty-state p {
    color: var(--color-text-secondary);
    margin-bottom: var(--spacing-sm);
  }

  .hint {
    font-size: 0.9rem;
    opacity: 0.7;
  }

  .empty-actions {
    display: flex;
    gap: var(--spacing-md);
    justify-content: center;
    margin-top: var(--spacing-lg);
  }

  /* Downloads Grid */
  .downloads-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: var(--spacing-lg);
  }

  .download-card {
    background: var(--color-surface);
    border-radius: var(--radius-lg);
    overflow: hidden;
    border: 1px solid var(--color-border);
    transition: transform 0.2s, box-shadow 0.2s;
  }

  .download-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  }

  .thumbnail-wrapper {
    position: relative;
  }

  .thumbnail {
    position: relative;
    aspect-ratio: 16/9;
    background: var(--color-bg);
    width: 100%;
    border: none;
    padding: 0;
    cursor: pointer;
    display: block;
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
    background: var(--color-bg);
  }

  .platform-icon {
    font-size: 3rem;
    opacity: 0.5;
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

  .thumbnail:hover .play-overlay {
    opacity: 1;
  }

  .duration {
    position: absolute;
    bottom: 8px;
    right: 8px;
    background: rgba(0, 0, 0, 0.8);
    color: white;
    font-size: 0.75rem;
    padding: 2px 4px;
    border-radius: var(--radius-sm);
  }

  .offline-badge {
    position: absolute;
    top: 8px;
    left: 8px;
    background: #10b981;
    color: white;
    font-size: 0.7rem;
    padding: 2px 6px;
    border-radius: var(--radius-sm);
    text-transform: uppercase;
    font-weight: 600;
  }

  .delete-btn {
    position: absolute;
    top: 8px;
    right: 8px;
    width: 28px;
    height: 28px;
    border-radius: 50%;
    background: rgba(0, 0, 0, 0.6);
    border: none;
    color: white;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    opacity: 0;
    transition: opacity 0.2s, background 0.2s;
    z-index: 10;
  }

  .download-card:hover .delete-btn {
    opacity: 1;
  }

  .delete-btn:hover {
    background: var(--color-error);
  }

  .delete-btn:disabled {
    cursor: wait;
  }

  .mini-spinner {
    width: 14px;
    height: 14px;
    border: 2px solid rgba(255, 255, 255, 0.3);
    border-top-color: white;
    border-radius: 50%;
    animation: spin 0.6s linear infinite;
  }

  .card-content {
    padding: var(--spacing-md);
  }

  .title {
    font-size: 0.95rem;
    font-weight: 600;
    margin: 0 0 var(--spacing-xs);
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
    line-height: 1.4;
  }

  .meta {
    font-size: 0.8rem;
    color: var(--color-text-secondary);
    margin-bottom: var(--spacing-xs);
  }

  .separator {
    margin: 0 var(--spacing-xs);
  }

  .platform {
    text-transform: capitalize;
  }

  .download-date {
    font-size: 0.75rem;
    color: var(--color-text-secondary);
    opacity: 0.7;
  }

  /* Active Downloads */
  .active-downloads {
    margin-top: var(--spacing-xl);
    padding: var(--spacing-lg);
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-lg);
  }

  .active-downloads h2 {
    font-size: 1.1rem;
    margin: 0 0 var(--spacing-md);
  }

  .active-list {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-md);
  }

  .active-item {
    display: flex;
    align-items: center;
    gap: var(--spacing-md);
    padding: var(--spacing-sm);
    background: var(--color-bg);
    border-radius: var(--radius-md);
  }

  .active-info {
    flex: 1;
    min-width: 0;
  }

  .active-title {
    display: block;
    font-weight: 500;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .active-status {
    font-size: 0.8rem;
    color: var(--color-text-secondary);
  }

  .progress-bar {
    width: 100px;
    height: 4px;
    background: var(--color-border);
    border-radius: var(--radius-full);
    overflow: hidden;
  }

  .progress-fill {
    height: 100%;
    background: var(--color-primary);
    transition: width 0.3s ease;
  }

  .cancel-btn {
    padding: var(--spacing-xs) var(--spacing-sm);
    background: var(--color-error);
    color: white;
    border: none;
    border-radius: var(--radius-sm);
    font-size: 0.8rem;
    cursor: pointer;
  }

  .cancel-btn:hover {
    opacity: 0.9;
  }

  /* Mobile */
  @media (max-width: 768px) {
    .page-header {
      flex-direction: column;
    }

    .downloads-grid {
      grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
      gap: var(--spacing-sm);
    }

    .card-content {
      padding: var(--spacing-sm);
    }

    .title {
      font-size: 0.85rem;
    }

    .delete-btn {
      opacity: 1;
    }

    .storage-legend {
      flex-direction: column;
      gap: var(--spacing-xs);
    }

    .filters {
      overflow-x: auto;
      -webkit-overflow-scrolling: touch;
    }

    .filter-btn {
      white-space: nowrap;
    }
  }
</style>
