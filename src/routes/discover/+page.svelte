<script lang="ts">
  import { api, type PlatformInfo, type DiscoverVideoResult, type DiscoverChannelResult, type SearchTiming } from '$lib/api/client';
  import { videoPlayer, discoverVideoToVideoItem, formatDuration } from '$lib/stores/videoPlayer.svelte';

  // State
  let platforms = $state<PlatformInfo[]>([]);
  let selectedPlatforms = $state<Set<string>>(new Set());
  let searchQuery = $state('');
  let searchType = $state<'videos' | 'channels'>('videos');
  let searching = $state(false);
  let videoResults = $state<DiscoverVideoResult[]>([]);
  let channelResults = $state<DiscoverChannelResult[]>([]);
  let timings = $state<SearchTiming[]>([]);
  let totalDuration = $state(0);
  let error = $state<string | null>(null);
  let subscribingTo = $state<string | null>(null);
  let subscribeSuccess = $state<string | null>(null);
  let savingVideo = $state<string | null>(null);
  let saveSuccess = $state<string | null>(null);
  let savedVideoIds = $state<Set<string>>(new Set());

  // Load platforms on mount
  $effect(() => {
    loadPlatforms();
  });

  async function loadPlatforms() {
    try {
      const response = await api.listPlatforms();
      platforms = response.platforms;
      // Select all searchable platforms by default
      selectedPlatforms = new Set(platforms.filter(p => p.supports_search).map(p => p.id));
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to load platforms';
    }
  }

  function togglePlatform(platformId: string) {
    const newSet = new Set(selectedPlatforms);
    if (newSet.has(platformId)) {
      newSet.delete(platformId);
    } else {
      newSet.add(platformId);
    }
    selectedPlatforms = newSet;
  }

  function selectAllPlatforms() {
    selectedPlatforms = new Set(platforms.filter(p => p.supports_search).map(p => p.id));
  }

  async function handleSearch() {
    if (!searchQuery.trim()) return;
    if (selectedPlatforms.size === 0) {
      error = 'Please select at least one platform';
      return;
    }

    searching = true;
    error = null;
    videoResults = [];
    channelResults = [];

    try {
      const platformList = Array.from(selectedPlatforms);

      if (searchType === 'videos') {
        const response = await api.discoverVideos({
          query: searchQuery,
          platforms: platformList,
          max_per_platform: 10,
        });
        videoResults = response.results;
        timings = response.timings;
        totalDuration = response.total_duration_ms;
      } else {
        const response = await api.discoverChannels({
          query: searchQuery,
          platforms: platformList,
          max_per_platform: 10,
        });
        channelResults = response.results;
        timings = response.timings;
        totalDuration = response.total_duration_ms;
      }
    } catch (e) {
      error = e instanceof Error ? e.message : 'Search failed';
    } finally {
      searching = false;
    }
  }

  function handleKeydown(event: KeyboardEvent) {
    if (event.key === 'Enter') {
      handleSearch();
    }
  }

  async function subscribeToChannel(channelUrl: string, channelName: string) {
    subscribingTo = channelUrl;
    subscribeSuccess = null;
    try {
      await api.addChannel(channelUrl);
      subscribeSuccess = channelName;
      setTimeout(() => subscribeSuccess = null, 3000);
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to subscribe';
    } finally {
      subscribingTo = null;
    }
  }

  async function saveVideo(video: DiscoverVideoResult) {
    const videoKey = `${video.platform}:${video.video_id}`;
    savingVideo = videoKey;
    saveSuccess = null;
    try {
      await api.saveVideo({
        platform: video.platform,
        video_id: video.video_id,
        video_url: video.video_url,
        title: video.title,
        description: video.description,
        thumbnail_url: video.thumbnail_url,
        duration_seconds: video.duration_seconds,
        view_count: video.view_count,
        upload_date: video.upload_date,
        channel_name: video.channel_name,
        channel_id: video.channel_id,
        channel_url: video.channel_url,
      });
      savedVideoIds = new Set([...savedVideoIds, videoKey]);
      saveSuccess = video.title;
      setTimeout(() => saveSuccess = null, 3000);
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to save video';
    } finally {
      savingVideo = null;
    }
  }

  function isVideoSaved(video: DiscoverVideoResult): boolean {
    return savedVideoIds.has(`${video.platform}:${video.video_id}`);
  }

  function playVideo(video: DiscoverVideoResult) {
    const videoItem = discoverVideoToVideoItem(video);
    videoPlayer.openModal(videoItem);
  }

  function formatCount(count: number | null): string {
    if (!count) return '';
    if (count >= 1_000_000_000) return `${(count / 1_000_000_000).toFixed(1)}B`;
    if (count >= 1_000_000) return `${(count / 1_000_000).toFixed(1)}M`;
    if (count >= 1_000) return `${(count / 1_000).toFixed(1)}K`;
    return count.toString();
  }

  function getPlatformColor(platformId: string): string {
    const platform = platforms.find(p => p.id === platformId);
    return platform?.color || '#666';
  }

  function getPlatformName(platformId: string): string {
    const platform = platforms.find(p => p.id === platformId);
    return platform?.name || platformId;
  }
