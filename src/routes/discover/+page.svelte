<script lang="ts">
  import { page } from '$app/stores';
  import { api, type PlatformInfo, type DiscoverVideoResult, type DiscoverChannelResult, type SearchTiming, type WatchStateItem } from '$lib/api/client';
  import { videoPlayer, discoverVideoToVideoItem, formatDuration } from '$lib/stores/videoPlayer.svelte';
  import { hiddenChannelsStore } from '$lib/stores/hiddenChannels.svelte';
  import SaveButton from '$lib/components/SaveButton/SaveButton.svelte';
  import HideButton from '$lib/components/HideButton/HideButton.svelte';
  import DownloadButton from '$lib/components/DownloadButton.svelte';

  // State
  let platforms = $state<PlatformInfo[]>([]);
  let selectedPlatforms = $state<Set<string>>(new Set(['youtube']));
  let searchQuery = $state('');
  let searchType = $state<'videos' | 'channels'>('videos');
  let searching = $state(false);
  let loadingMore = $state(false);
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

  // Watch state filter
  let watchFilter = $state<'all' | 'unwatched'>('all');
  let watchStates = $state<Map<string, WatchStateItem>>(new Map());

  // Pagination for infinite scroll
  let currentPage = $state(1);
  let hasMore = $state(true);
  let resultsPerPage = 20;

  // Mood/category state - influences search queries
  type MoodType = 'focus_learning' | 'stay_positive' | 'music_mode' | 'news_politics' | 'gaming' | null;
  const MOOD_OPTIONS: { id: Exclude<MoodType, null>; label: string; icon: string; description: string; searchTerms: string[] }[] = [
    { id: 'focus_learning', label: 'Focus & Learning', icon: '📚', description: 'Education, Science, How-to',
      searchTerms: ['educational documentary', 'science explained', 'how to tutorial', 'learn new skill', 'TED talk', 'deep dive', 'explained'] },
    { id: 'stay_positive', label: 'Stay Positive', icon: '😄', description: 'Comedy, Entertainment',
      searchTerms: ['comedy sketch', 'funny compilation', 'stand up comedy', 'wholesome content', 'feel good video', 'comedy show', 'funny moments'] },
    { id: 'music_mode', label: 'Music Mode', icon: '🎵', description: 'Music videos & performances',
      searchTerms: ['music video official', 'live performance concert', 'acoustic cover', 'new music 2024', 'music mix', 'live session', 'music reaction'] },
    { id: 'news_politics', label: 'News & Politics', icon: '📰', description: 'Current events, Politics',
      searchTerms: ['news analysis', 'political commentary', 'current events', 'interview politics', 'documentary news', 'breaking news', 'political debate'] },
    { id: 'gaming', label: 'Gaming', icon: '🎮', description: 'Gaming content',
      searchTerms: ['gameplay walkthrough', 'gaming highlights', 'game review', 'esports', 'lets play', 'game stream', 'gaming news'] },
  ];
  let selectedMood = $state<MoodType>(null);
  let lastSearchTerm = $state<string>('');

  // Helper to get watch state for a video
  function getWatchState(platform: string, videoId: string): WatchStateItem | undefined {
    return watchStates.get(`${platform}:${videoId}`);
  }

  // Filtered results (excluding hidden channels and optionally watched videos)
  let filteredVideoResults = $derived(
    videoResults.filter(v => {
      // Filter hidden channels
      if (v.channel_id && hiddenChannelsStore.isHidden(v.platform, v.channel_id)) {
        return false;
      }
      // Filter watched videos if filter is set to unwatched
      if (watchFilter === 'unwatched') {
        const state = getWatchState(v.platform, v.video_id);
        // Hide fully watched videos, but keep partially watched
        if (state?.is_watched) {
          return false;
        }
      }
      return true;
    })
  );
  let filteredChannelResults = $derived(
    channelResults.filter(c => !hiddenChannelsStore.isHidden(c.platform, c.channel_id))
  );

  // Load platforms and hidden channels on mount
  $effect(() => {
    loadPlatforms();
    hiddenChannelsStore.load();
  });

  async function loadPlatforms() {
    try {
      const response = await api.listPlatforms();
      platforms = response.platforms;

      // Check for platform query parameter and pre-select it
      const urlPlatform = $page.url.searchParams.get('platform');
      if (urlPlatform && platforms.some(p => p.id === urlPlatform)) {
        selectedPlatforms = new Set([urlPlatform]);
        // Switch to channels tab for easier discovery
        searchType = 'channels';
      }
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to load platforms';
    }
  }

  async function loadWatchStates(videos: DiscoverVideoResult[]) {
    if (videos.length === 0) return;

    try {
      const response = await api.checkWatchStates(
        videos.map(v => ({ platform: v.platform, video_id: v.video_id }))
      );

      // Update watch states map
      const newStates = new Map(watchStates);
      for (const state of response.states) {
        newStates.set(`${state.platform}:${state.video_id}`, state);
      }
      watchStates = newStates;
    } catch (e) {
      console.error('Failed to load watch states:', e);
      // Non-critical error, don't show to user
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

  function getSearchQuery(): string {
    // Combine user query with mood-based search term
    const moodConfig = selectedMood ? MOOD_OPTIONS.find(m => m.id === selectedMood) : null;
    let query = searchQuery.trim();

    if (moodConfig) {
      // Pick a random search term from the mood's terms
      const randomTerm = moodConfig.searchTerms[Math.floor(Math.random() * moodConfig.searchTerms.length)];
      query = query ? `${query} ${randomTerm}` : randomTerm;
    }

    return query;
  }

  async function handleSearch(append: boolean = false) {
    const query = getSearchQuery();
    if (!query) {
      if (!selectedMood) {
        error = 'Enter a search query or select a mood to discover content';
        return;
      }
    }

    if (selectedPlatforms.size === 0) {
      error = 'Please select at least one platform';
      return;
    }

    if (append) {
      loadingMore = true;
    } else {
      searching = true;
      videoResults = [];
      channelResults = [];
      currentPage = 1;
      hasMore = true;
      lastSearchTerm = query;
    }
    error = null;

    try {
      const platformList = Array.from(selectedPlatforms);
      const maxPerPlatform = resultsPerPage;

      if (searchType === 'videos') {
        const response = await api.discoverVideos({
          query: append ? lastSearchTerm : query,
          platforms: platformList,
          max_per_platform: maxPerPlatform,
        });

        if (append) {
          // Filter out duplicates when appending
          const existingIds = new Set(videoResults.map(v => `${v.platform}:${v.video_id}`));
          const newResults = response.results.filter(v => !existingIds.has(`${v.platform}:${v.video_id}`));
          videoResults = [...videoResults, ...newResults];
          hasMore = newResults.length >= maxPerPlatform / 2;
          // Load watch states for new results
          loadWatchStates(newResults);
        } else {
          videoResults = response.results;
          hasMore = response.results.length >= maxPerPlatform;
          // Load watch states for all results
          loadWatchStates(response.results);
        }
        timings = response.timings;
        totalDuration = response.total_duration_ms;
      } else {
        const response = await api.discoverChannels({
          query: append ? lastSearchTerm : query,
          platforms: platformList,
          max_per_platform: maxPerPlatform,
        });

        if (append) {
          const existingIds = new Set(channelResults.map(c => `${c.platform}:${c.channel_id}`));
          const newResults = response.results.filter(c => !existingIds.has(`${c.platform}:${c.channel_id}`));
          channelResults = [...channelResults, ...newResults];
          hasMore = newResults.length >= maxPerPlatform / 2;
        } else {
          channelResults = response.results;
          hasMore = response.results.length >= maxPerPlatform;
        }
        timings = response.timings;
        totalDuration = response.total_duration_ms;
      }
      currentPage++;
    } catch (e) {
      error = e instanceof Error ? e.message : 'Search failed';
    } finally {
      searching = false;
      loadingMore = false;
    }
  }

  function handleKeydown(event: KeyboardEvent) {
    if (event.key === 'Enter') {
      handleSearch();
    }
  }

  function loadMore() {
    if (!loadingMore && hasMore) {
      handleSearch(true);
    }
  }

  function selectMood(mood: MoodType) {
    if (selectedMood === mood) {
      selectedMood = null;
    } else {
      selectedMood = mood;
      // Automatically search when mood is selected
      handleSearch();
    }
  }

  function clearResults() {
    videoResults = [];
    channelResults = [];
    selectedMood = null;
    searchQuery = '';
    error = null;
    hasMore = true;
    currentPage = 1;
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
    // Build queue from all video results for auto-advance
    const videoQueue = videoResults.map(v => discoverVideoToVideoItem(v));
    const videoIndex = videoResults.findIndex(v =>
      v.platform === video.platform && v.video_id === video.video_id
    );

    // Open with queue for auto-advance
    videoPlayer.openWithQueue(videoQueue, videoIndex >= 0 ? videoIndex : 0);
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

  async function searchChannelVideos(channel: DiscoverChannelResult) {
    // Switch to videos tab and search for the channel name
    searchType = 'videos';
    searchQuery = channel.name;
    // Only search on the channel's platform
    selectedPlatforms = new Set([channel.platform]);
    await handleSearch();
  }

  let collectionSaveSuccess = $state<string | null>(null);

  function handleCollectionSaved(event: { collectionName: string }) {
    collectionSaveSuccess = `Added to ${event.collectionName}!`;
    setTimeout(() => collectionSaveSuccess = null, 3000);
  }

</script>

<div class="discover-page">
  <header class="page-header">
    <h1>Discover</h1>
    <p class="subtitle">Find new content across multiple video platforms</p>
  </header>

  <!-- Mood/Category Quick Filters -->
  <div class="mood-section">
    <div class="mood-buttons">
      {#each MOOD_OPTIONS as mood}
        <button
          class="mood-btn"
          class:selected={selectedMood === mood.id}
          onclick={() => selectMood(mood.id)}
        >
          <span class="mood-icon">{mood.icon}</span>
          <span class="mood-label">{mood.label}</span>
        </button>
      {/each}
    </div>
  </div>

  <!-- Search Controls -->
  <div class="search-controls">
    <!-- Platform Toggles -->
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
      <button class="select-all-btn" onclick={selectAllPlatforms}>All</button>
    </div>

    <!-- Search Bar -->
    <div class="search-bar">
      <div class="search-filters-row">
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
        {#if searchType === 'videos'}
          <div class="watch-filter-tabs">
            <button
              class="filter-tab"
              class:active={watchFilter === 'all'}
              onclick={() => watchFilter = 'all'}
            >
              All
            </button>
            <button
              class="filter-tab"
              class:active={watchFilter === 'unwatched'}
              onclick={() => watchFilter = 'unwatched'}
            >
              Unwatched
            </button>
          </div>
        {/if}
      </div>
      <input
        type="text"
        placeholder={selectedMood ? `Search within ${MOOD_OPTIONS.find(m => m.id === selectedMood)?.label || 'mood'}...` : 'Search across platforms...'}
        bind:value={searchQuery}
        onkeydown={handleKeydown}
        class="search-input"
      />
      <button
        class="search-btn"
        onclick={() => handleSearch()}
        disabled={searching || (!searchQuery.trim() && !selectedMood)}
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

  {#if collectionSaveSuccess}
    <div class="success-message">{collectionSaveSuccess}</div>
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
      <div class="results-header">
        <span class="results-count">{videoResults.length} videos found</span>
        {#if selectedMood || searchQuery}
          <button class="clear-btn" onclick={clearResults}>Clear</button>
        {/if}
      </div>
      <div class="video-grid">
        {#each filteredVideoResults as video}
          <div class="video-card">
            <div class="thumbnail">
              {#if video.thumbnail_url}
                <img src={video.thumbnail_url} alt={video.title} loading="lazy" />
              {:else}
                <div class="no-thumbnail">No Thumbnail</div>
              {/if}
              <button class="play-overlay" onclick={() => playVideo(video)} aria-label="Play video">
                <svg viewBox="0 0 24 24" fill="currentColor" width="48" height="48">
                  <path d="M8 5v14l11-7z" />
                </svg>
              </button>
              {#if video.duration_seconds}
                <span class="duration">{formatDuration(video.duration_seconds)}</span>
              {/if}
              <span class="platform-badge" style="background-color: {getPlatformColor(video.platform)}">
                {getPlatformName(video.platform)}
              </span>
              <SaveButton
                mediaType="video"
                mediaUrl={video.video_url}
                thumbnailUrl={video.thumbnail_url}
                title={video.title}
                sourceUrl={video.video_url}
                domain={video.platform}
                embedType={video.platform}
                videoId={video.video_id}
                onsaved={handleCollectionSaved}
              />
              <div class="download-btn">
                <DownloadButton
                  platform={video.platform}
                  videoId={video.video_id}
                  title={video.title}
                  thumbnailUrl={video.thumbnail_url}
                  size="sm"
                />
              </div>
              {#if video.channel_id}
                <HideButton
                  platform={video.platform}
                  channelId={video.channel_id}
                  channelName={video.channel_name || 'Unknown Channel'}
                  channelAvatarUrl={video.channel_avatar_url}
                />
              {/if}
              {#if getWatchState(video.platform, video.video_id)?.is_partially_watched}
                {@const watchState = getWatchState(video.platform, video.video_id)}
                {#if watchState?.watch_progress_seconds && watchState?.duration_seconds}
                  <div class="watch-progress-bar">
                    <div
                      class="watch-progress-fill"
                      style="width: {Math.min(100, (watchState.watch_progress_seconds / watchState.duration_seconds) * 100)}%"
                    ></div>
                  </div>
                  <span class="partial-badge">In Progress</span>
                {/if}
              {/if}
            </div>
            <div class="video-info">
              <a href={video.video_url} target="_blank" rel="noopener noreferrer" class="video-title">
                {video.title}
              </a>
              {#if video.description}
                <p class="video-description">{video.description.slice(0, 120)}{video.description.length > 120 ? '...' : ''}</p>
              {/if}
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
      <!-- Load More -->
      {#if hasMore}
        <div class="load-more">
          <button
            class="load-more-btn"
            onclick={loadMore}
            disabled={loadingMore}
          >
            {#if loadingMore}
              <span class="loading-spinner small"></span>
              Loading more...
            {:else}
              Load More Videos
            {/if}
          </button>
        </div>
      {/if}
    {:else if searchType === 'channels' && channelResults.length > 0}
      <div class="results-count">{channelResults.length} channels found</div>
      <div class="channel-grid">
        {#each filteredChannelResults as channel}
          <div class="channel-card">
            <HideButton
              platform={channel.platform}
              channelId={channel.channel_id}
              channelName={channel.name}
              channelAvatarUrl={channel.avatar_url}
            />
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
                class="action-btn see-all"
                onclick={() => searchChannelVideos(channel)}
                title="Search for videos from this channel"
              >
                See Videos
              </button>
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
    {:else if !searching && (videoResults.length === 0 && channelResults.length === 0) && (searchQuery || selectedMood)}
      <div class="no-results">
        <p>No results found</p>
        <p class="hint">Try different keywords, select a different mood, or add more platforms</p>
      </div>
    {:else}
      <div class="empty-state">
        <div class="empty-icon">🌐</div>
        <h2>Discover New Content</h2>
        <p>Select a mood above to find videos, or enter a search query to explore across platforms.</p>
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

  /* Section Headers */
  .section-header {
    margin-bottom: var(--spacing-md);
  }

  .section-header h2 {
    font-size: 1.25rem;
    margin: 0 0 var(--spacing-xs) 0;
  }

  .section-subtitle {
    font-size: 0.9rem;
    color: var(--color-text-secondary);
  }

  .section-divider {
    height: 1px;
    background: var(--color-border);
    margin: var(--spacing-xl) 0;
  }

  /* Mood Section */
  .mood-section {
    margin-bottom: var(--spacing-lg);
  }

  .mood-buttons {
    display: flex;
    flex-wrap: wrap;
    gap: var(--spacing-sm);
    margin-bottom: var(--spacing-md);
  }

  .mood-btn {
    display: flex;
    align-items: center;
    gap: var(--spacing-xs);
    padding: var(--spacing-sm) var(--spacing-md);
    background: var(--color-bg-secondary);
    border: 2px solid var(--color-border);
    border-radius: var(--radius-full);
    cursor: pointer;
    transition: all 0.2s ease;
    white-space: nowrap;
  }

  .mood-btn:hover {
    border-color: var(--color-primary);
    background: var(--color-bg);
  }

  .mood-btn.selected {
    background: var(--color-primary);
    border-color: var(--color-primary);
    color: white;
  }

  .mood-icon {
    font-size: 1.25rem;
  }

  .mood-label {
    font-weight: 500;
    font-size: 0.9rem;
  }

  .mood-desc {
    font-size: 0.75rem;
    opacity: 0.7;
  }

  .mood-loading {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: var(--spacing-md);
    padding: var(--spacing-xl);
    color: var(--color-text-secondary);
  }

  .mood-error {
    padding: var(--spacing-md);
    background: rgba(239, 68, 68, 0.1);
    color: var(--color-error);
    border-radius: var(--radius-md);
    font-size: 0.9rem;
  }

  .mood-search-bar {
    display: flex;
    gap: var(--spacing-sm);
    margin-bottom: var(--spacing-md);
  }

  .mood-search-input {
    flex: 1;
    padding: var(--spacing-sm) var(--spacing-md);
    font-size: 0.9rem;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    background: var(--color-bg);
    color: var(--color-text);
  }

  .mood-search-input:focus {
    outline: none;
    border-color: var(--color-primary);
  }

  .mood-search-btn {
    padding: var(--spacing-sm) var(--spacing-md);
    background: var(--color-primary);
    color: white;
    border: none;
    border-radius: var(--radius-md);
    font-size: 0.85rem;
    font-weight: 500;
    cursor: pointer;
    white-space: nowrap;
  }

  .mood-search-btn:hover:not(:disabled) {
    opacity: 0.9;
  }

  .mood-search-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .mood-subscribe-btn {
    margin-top: var(--spacing-xs);
    padding: 2px 8px;
    font-size: 0.7rem;
    background: var(--color-primary);
    color: white;
    border: none;
    border-radius: var(--radius-sm);
    cursor: pointer;
  }

  .mood-subscribe-btn:hover:not(:disabled) {
    opacity: 0.9;
  }

  .mood-subscribe-btn:disabled {
    opacity: 0.5;
  }

  .mood-results-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: var(--spacing-md);
  }

  .mood-count {
    color: var(--color-text-secondary);
    font-size: 0.9rem;
  }

  .clear-mood-btn {
    padding: var(--spacing-xs) var(--spacing-md);
    background: var(--color-bg-secondary);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    color: var(--color-text-secondary);
    font-size: 0.8rem;
    cursor: pointer;
  }

  .clear-mood-btn:hover {
    background: var(--color-bg);
    border-color: var(--color-text-secondary);
  }

  .mood-video-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: var(--spacing-md);
  }

  .mood-video-card {
    background: var(--color-bg-secondary);
    border-radius: var(--radius-md);
    overflow: hidden;
  }

  .mood-thumbnail {
    position: relative;
    aspect-ratio: 16 / 9;
    width: 100%;
    background: var(--color-bg);
    border: none;
    padding: 0;
    cursor: pointer;
    display: block;
  }

  .mood-thumbnail img {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }

  .mood-thumbnail .play-overlay {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(0, 0, 0, 0.4);
    color: white;
    opacity: 0;
    transition: opacity 0.2s;
  }

  .mood-thumbnail:hover .play-overlay {
    opacity: 1;
  }

  .mood-video-info {
    padding: var(--spacing-sm);
  }

  .mood-video-title {
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
    font-size: 0.85rem;
    font-weight: 500;
    line-height: 1.3;
    margin-bottom: var(--spacing-xs);
  }

  .mood-video-channel {
    display: block;
    font-size: 0.75rem;
    color: var(--color-text-secondary);
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

  .search-filters-row {
    display: flex;
    flex-wrap: wrap;
    gap: var(--spacing-md);
    margin-bottom: var(--spacing-sm);
  }

  .search-type-tabs {
    display: flex;
    gap: var(--spacing-xs);
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

  .watch-filter-tabs {
    display: flex;
    gap: var(--spacing-xs);
  }

  .filter-tab {
    padding: var(--spacing-xs) var(--spacing-sm);
    background: var(--color-bg-secondary);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    cursor: pointer;
    color: var(--color-text-secondary);
    font-size: 0.85rem;
    font-weight: 500;
    transition: all 0.2s ease;
  }

  .filter-tab:hover {
    border-color: var(--color-primary);
  }

  .filter-tab.active {
    background: var(--color-primary);
    border-color: var(--color-primary);
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

  .thumbnail {
    position: relative;
    aspect-ratio: 16 / 9;
    background: var(--color-bg);
    overflow: hidden;
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
    border: none;
    cursor: pointer;
    z-index: 1;
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

  .download-btn {
    position: absolute;
    top: var(--spacing-xs);
    right: 44px;
    z-index: 10;
    opacity: 0;
    transition: opacity 0.2s;
  }

  .thumbnail:hover .download-btn,
  .video-card:hover .download-btn {
    opacity: 1;
  }

  @media (max-width: 768px) {
    .download-btn {
      opacity: 1;
    }
  }

  .watch-progress-bar {
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    height: 4px;
    background: rgba(0, 0, 0, 0.5);
  }

  .watch-progress-fill {
    height: 100%;
    background: var(--color-primary);
    transition: width 0.3s ease;
  }

  .partial-badge {
    position: absolute;
    bottom: var(--spacing-xs);
    left: var(--spacing-xs);
    background: rgba(var(--color-primary-rgb, 99, 102, 241), 0.9);
    color: white;
    padding: 2px 6px;
    border-radius: var(--radius-sm);
    font-size: 0.65rem;
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

  .video-description {
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
    font-size: 0.8rem;
    color: var(--color-text-secondary);
    line-height: 1.4;
    margin: var(--spacing-xs) 0;
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

  .action-btn.see-all {
    background: var(--color-bg);
    color: var(--color-text);
    border: 1px solid var(--color-border);
  }

  .action-btn.see-all:hover {
    background: var(--color-bg-secondary);
    border-color: var(--color-primary);
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
    position: relative;
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
    flex-direction: column;
    align-items: flex-start;
    gap: var(--spacing-xs);
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

  /* Search Controls */
  .search-controls {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-md);
    margin-bottom: var(--spacing-lg);
    padding: var(--spacing-md);
    background: var(--color-bg-secondary);
    border-radius: var(--radius-lg);
    border: 1px solid var(--color-border);
  }

  /* Results Header */
  .results-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: var(--spacing-md);
  }

  .results-count {
    color: var(--color-text-secondary);
    font-size: 0.9rem;
  }

  .clear-btn {
    padding: var(--spacing-xs) var(--spacing-md);
    background: var(--color-bg-secondary);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    color: var(--color-text-secondary);
    font-size: 0.85rem;
    cursor: pointer;
    transition: all 0.2s ease;
  }

  .clear-btn:hover {
    background: var(--color-bg);
    border-color: var(--color-text-secondary);
    color: var(--color-text);
  }

  /* Load More */
  .load-more {
    display: flex;
    justify-content: center;
    padding: var(--spacing-xl) 0;
  }

  .load-more-btn {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    padding: var(--spacing-md) var(--spacing-xl);
    background: var(--color-primary);
    color: white;
    border: none;
    border-radius: var(--radius-md);
    font-size: 1rem;
    font-weight: 600;
    cursor: pointer;
    transition: all 0.2s ease;
  }

  .load-more-btn:hover:not(:disabled) {
    opacity: 0.9;
    transform: translateY(-1px);
  }

  .load-more-btn:disabled {
    opacity: 0.7;
    cursor: wait;
  }

  .loading-spinner.small {
    width: 20px;
    height: 20px;
    border-width: 2px;
  }

  /* Mobile */
  @media (max-width: 768px) {
    .mood-buttons {
      overflow-x: auto;
      flex-wrap: nowrap;
      padding-bottom: var(--spacing-sm);
      -webkit-overflow-scrolling: touch;
    }

    .mood-btn {
      flex-shrink: 0;
    }

    .search-controls {
      padding: var(--spacing-sm);
    }

    .platform-toggles {
      overflow-x: auto;
      flex-wrap: nowrap;
      padding-bottom: var(--spacing-sm);
      -webkit-overflow-scrolling: touch;
    }

    .platform-btn {
      flex-shrink: 0;
    }

    .search-bar {
      flex-direction: column;
    }

    .search-type-tabs {
      width: 100%;
    }

    .type-tab {
      flex: 1;
      justify-content: center;
    }

    .search-btn {
      width: 100%;
    }

    .video-grid {
      grid-template-columns: 1fr;
    }

    .results-header {
      flex-direction: column;
      gap: var(--spacing-sm);
      align-items: flex-start;
    }

    .load-more-btn {
      width: 100%;
      justify-content: center;
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
