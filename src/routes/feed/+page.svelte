<script lang="ts">
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import {
    api,
    type FeedItem,
    type FeedResponse,
    type ChannelGroupedFeed,
    type FeedStats,
  } from '$lib/api/client';
  import { videoPlayer, feedItemToVideoItem, formatDuration } from '$lib/stores/videoPlayer.svelte';

  // View mode
  let viewMode = $state<'chronological' | 'by_channel'>('chronological');

  // Filters
  let filterStatus = $state<'all' | 'unwatched' | 'watched'>('unwatched');
  let platformFilter = $state<'all' | 'youtube' | 'rumble'>('all');
  let channelId = $state<number | null>(null);

  // Data
  let feedItems = $state<FeedItem[]>([]);
  let groupedFeed = $state<ChannelGroupedFeed[]>([]);
  let stats = $state<FeedStats | null>(null);
  let loading = $state(true);
  let loadingMore = $state(false);
  let error = $state<string | null>(null);

  // Pagination
  let currentPage = $state(1);
  let hasMore = $state(false);
  let totalItems = $state(0);
  const perPage = 24;

  // Syncing
  let syncing = $state(false);

  onMount(() => {
    // Check for channel_id in URL
    const urlChannelId = $page.url.searchParams.get('channel_id');
    if (urlChannelId) {
      channelId = parseInt(urlChannelId, 10);
    }
    loadFeed();
    loadStats();
  });

  async function loadFeed() {
    loading = true;
    error = null;
    currentPage = 1;
    try {
      if (viewMode === 'chronological') {
        const params: Parameters<typeof api.getFeed>[0] = {
          filter: filterStatus,
          page: 1,
          per_page: perPage,
        };
        if (platformFilter !== 'all') params.platform = platformFilter;
        if (channelId) params.channel_id = channelId;

        const response = await api.getFeed(params);
        feedItems = response.items;
        hasMore = response.has_more;
        totalItems = response.total;
      } else {
        const params: Parameters<typeof api.getFeedByChannel>[0] = {
          filter: filterStatus,
        };
        if (platformFilter !== 'all') params.platform = platformFilter;

        const response = await api.getFeedByChannel(params);
        groupedFeed = response.channels;
      }
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to load feed';
    } finally {
      loading = false;
    }
  }

  async function loadMore() {
    if (loadingMore || !hasMore || viewMode !== 'chronological') return;

    loadingMore = true;
    try {
      const params: Parameters<typeof api.getFeed>[0] = {
        filter: filterStatus,
        page: currentPage + 1,
        per_page: perPage,
      };
      if (platformFilter !== 'all') params.platform = platformFilter;
      if (channelId) params.channel_id = channelId;

      const response = await api.getFeed(params);
      feedItems = [...feedItems, ...response.items];
      currentPage = response.page;
      hasMore = response.has_more;
    } catch (e) {
      console.error('Load more failed:', e);
    } finally {
      loadingMore = false;
    }
  }

  async function loadStats() {
    try {
      stats = await api.getFeedStats();
    } catch (e) {
      console.error('Failed to load stats:', e);
    }
  }

  async function handleSync() {
    syncing = true;
    try {
      await api.syncAllFeeds();
      await loadFeed();
      await loadStats();
    } catch (e) {
      console.error('Sync failed:', e);
    } finally {
      syncing = false;
    }
  }

  async function handleMarkWatched(item: FeedItem) {
    try {
      const updated = await api.markFeedItemWatched(item.id);
      updateItemInList(updated);
      if (stats) {
        stats = {
          ...stats,
          unwatched_videos: stats.unwatched_videos - 1,
          watched_videos: stats.watched_videos + 1,
        };
      }
    } catch (e) {
      console.error('Mark watched failed:', e);
    }
  }

  async function handleMarkUnwatched(item: FeedItem) {
    try {
      const updated = await api.markFeedItemUnwatched(item.id);
      updateItemInList(updated);
      if (stats) {
        stats = {
          ...stats,
          unwatched_videos: stats.unwatched_videos + 1,
          watched_videos: stats.watched_videos - 1,
        };
      }
    } catch (e) {
      console.error('Mark unwatched failed:', e);
    }
  }

  function updateItemInList(updated: FeedItem) {
    feedItems = feedItems.map((i) => (i.id === updated.id ? { ...i, ...updated } : i));
    // Also update in grouped view if present
    groupedFeed = groupedFeed.map((group) => ({
      ...group,
      items: group.items.map((i) => (i.id === updated.id ? { ...i, ...updated } : i)),
    }));
  }

  function playVideo(item: FeedItem) {
    const videoItem = feedItemToVideoItem(item);
    videoPlayer.openModal(videoItem);
    // Mark as watched when playing
    if (!item.is_watched) {
      handleMarkWatched(item);
    }
  }

  function formatTimeAgo(dateStr: string): string {
    const date = new Date(dateStr);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));

    if (days === 0) return 'Today';
    if (days === 1) return 'Yesterday';
    if (days < 7) return `${days} days ago`;
    if (days < 30) return `${Math.floor(days / 7)} weeks ago`;
    if (days < 365) return `${Math.floor(days / 30)} months ago`;
    return `${Math.floor(days / 365)} years ago`;
  }

  function clearChannelFilter() {
    channelId = null;
    // Update URL
    const url = new URL(window.location.href);
    url.searchParams.delete('channel_id');
    window.history.replaceState({}, '', url);
    loadFeed();
  }

  // Reload when filters change
  $effect(() => {
    if (filterStatus || platformFilter || viewMode) {
      loadFeed();
    }
  });