</script>

<div class="discover-page">
  <header class="page-header">
    <h1>Discover</h1>
    <p class="subtitle">Search across multiple video platforms</p>
  </header>

  <!-- Platform Toggles -->
  <div class="platform-section">
    <div class="platform-header">
      <span class="platform-label">Platforms:</span>
      <button class="select-all-btn" onclick={selectAllPlatforms}>Select All</button>
    </div>
    <div class="platform-toggles">
      {#each platforms.filter(p => p.supports_search) as platform}
        <button
          class="platform-btn"
          class:selected={selectedPlatforms.has(platform.id)}
          onclick={() => togglePlatform(platform.id)}
          style="--platform-color: {platform.color}"
        >
          <span class="platform-icon">{platform.icon}</span>
          <span class="platform-name">{platform.name}</span>
        </button>
      {/each}
    </div>
  </div>

  <!-- Search Bar -->
  <div class="search-section">
    <div class="search-type-tabs">
      <button
        class="type-tab"
        class:active={searchType === 'videos'}
        onclick={() => searchType = 'videos'}
      >
        Videos
      </button>
      <button
        class="type-tab"
        class:active={searchType === 'channels'}
        onclick={() => searchType = 'channels'}
      >
        Channels
      </button>
    </div>
    <div class="search-bar">
      <input
        type="text"
        placeholder="Search across all selected platforms..."
        bind:value={searchQuery}
        onkeydown={handleKeydown}
        class="search-input"
      />
      <button
        class="search-btn"
        onclick={handleSearch}
        disabled={searching || !searchQuery.trim()}
      >
        {searching ? 'Searching...' : 'Search'}
      </button>
    </div>
  </div>

  <!-- Status Messages -->
  {#if error}
    <div class="error-message">{error}</div>
  {/if}

  {#if subscribeSuccess}
    <div class="success-message">Subscribed to {subscribeSuccess}!</div>
  {/if}

  {#if saveSuccess}
    <div class="success-message">Saved "{saveSuccess.slice(0, 50)}{saveSuccess.length > 50 ? '...' : ''}"!</div>
  {/if}

  <!-- Timings -->
  {#if timings.length > 0}
    <div class="timings">
      <span class="timing-total">Total: {totalDuration}ms</span>
      {#each timings as timing}
        <span
          class="timing-badge"
          class:failed={!timing.success}
          style="--platform-color: {getPlatformColor(timing.platform)}"
          title={timing.error || `${timing.duration_ms}ms`}
        >
          {getPlatformName(timing.platform)}: {timing.success ? `${timing.duration_ms}ms` : 'failed'}
        </span>
      {/each}
    </div>
  {/if}

  <!-- Results -->
  <div class="results-section">
    {#if searching}
      <div class="loading">
        <div class="loading-spinner"></div>
        <span>Searching across {selectedPlatforms.size} platforms...</span>
      </div>
    {:else if searchType === 'videos' && videoResults.length > 0}
      <div class="results-count">{videoResults.length} videos found</div>
      <div class="video-grid">
        {#each videoResults as video}
          <div class="video-card">
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
                  {getPlatformName(video.platform)}
                </span>
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
              <div class="video-actions">
                <button
                  class="action-btn save"
                  class:saved={isVideoSaved(video)}
                  onclick={() => saveVideo(video)}
                  disabled={savingVideo === `${video.platform}:${video.video_id}` || isVideoSaved(video)}
                  title={isVideoSaved(video) ? 'Already saved' : 'Save video'}
                >
                  {#if savingVideo === `${video.platform}:${video.video_id}`}
                    ...
                  {:else if isVideoSaved(video)}
                    Saved
                  {:else}
                    Save
                  {/if}
                </button>
                {#if video.channel_url}
                  <button
                    class="action-btn subscribe"
                    onclick={() => subscribeToChannel(video.channel_url!, video.channel_name || 'channel')}
                    disabled={subscribingTo === video.channel_url}
                    title="Subscribe to channel"
                  >
                    {subscribingTo === video.channel_url ? '...' : '+Sub'}
                  </button>
                {/if}
                <button class="action-btn play" onclick={() => playVideo(video)}>
                  Play
                </button>
              </div>
            </div>
          </div>
        {/each}
      </div>
    {:else if searchType === 'channels' && channelResults.length > 0}
      <div class="results-count">{channelResults.length} channels found</div>
      <div class="channel-grid">
        {#each channelResults as channel}
          <div class="channel-card">
            <div class="channel-avatar">
              {#if channel.avatar_url}
                <img src={channel.avatar_url} alt={channel.name} />
              {:else}
                <div class="no-avatar">{channel.name.charAt(0).toUpperCase()}</div>
              {/if}
            </div>
            <div class="channel-info">
              <a href={channel.channel_url} target="_blank" rel="noopener noreferrer" class="channel-name-link">
                {channel.name}
              </a>
              <span class="channel-platform" style="color: {getPlatformColor(channel.platform)}">
                {getPlatformName(channel.platform)}
              </span>
              <div class="channel-stats">
                {#if channel.subscriber_count}
                  <span>{formatCount(channel.subscriber_count)} subscribers</span>
                {/if}
                {#if channel.video_count}
                  <span>{formatCount(channel.video_count)} videos</span>
                {/if}
              </div>
              {#if channel.description}
                <p class="channel-desc">{channel.description.slice(0, 150)}{channel.description.length > 150 ? '...' : ''}</p>
              {/if}
            </div>
            <div class="channel-actions">
              <button
                class="action-btn subscribe"
                onclick={() => subscribeToChannel(channel.channel_url, channel.name)}
                disabled={subscribingTo === channel.channel_url}
              >
                {subscribingTo === channel.channel_url ? 'Subscribing...' : 'Subscribe'}
              </button>
            </div>
          </div>
        {/each}
      </div>
    {:else if !searching && (videoResults.length === 0 && channelResults.length === 0) && searchQuery}
      <div class="no-results">
        <p>No results found for "{searchQuery}"</p>
        <p class="hint">Try different keywords or select more platforms</p>
      </div>
    {:else}
      <div class="empty-state">
        <div class="empty-icon">🌐</div>
        <h2>Search Across Platforms</h2>
        <p>Search for videos or channels across YouTube, Rumble, Odysee, BitChute, and Dailymotion simultaneously.</p>
        <p class="hint">Select platforms above and enter your search query</p>
      </div>
    {/if}
  </div>
</div>

<style>
  .discover-page {
    max-width: 1400px;
    margin: 0 auto;
  }

  .page-header {
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

  /* Platform Section */
  .platform-section {
    margin-bottom: var(--spacing-lg);
  }

  .platform-header {
    display: flex;
    align-items: center;
    gap: var(--spacing-md);
    margin-bottom: var(--spacing-sm);
  }

  .platform-label {
    font-weight: 500;
  }

  .select-all-btn {
    font-size: 0.75rem;
    padding: var(--spacing-xs) var(--spacing-sm);
    background: var(--color-bg-secondary);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-sm);
    color: var(--color-text-secondary);
    cursor: pointer;
  }

  .select-all-btn:hover {
    background: var(--color-bg);
  }

  .platform-toggles {
    display: flex;
    flex-wrap: wrap;
    gap: var(--spacing-sm);
  }

  .platform-btn {
    display: flex;
    align-items: center;
    gap: var(--spacing-xs);
    padding: var(--spacing-sm) var(--spacing-md);
    background: var(--color-bg-secondary);
    border: 2px solid var(--color-border);
    border-radius: var(--radius-md);
    cursor: pointer;
    transition: all 0.2s ease;
  }

  .platform-btn:hover {
    border-color: var(--platform-color);
  }

  .platform-btn.selected {
    background: var(--platform-color);
    border-color: var(--platform-color);
    color: white;
  }

  .platform-icon {
    font-size: 1.25rem;
  }

  .platform-name {
    font-weight: 500;
  }

  /* Search Section */
  .search-section {
    margin-bottom: var(--spacing-lg);
  }

  .search-type-tabs {
    display: flex;
    gap: var(--spacing-xs);
    margin-bottom: var(--spacing-sm);
  }

  .type-tab {
    padding: var(--spacing-sm) var(--spacing-md);
    background: var(--color-bg-secondary);
    border: none;
    border-radius: var(--radius-md) var(--radius-md) 0 0;
    cursor: pointer;
    color: var(--color-text-secondary);
    font-weight: 500;
  }

  .type-tab.active {
    background: var(--color-primary);
    color: white;
  }

  .search-bar {
    display: flex;
    gap: var(--spacing-sm);
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

  .search-btn {
    padding: var(--spacing-md) var(--spacing-xl);
    background: var(--color-primary);
    color: white;
    border: none;
    border-radius: var(--radius-md);
    font-weight: 600;
    cursor: pointer;
    white-space: nowrap;
  }

  .search-btn:hover:not(:disabled) {
    opacity: 0.9;
  }

  .search-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  /* Messages */
  .error-message {
    padding: var(--spacing-md);
    background: rgba(239, 68, 68, 0.1);
    color: var(--color-error);
    border-radius: var(--radius-md);
    margin-bottom: var(--spacing-md);
  }

  .success-message {
    padding: var(--spacing-md);
    background: rgba(34, 197, 94, 0.1);
    color: var(--color-success);
    border-radius: var(--radius-md);
    margin-bottom: var(--spacing-md);
  }

  /* Timings */
  .timings {
    display: flex;
    flex-wrap: wrap;
    gap: var(--spacing-sm);
    margin-bottom: var(--spacing-lg);
    font-size: 0.75rem;
  }

  .timing-total {
    font-weight: 600;
    color: var(--color-text);
  }

  .timing-badge {
    padding: var(--spacing-xs) var(--spacing-sm);
    background: var(--color-bg-secondary);
    border-radius: var(--radius-sm);
    border-left: 3px solid var(--platform-color);
  }

  .timing-badge.failed {
    color: var(--color-error);
    border-left-color: var(--color-error);
  }

  /* Results */
  .results-section {
    min-height: 300px;
  }

  .results-count {
    color: var(--color-text-secondary);
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
    background: var(--color-bg);
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
    margin-bottom: var(--spacing-sm);
  }

  .channel-name {
    font-weight: 500;
  }

  .video-actions {
    display: flex;
    gap: var(--spacing-sm);
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

  .action-btn.save {
    background: var(--color-success);
    color: white;
  }

  .action-btn.save:hover:not(:disabled) {
    opacity: 0.9;
  }

  .action-btn.save:disabled {
    opacity: 0.5;
  }

  .action-btn.save.saved {
    background: var(--color-bg-secondary);
    color: var(--color-text-secondary);
    cursor: default;
  }

  .action-btn.subscribe {
    background: var(--color-primary);
    color: white;
  }

  .action-btn.subscribe:hover:not(:disabled) {
    opacity: 0.9;
  }

  .action-btn.subscribe:disabled {
    opacity: 0.5;
  }

  .action-btn.play {
    background: var(--color-bg);
    color: var(--color-text);
    border: 1px solid var(--color-border);
  }

  .action-btn.play:hover {
    background: var(--color-bg-secondary);
  }

  /* Channel Grid */
  .channel-grid {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-md);
  }

  .channel-card {
    display: flex;
    gap: var(--spacing-md);
    padding: var(--spacing-md);
    background: var(--color-bg-secondary);
    border-radius: var(--radius-lg);
  }

  .channel-avatar {
    flex-shrink: 0;
    width: 80px;
    height: 80px;
    border-radius: 50%;
    overflow: hidden;
    background: var(--color-bg);
  }

  .channel-avatar img {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }

  .no-avatar {
    width: 100%;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 2rem;
    font-weight: 600;
    color: var(--color-text-secondary);
    background: var(--color-bg);
  }

  .channel-info {
    flex: 1;
    min-width: 0;
  }

  .channel-name-link {
    display: block;
    font-size: 1.1rem;
    font-weight: 600;
    color: var(--color-text);
    text-decoration: none;
    margin-bottom: var(--spacing-xs);
  }

  .channel-name-link:hover {
    color: var(--color-primary);
  }

  .channel-platform {
    font-size: 0.8rem;
    font-weight: 500;
    margin-bottom: var(--spacing-xs);
  }

  .channel-stats {
    display: flex;
    gap: var(--spacing-md);
    font-size: 0.85rem;
    color: var(--color-text-secondary);
    margin-bottom: var(--spacing-xs);
  }

  .channel-desc {
    font-size: 0.9rem;
    color: var(--color-text-secondary);
    line-height: 1.4;
    margin: 0;
  }

  .channel-actions {
    display: flex;
    align-items: flex-start;
  }

  /* Empty States */
  .no-results, .empty-state {
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

  .hint {
    font-size: 0.9rem;
    opacity: 0.7;
  }

  /* Mobile */
  @media (max-width: 768px) {
    .search-bar {
      flex-direction: column;
    }

    .search-btn {
      width: 100%;
    }

    .video-grid {
      grid-template-columns: 1fr;
    }

    .channel-card {
      flex-direction: column;
      align-items: center;
      text-align: center;
    }

    .channel-stats {
      justify-content: center;
    }
  }
</style>