</script>

<div class="feed-page">
  <header class="page-header">
    <div class="header-content">
      <h1>Feed</h1>
      <p class="subtitle">
        {#if stats}
          {stats.unwatched_videos} unwatched of {stats.total_videos} videos from {stats.total_channels}
          channels
        {:else}
          Your personal video feed
        {/if}
      </p>
    </div>
    <div class="header-actions">
      <button class="btn btn-secondary" onclick={handleSync} disabled={syncing}>
        <svg
          viewBox="0 0 24 24"
          fill="currentColor"
          width="18"
          height="18"
          class:spinning={syncing}
        >
          <path
            d="M12 4V1L8 5l4 4V6c3.31 0 6 2.69 6 6 0 1.01-.25 1.97-.7 2.8l1.46 1.46C19.54 15.03 20 13.57 20 12c0-4.42-3.58-8-8-8zm0 14c-3.31 0-6-2.69-6-6 0-1.01.25-1.97.7-2.8L5.24 7.74C4.46 8.97 4 10.43 4 12c0 4.42 3.58 8 8 8v3l4-4-4-4v3z"
          />
        </svg>
        {syncing ? 'Syncing...' : 'Sync'}
      </button>
      <a href="/subscriptions" class="btn btn-primary">Manage Subscriptions</a>
    </div>
  </header>

  <!-- Filters and View Toggle -->
  <div class="controls">
    <div class="view-toggle">
      <button
        class="toggle-btn"
        class:active={viewMode === 'chronological'}
        onclick={() => (viewMode = 'chronological')}
      >
        <svg viewBox="0 0 24 24" fill="currentColor" width="18" height="18">
          <path d="M4 6h16v2H4V6zm0 5h16v2H4v-2zm0 5h16v2H4v-2z" />
        </svg>
        Timeline
      </button>
      <button
        class="toggle-btn"
        class:active={viewMode === 'by_channel'}
        onclick={() => (viewMode = 'by_channel')}
      >
        <svg viewBox="0 0 24 24" fill="currentColor" width="18" height="18">
          <path d="M4 8h4V4H4v4zm6 12h4v-4h-4v4zm-6 0h4v-4H4v4zm0-6h4v-4H4v4zm6 0h4v-4h-4v4zm6-10v4h4V4h-4zm-6 4h4V4h-4v4zm6 6h4v-4h-4v4zm0 6h4v-4h-4v4z" />
        </svg>
        By Channel
      </button>
    </div>

    <div class="filters">
      <div class="filter-group">
        <select bind:value={filterStatus} class="select">
          <option value="unwatched">Unwatched</option>
          <option value="all">All Videos</option>
          <option value="watched">Watched</option>
        </select>
      </div>
      <div class="filter-group">
        <select bind:value={platformFilter} class="select">
          <option value="all">All Platforms</option>
          <option value="youtube">YouTube</option>
          <option value="rumble">Rumble</option>
        </select>
      </div>
    </div>

    {#if channelId}
      <button class="filter-chip" onclick={clearChannelFilter}>
        Filtered by channel
        <svg viewBox="0 0 24 24" fill="currentColor" width="16" height="16">
          <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z" />
        </svg>
      </button>
    {/if}
  </div>

  {#if error}
    <div class="error-message">{error}</div>
  {/if}

  {#if loading}
    <div class="loading-state">
      <div class="spinner"></div>
      <p>Loading feed...</p>
    </div>
  {:else if viewMode === 'chronological'}
    {#if feedItems.length === 0}
      <div class="empty-state">
        <div class="empty-icon">
          <svg viewBox="0 0 24 24" fill="currentColor" width="64" height="64">
            <path d="M21 3H3c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h18c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm0 16H3V5h18v14zM8 15l4.5-6 3.5 4.5 2.5-3L21 15H8z" />
          </svg>
        </div>
        <h2>No Videos Found</h2>
        <p>
          {#if filterStatus === 'unwatched'}
            You're all caught up! No unwatched videos.
          {:else if filterStatus === 'watched'}
            No watched videos yet.
          {:else}
            No videos in your feed. Add some channels to get started.
          {/if}
        </p>
        <a href="/subscriptions" class="btn btn-primary">Add Channels</a>
      </div>
    {:else}
      <div class="video-grid">
        {#each feedItems as item}
          <div class="video-card" class:watched={item.is_watched}>
            <button class="card-thumbnail" onclick={() => playVideo(item)}>
              {#if item.thumbnail_url}
                <img src={item.thumbnail_url} alt={item.title} loading="lazy" />
              {:else}
                <div class="no-thumbnail">
                  <svg viewBox="0 0 24 24" fill="currentColor" width="48" height="48">
                    <path d="M8 5v14l11-7z" />
                  </svg>
                </div>
              {/if}
              <div class="play-overlay">
                <svg viewBox="0 0 24 24" fill="currentColor" width="48" height="48">
                  <path d="M8 5v14l11-7z" />
                </svg>
              </div>
              {#if item.duration_seconds}
                <span class="duration">{formatDuration(item.duration_seconds)}</span>
              {/if}
              {#if item.is_watched}
                <span class="watched-badge">Watched</span>
              {/if}
            </button>
            <div class="card-content">
              <h3 class="video-title" title={item.title}>{item.title}</h3>
              <div class="video-meta">
                <span class="channel-name">{item.channel_name}</span>
                <span class="separator">·</span>
                <span class="upload-date">{formatTimeAgo(item.upload_date)}</span>
              </div>
              <div class="card-actions">
                <span class="platform-badge" class:youtube={item.platform === 'youtube'}>
                  {item.platform}
                </span>
                {#if item.is_watched}
                  <button
                    class="action-btn-sm"
                    title="Mark as unwatched"
                    onclick={() => handleMarkUnwatched(item)}
                  >
                    <svg viewBox="0 0 24 24" fill="currentColor" width="16" height="16">
                      <path d="M12 4.5C7 4.5 2.73 7.61 1 12c1.73 4.39 6 7.5 11 7.5s9.27-3.11 11-7.5c-1.73-4.39-6-7.5-11-7.5zM12 17c-2.76 0-5-2.24-5-5s2.24-5 5-5 5 2.24 5 5-2.24 5-5 5zm0-8c-1.66 0-3 1.34-3 3s1.34 3 3 3 3-1.34 3-3-1.34-3-3-3z" />
                    </svg>
                  </button>
                {:else}
                  <button
                    class="action-btn-sm"
                    title="Mark as watched"
                    onclick={() => handleMarkWatched(item)}
                  >
                    <svg viewBox="0 0 24 24" fill="currentColor" width="16" height="16">
                      <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z" />
                    </svg>
                  </button>
                {/if}
              </div>
            </div>
          </div>
        {/each}
      </div>

      {#if hasMore}
        <div class="load-more">
          <button class="btn btn-secondary" onclick={loadMore} disabled={loadingMore}>
            {loadingMore ? 'Loading...' : 'Load More'}
          </button>
        </div>
      {/if}
    {/if}
  {:else}
    <!-- By Channel View -->
    {#if groupedFeed.length === 0}
      <div class="empty-state">
        <h2>No Channels</h2>
        <p>Add some channels to see your feed organized by creator.</p>
        <a href="/subscriptions" class="btn btn-primary">Add Channels</a>
      </div>
    {:else}
      <div class="channel-groups">
        {#each groupedFeed as group}
          <div class="channel-group">
            <div class="group-header">
              <div class="group-avatar">
                {#if group.channel_avatar_url}
                  <img src={group.channel_avatar_url} alt={group.channel_name} />
                {:else}
                  <div class="avatar-placeholder" style="background-color: {group.platform === 'youtube' ? '#ff0000' : '#85c742'}">
                    {group.platform === 'youtube' ? 'YT' : 'R'}
                  </div>
                {/if}
              </div>
              <div class="group-info">
                <h3>{group.channel_name}</h3>
                <span class="group-meta">
                  {group.unwatched_count} unwatched of {group.total_items}
                </span>
              </div>
              <a href="/feed?channel_id={group.channel_id}" class="btn btn-secondary btn-sm">
                View All
              </a>
            </div>
            <div class="group-videos">
              {#each group.items.slice(0, 4) as item}
                <button class="mini-video-card" onclick={() => playVideo(item)}>
                  <div class="mini-thumbnail">
                    {#if item.thumbnail_url}
                      <img src={item.thumbnail_url} alt={item.title} loading="lazy" />
                    {:else}
                      <div class="no-thumbnail">
                        <svg viewBox="0 0 24 24" fill="currentColor" width="24" height="24">
                          <path d="M8 5v14l11-7z" />
                        </svg>
                      </div>
                    {/if}
                    {#if item.is_watched}
                      <span class="watched-indicator"></span>
                    {/if}
                  </div>
                  <span class="mini-title">{item.title}</span>
                </button>
              {/each}
            </div>
          </div>
        {/each}
      </div>
    {/if}
  {/if}
</div>

<style>
  .feed-page {
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
    align-items: center;
  }

  .header-actions .btn {
    display: flex;
    align-items: center;
    gap: var(--spacing-xs);
  }

  .controls {
    display: flex;
    gap: var(--spacing-lg);
    margin-bottom: var(--spacing-lg);
    flex-wrap: wrap;
    align-items: center;
  }

  .view-toggle {
    display: flex;
    background: var(--color-surface);
    border-radius: var(--radius-md);
    overflow: hidden;
    border: 1px solid var(--color-border);
  }

  .toggle-btn {
    display: flex;
    align-items: center;
    gap: var(--spacing-xs);
    padding: var(--spacing-sm) var(--spacing-md);
    background: transparent;
    border: none;
    cursor: pointer;
    color: var(--color-text-secondary);
    transition: all 0.2s;
  }

  .toggle-btn:hover {
    background: var(--color-bg);
  }

  .toggle-btn.active {
    background: var(--color-primary);
    color: white;
  }

  .filters {
    display: flex;
    gap: var(--spacing-sm);
  }

  .select {
    padding: var(--spacing-xs) var(--spacing-sm);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    background: var(--color-bg);
    color: var(--color-text);
  }

  .filter-chip {
    display: flex;
    align-items: center;
    gap: var(--spacing-xs);
    padding: var(--spacing-xs) var(--spacing-sm);
    background: var(--color-primary);
    color: white;
    border: none;
    border-radius: var(--radius-md);
    cursor: pointer;
    font-size: 0.85rem;
  }

  .filter-chip:hover {
    opacity: 0.9;
  }

  .error-message {
    background: #fef2f2;
    color: var(--color-error);
    padding: var(--spacing-md);
    border-radius: var(--radius-md);
    margin-bottom: var(--spacing-lg);
  }

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

  .spinning {
    animation: spin 0.8s linear infinite;
  }

  .empty-state {
    text-align: center;
    padding: calc(var(--spacing-xl) * 2);
  }

  .empty-icon {
    color: var(--color-text-secondary);
    opacity: 0.5;
    margin-bottom: var(--spacing-lg);
  }

  .empty-state h2 {
    margin-bottom: var(--spacing-sm);
  }

  .empty-state p {
    color: var(--color-text-secondary);
    margin-bottom: var(--spacing-lg);
  }

  /* Video Grid */
  .video-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: var(--spacing-lg);
  }

  .video-card {
    background: var(--color-surface);
    border-radius: var(--radius-lg);
    overflow: hidden;
    border: 1px solid var(--color-border);
    transition: transform 0.2s, box-shadow 0.2s;
  }

  .video-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  }

  .video-card.watched {
    opacity: 0.7;
  }

  .card-thumbnail {
    position: relative;
    aspect-ratio: 16/9;
    background: var(--color-bg);
    width: 100%;
    border: none;
    padding: 0;
    cursor: pointer;
    display: block;
  }

  .card-thumbnail img {
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
    opacity: 0.3;
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

  .card-thumbnail:hover .play-overlay {
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

  .watched-badge {
    position: absolute;
    top: 8px;
    left: 8px;
    background: var(--color-success);
    color: white;
    font-size: 0.7rem;
    padding: 2px 6px;
    border-radius: var(--radius-sm);
    text-transform: uppercase;
    font-weight: 600;
  }

  .card-content {
    padding: var(--spacing-md);
  }

  .video-title {
    font-size: 0.95rem;
    font-weight: 600;
    margin: 0 0 var(--spacing-xs);
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
    line-height: 1.4;
  }

  .video-meta {
    font-size: 0.8rem;
    color: var(--color-text-secondary);
    margin-bottom: var(--spacing-sm);
  }

  .channel-name {
    font-weight: 500;
  }

  .separator {
    margin: 0 var(--spacing-xs);
  }

  .card-actions {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .platform-badge {
    font-size: 0.65rem;
    padding: 2px 6px;
    border-radius: var(--radius-sm);
    background: #85c742;
    color: white;
    text-transform: uppercase;
    font-weight: 600;
  }

  .platform-badge.youtube {
    background: #ff0000;
  }

  .action-btn-sm {
    background: var(--color-bg);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-sm);
    padding: 4px;
    cursor: pointer;
    color: var(--color-text-secondary);
    transition: all 0.2s;
  }

  .action-btn-sm:hover {
    background: var(--color-surface);
    color: var(--color-text);
  }

  .load-more {
    text-align: center;
    margin-top: var(--spacing-xl);
  }

  /* Channel Groups View */
  .channel-groups {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-xl);
  }

  .channel-group {
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-lg);
    padding: var(--spacing-lg);
  }

  .group-header {
    display: flex;
    align-items: center;
    gap: var(--spacing-md);
    margin-bottom: var(--spacing-md);
  }

  .group-avatar {
    width: 48px;
    height: 48px;
    border-radius: 50%;
    overflow: hidden;
    flex-shrink: 0;
  }

  .group-avatar img {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }

  .avatar-placeholder {
    width: 100%;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-weight: bold;
  }

  .group-info {
    flex: 1;
  }

  .group-info h3 {
    font-size: 1.1rem;
    margin: 0;
  }

  .group-meta {
    font-size: 0.85rem;
    color: var(--color-text-secondary);
  }

  .btn-sm {
    padding: var(--spacing-xs) var(--spacing-sm);
    font-size: 0.85rem;
  }

  .group-videos {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: var(--spacing-md);
  }

  .mini-video-card {
    background: none;
    border: none;
    padding: 0;
    cursor: pointer;
    text-align: left;
  }

  .mini-thumbnail {
    position: relative;
    aspect-ratio: 16/9;
    background: var(--color-bg);
    border-radius: var(--radius-md);
    overflow: hidden;
    margin-bottom: var(--spacing-xs);
  }

  .mini-thumbnail img {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }

  .watched-indicator {
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    height: 3px;
    background: var(--color-success);
  }

  .mini-title {
    font-size: 0.8rem;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
    color: var(--color-text);
  }

  /* Button styles */
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
  }

  .btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .btn-primary {
    background: var(--color-primary);
    color: white;
    border: none;
  }

  .btn-primary:hover:not(:disabled) {
    opacity: 0.9;
  }

  .btn-secondary {
    background: var(--color-bg);
    color: var(--color-text);
    border: 1px solid var(--color-border);
  }

  .btn-secondary:hover:not(:disabled) {
    background: var(--color-surface);
  }

  /* Mobile Styles */
  @media (max-width: 768px) {
    .page-header {
      display: none;
    }

    .controls {
      flex-direction: column;
      gap: var(--spacing-sm);
    }

    .view-toggle {
      width: 100%;
    }

    .toggle-btn {
      flex: 1;
      justify-content: center;
    }

    .filters {
      width: 100%;
    }

    .filters .select {
      flex: 1;
    }

    .video-grid {
      grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
      gap: var(--spacing-sm);
    }

    .card-content {
      padding: var(--spacing-sm);
    }

    .video-title {
      font-size: 0.85rem;
      -webkit-line-clamp: 2;
    }

    .video-meta {
      font-size: 0.75rem;
    }

    .group-videos {
      grid-template-columns: repeat(2, 1fr);
    }
  }

  @media (max-width: 480px) {
    .video-grid {
      grid-template-columns: 1fr;
    }

    .card-thumbnail {
      aspect-ratio: 16/9;
    }

    .group-videos {
      grid-template-columns: 1fr 1fr;
      gap: var(--spacing-sm);
    }
  }
</style>
