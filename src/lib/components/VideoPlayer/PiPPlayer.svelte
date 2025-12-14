<script lang="ts">
  import { videoPlayer, formatDuration, getCachedStreamInfo, prefetchStreams, type StreamInfo } from '$lib/stores/videoPlayer.svelte';
  import { getPlatformName, getPlatformColor } from '$lib/utils/embedUrl';
  import { loadYouTubeAPI, createYouTubePlayer, type YouTubePlayer } from '$lib/utils/youtubeApi';
  import { api } from '$lib/api/client';
  import EmbedFallback from './EmbedFallback.svelte';

  // Progress tracking
  let progressInterval: ReturnType<typeof setInterval> | null = null;
  let lastSavedProgress = 0;
  const PROGRESS_SAVE_INTERVAL = 15000; // Save every 15 seconds
  const WATCHED_THRESHOLD = 0.90; // Mark as watched at 90% completion

  // Dragging state
  let isDragging = $state(false);
  let position = $state({ x: 0, y: 0 });
  let dragOffset = $state({ x: 0, y: 0 });
  let playerRef: HTMLDivElement | undefined = $state();
  let iframeLoaded = $state(false);
  let iframeError = $state(false);

  // Direct stream state
  let streamInfo = $state<StreamInfo | null>(null);
  let loadingStream = $state(false);
  let useDirectStream = $state(false);
  let videoElement: HTMLVideoElement | null = $state(null);
  let audioElement: HTMLAudioElement | null = $state(null);

  // YouTube API player
  let ytPlayer: YouTubePlayer | null = null;
  let ytPlayerReady = $state(false);
  let ytApiLoading = $state(false);
  let useYouTubeApi = $state(true);

  // Size: small (320x180) or medium (480x270)
  let size = $state<'small' | 'medium'>('small');

  // Computed values
  const video = $derived(videoPlayer.currentVideo);
  const isOpen = $derived(videoPlayer.isPiP && video !== null);
  const embedUrl = $derived(video?.embedConfig.embedUrl);
  const canEmbed = $derived(video?.embedConfig.supportsEmbed && !iframeError);
  const platformName = $derived(video ? getPlatformName(video.platform) : '');
  const platformColor = $derived(video ? getPlatformColor(video.platform) : '#666');
  const hasDirectStream = $derived(streamInfo?.stream_url && useDirectStream);
  const isYouTube = $derived(video?.platform === 'youtube');
  const isAudio = $derived(video?.platform === 'redbar');
  const shouldUseYtApi = $derived(isYouTube && useYouTubeApi && canEmbed && !hasDirectStream);
  const videoKey = $derived(videoPlayer.videoKey);
  const savedPlayhead = $derived(videoPlayer.savedPlayhead);

  const dimensions = $derived(size === 'small' ? { width: 320, height: 180 } : { width: 480, height: 270 });

  function handleClose() {
    // Save final progress before closing
    const currentTime = getCurrentPlaybackTime();
    if (currentTime > 0) {
      saveProgress(currentTime);
    }
    stopProgressTracking();

    // Clean up YouTube player
    if (ytPlayer) {
      try {
        ytPlayer.destroy();
      } catch {}
      ytPlayer = null;
    }
    ytPlayerReady = false;

    videoPlayer.close();
    iframeLoaded = false;
    iframeError = false;
    streamInfo = null;
    useDirectStream = false;
    position = { x: 0, y: 0 };
    lastSavedProgress = 0;
  }

  async function fetchStreamInfo() {
    if (!video || video.platform !== 'youtube') return;

    // Check cache first (from pre-fetch)
    const cached = getCachedStreamInfo(video.platform, video.videoId);
    if (cached) {
      streamInfo = cached;
      console.log('[PiP] Using cached stream:', cached.stream_url ? 'Available' : 'N/A', cached.quality || '');
      if (cached.stream_url) {
        useDirectStream = true;
      }
      return;
    }

    loadingStream = true;
    try {
      const response = await fetch(`/api/stream/${video.platform}/${video.videoId}`);
      if (response.ok) {
        streamInfo = await response.json();
        console.log('[PiP] Stream info:', streamInfo?.stream_url ? 'Available' : 'N/A', streamInfo?.quality || '');
        // Auto-enable direct stream if available (better for background playback)
        if (streamInfo?.stream_url) {
          useDirectStream = true;
        }
      } else {
        console.warn('[PiP] Stream API error:', response.status);
      }
    } catch (e) {
      console.warn('[PiP] Stream fetch failed:', e);
    } finally {
      loadingStream = false;
    }
  }

  function toggleDirectStream() {
    if (streamInfo?.stream_url) {
      useDirectStream = !useDirectStream;
    }
  }

  /**
   * Get the current playback time from whichever player is active
   */
  function getCurrentPlaybackTime(): number {
    if (ytPlayer && ytPlayerReady) {
      try {
        return ytPlayer.getCurrentTime();
      } catch {}
    }
    if (videoElement) {
      return videoElement.currentTime;
    }
    if (audioElement) {
      return audioElement.currentTime;
    }
    return 0;
  }

  /**
   * Get the total duration from whichever player is active
   */
  function getTotalDuration(): number {
    if (ytPlayer && ytPlayerReady) {
      try {
        return ytPlayer.getDuration();
      } catch {}
    }
    if (videoElement) {
      return videoElement.duration || video?.duration || 0;
    }
    if (audioElement) {
      return audioElement.duration || video?.duration || 0;
    }
    return video?.duration || 0;
  }

  /**
   * Save progress to the API
   */
  async function saveProgress(currentTime: number) {
    if (!video || !video.sourceId || video.sourceType === 'discover') return;
    if (Math.abs(currentTime - lastSavedProgress) < 5) return;

    try {
      if (video.sourceType === 'feed') {
        await api.updateFeedItemProgress(video.sourceId, Math.floor(currentTime));
      } else if (video.sourceType === 'saved') {
        await api.updateSavedVideoProgress(video.sourceId, Math.floor(currentTime));
      }
      lastSavedProgress = currentTime;
      console.log('[PiP] Progress saved:', Math.floor(currentTime), 'seconds');
    } catch (e) {
      console.warn('[PiP] Failed to save progress:', e);
    }
  }

  /**
   * Mark the video as watched
   */
  async function markAsWatched(finalProgress: number) {
    if (!video || !video.sourceId || video.sourceType === 'discover') return;

    try {
      if (video.sourceType === 'feed') {
        await api.markFeedItemWatched(video.sourceId, Math.floor(finalProgress));
      } else if (video.sourceType === 'saved') {
        await api.markSavedVideoWatched(video.sourceId, Math.floor(finalProgress));
      }
      console.log('[PiP] Marked as watched');
    } catch (e) {
      console.warn('[PiP] Failed to mark as watched:', e);
    }
  }

  /**
   * Check if video should be marked as watched (>90% complete)
   */
  function checkWatchedThreshold() {
    const currentTime = getCurrentPlaybackTime();
    const duration = getTotalDuration();
    if (duration > 0 && currentTime / duration >= WATCHED_THRESHOLD) {
      markAsWatched(currentTime);
      stopProgressTracking();
    }
  }

  /**
   * Start periodic progress tracking
   */
  function startProgressTracking() {
    stopProgressTracking();
    progressInterval = setInterval(() => {
      const currentTime = getCurrentPlaybackTime();
      saveProgress(currentTime);
      checkWatchedThreshold();
    }, PROGRESS_SAVE_INTERVAL);
    console.log('[PiP] Progress tracking started');
  }

  /**
   * Stop progress tracking
   */
  function stopProgressTracking() {
    if (progressInterval) {
      clearInterval(progressInterval);
      progressInterval = null;
    }
  }

  /**
   * Get the initial playhead position
   */
  function getInitialPlayhead(): number {
    if (savedPlayhead > 0) {
      return savedPlayhead;
    }
    if (video?.watchProgress && video.watchProgress > 0) {
      return video.watchProgress;
    }
    return 0;
  }

  function handleExpand() {
    // Save current playhead position before switching
    const currentTime = getCurrentPlaybackTime();
    if (currentTime > 0) {
      saveProgress(currentTime);
    }
    stopProgressTracking();
    videoPlayer.savePlayhead(currentTime);
    videoPlayer.switchToModal();
  }

  function handleVideoEnded() {
    // Mark video as watched when it ends naturally
    const duration = getTotalDuration();
    markAsWatched(duration);
    stopProgressTracking();

    // Try to play next video in queue, otherwise close
    if (!videoPlayer.playNext()) {
      handleClose();
    }
  }

  async function initYouTubePlayer() {
    if (!video || video.platform !== 'youtube') return;

    ytApiLoading = true;
    ytPlayerReady = false;

    try {
      await loadYouTubeAPI();

      // Clean up existing player
      if (ytPlayer) {
        try {
          ytPlayer.destroy();
        } catch {}
        ytPlayer = null;
      }

      // Wait for DOM element to exist
      await new Promise(resolve => setTimeout(resolve, 150));

      const container = document.getElementById('pip-yt-player-container');
      if (!container) {
        console.warn('[PiP] YouTube player container not found');
        useYouTubeApi = false;
        return;
      }

      const startTime = getInitialPlayhead();

      ytPlayer = createYouTubePlayer('pip-yt-player-container', video.videoId, {
        onReady: () => {
          ytPlayerReady = true;
          console.log('[PiP] YouTube player ready');
          // Seek to saved position if any
          if (startTime > 0 && ytPlayer) {
            try {
              ytPlayer.seekTo(startTime, true);
              videoPlayer.clearSavedPlayhead();
              console.log('[PiP] Seeking to saved position:', startTime);
            } catch {}
          }
          // Start progress tracking
          startProgressTracking();
        },
        onEnded: () => {
          console.log('[PiP] YouTube video ended');
          handleVideoEnded();
        },
        onError: (error) => {
          console.warn('[PiP] YouTube player error:', error);
          useYouTubeApi = false;
        },
      });
    } catch (error) {
      console.warn('[PiP] Failed to init YouTube API:', error);
      useYouTubeApi = false;
    } finally {
      ytApiLoading = false;
    }
  }

  function toggleSize() {
    size = size === 'small' ? 'medium' : 'small';
  }

  function handleMouseDown(event: MouseEvent) {
    if (event.target instanceof HTMLButtonElement || event.target instanceof HTMLAnchorElement) {
      return;
    }
    isDragging = true;
    if (playerRef) {
      const rect = playerRef.getBoundingClientRect();
      dragOffset = {
        x: event.clientX - rect.left,
        y: event.clientY - rect.top,
      };
    }
  }

  function handleMouseMove(event: MouseEvent) {
    if (!isDragging) return;

    const newX = event.clientX - dragOffset.x;
    const newY = event.clientY - dragOffset.y;

    // Keep within viewport
    const maxX = window.innerWidth - dimensions.width;
    const maxY = window.innerHeight - dimensions.height;

    position = {
      x: Math.max(0, Math.min(newX, maxX)),
      y: Math.max(0, Math.min(newY, maxY)),
    };
  }

  function handleMouseUp() {
    isDragging = false;
  }

  function handleKeydown(event: KeyboardEvent) {
    if (!isOpen) return;

    if (event.key === 'Escape') {
      handleClose();
    } else if (event.key === 'm' || event.key === 'M') {
      handleExpand();
    }
  }

  function handleIframeLoad() {
    iframeLoaded = true;
  }

  function handleIframeError() {
    iframeError = true;
  }

  // Reset state when video changes
  $effect(() => {
    if (video) {
      iframeLoaded = false;
      iframeError = false;
      streamInfo = null;
      useDirectStream = false;
      ytPlayerReady = false;
      lastSavedProgress = 0;
      stopProgressTracking();
      // Fetch stream info for direct playback
      fetchStreamInfo();
    }
  });

  // Initialize YouTube API player for YouTube videos
  $effect(() => {
    // Use videoKey to force re-init when video changes
    const key = videoKey;
    if (isOpen && shouldUseYtApi && video) {
      initYouTubePlayer();
    }
  });

  // Restore playhead for direct video element and start progress tracking
  $effect(() => {
    if (videoElement && hasDirectStream) {
      const startTime = getInitialPlayhead();
      if (startTime > 0) {
        videoElement.currentTime = startTime;
        videoPlayer.clearSavedPlayhead();
        console.log('[PiP] Direct video seeking to:', startTime);
      }
      // Start progress tracking for direct video
      startProgressTracking();
    }
  });

  // Restore playhead for audio element and start progress tracking
  $effect(() => {
    if (audioElement && isAudio) {
      const startTime = getInitialPlayhead();
      if (startTime > 0) {
        audioElement.currentTime = startTime;
        videoPlayer.clearSavedPlayhead();
        console.log('[PiP] Audio seeking to:', startTime);
      }
      // Start progress tracking for audio
      startProgressTracking();
    }
  });

  // Cleanup YouTube player and progress tracking when closing or switching modes
  $effect(() => {
    return () => {
      stopProgressTracking();
      if (ytPlayer) {
        try {
          ytPlayer.destroy();
        } catch {}
        ytPlayer = null;
      }
    };
  });

  // Calculate initial position (bottom-right corner with padding)
  $effect(() => {
    if (isOpen && position.x === 0 && position.y === 0) {
      position = {
        x: window.innerWidth - dimensions.width - 20,
        y: window.innerHeight - dimensions.height - 20,
      };
    }
  });
</script>

<svelte:window
  onkeydown={handleKeydown}
  onmousemove={handleMouseMove}
  onmouseup={handleMouseUp}
/>

{#if isOpen && video}
  <div
    class="pip-player"
    class:dragging={isDragging}
    bind:this={playerRef}
    style="left: {position.x}px; top: {position.y}px; width: {dimensions.width}px; height: {dimensions.height}px;"
    onmousedown={handleMouseDown}
    role="dialog"
    aria-label="Picture in Picture Video Player"
  >
    <!-- Video Content -->
    <div class="pip-content">
      {#if isAudio}
        <!-- Audio player for podcasts (Red Bar Radio) -->
        <div class="audio-pip-player">
          {#if video.thumbnailUrl}
            <img src={video.thumbnailUrl} alt={video.title} class="audio-thumbnail" />
          {:else}
            <div class="audio-placeholder">
              <svg viewBox="0 0 24 24" fill="currentColor" width="48" height="48">
                <path d="M12 3v10.55c-.59-.34-1.27-.55-2-.55-2.21 0-4 1.79-4 4s1.79 4 4 4 4-1.79 4-4V7h4V3h-6z"/>
              </svg>
            </div>
          {/if}
          <audio
            bind:this={audioElement}
            src={video.videoUrl}
            controls
            autoplay
            onended={handleVideoEnded}
            onplay={startProgressTracking}
            class="pip-audio"
          >
            Your browser does not support audio playback.
          </audio>
        </div>
      {:else if hasDirectStream && streamInfo?.stream_url}
        <!-- Direct stream playback (premium, no ads) -->
        <div class="direct-player">
          <video
            bind:this={videoElement}
            src={streamInfo.stream_url}
            controls
            autoplay
            class="direct-video"
            onended={handleVideoEnded}
          >
            Your browser does not support video playback.
          </video>
        </div>
      {:else if shouldUseYtApi}
        <!-- YouTube API player for auto-advance detection -->
        <div class="yt-player-wrapper">
          {#if !ytPlayerReady || ytApiLoading}
            <div class="loading-spinner">
              <div class="spinner"></div>
            </div>
          {/if}
          <div id="pip-yt-player-container" class="yt-player-container" class:loaded={ytPlayerReady}></div>
        </div>
      {:else if canEmbed && embedUrl}
        <div class="iframe-container">
          {#if !iframeLoaded}
            <div class="loading-spinner">
              <div class="spinner"></div>
            </div>
          {/if}
          <iframe
            src={embedUrl}
            title={video.title}
            allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
            allowfullscreen
            onload={handleIframeLoad}
            onerror={handleIframeError}
            class:loaded={iframeLoaded}
          ></iframe>
        </div>
      {:else}
        <div class="pip-fallback">
          {#if video.thumbnailUrl}
            <img src={video.thumbnailUrl} alt={video.title} class="fallback-thumbnail" />
          {/if}
          <a
            href={video.videoUrl}
            target="_blank"
            rel="noopener noreferrer"
            class="watch-external"
            style="background-color: {platformColor}"
          >
            Watch on {platformName}
          </a>
        </div>
      {/if}
    </div>

    <!-- Controls Overlay -->
    <div class="pip-controls">
      <div class="controls-top">
        <div class="controls-left">
          <span class="platform-badge" style="background-color: {platformColor}">
            {platformName}
          </span>
          {#if streamInfo?.is_premium}
            <span class="premium-badge" title="Premium playback">P</span>
          {/if}
        </div>
        <div class="controls-right">
          {#if streamInfo?.stream_url}
            <button
              class="control-btn"
              class:active={useDirectStream}
              onclick={toggleDirectStream}
              title={useDirectStream ? 'Switch to embed' : 'Switch to direct (no ads)'}
            >
              <svg viewBox="0 0 24 24" fill="currentColor" width="16" height="16">
                <path d="M21 3H3c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h18c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm0 16H3V5h18v14zM9 8l7 4-7 4V8z"/>
              </svg>
            </button>
          {/if}
          <button
            class="control-btn"
            onclick={toggleSize}
            title={size === 'small' ? 'Enlarge' : 'Shrink'}
          >
            <svg viewBox="0 0 24 24" fill="currentColor" width="16" height="16">
              {#if size === 'small'}
                <path d="M7 14H5v5h5v-2H7v-3zm-2-4h2V7h3V5H5v5zm12 7h-3v2h5v-5h-2v3zM14 5v2h3v3h2V5h-5z"/>
              {:else}
                <path d="M5 16h3v3h2v-5H5v2zm3-8H5v2h5V5H8v3zm6 11h2v-3h3v-2h-5v5zm2-11V5h-2v5h5V8h-3z"/>
              {/if}
            </svg>
          </button>
          <button
            class="control-btn"
            onclick={handleExpand}
            title="Expand (M)"
          >
            <svg viewBox="0 0 24 24" fill="currentColor" width="16" height="16">
              <path d="M19 7h-8v6h8V7zm2-4H3c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h18c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm0 16H3V5h18v14z"/>
            </svg>
          </button>
          <button
            class="control-btn close-btn"
            onclick={handleClose}
            title="Close (Escape)"
          >
            <svg viewBox="0 0 24 24" fill="currentColor" width="16" height="16">
              <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
            </svg>
          </button>
        </div>
      </div>
      <div class="controls-bottom">
        <span class="video-title" title={video.title}>{video.title}</span>
      </div>
    </div>
  </div>
{/if}

<style>
  .pip-player {
    position: fixed;
    z-index: 999;
    background: black;
    border-radius: var(--radius-lg);
    overflow: hidden;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
    cursor: move;
    user-select: none;
    transition: box-shadow 0.2s ease;
  }

  .pip-player:hover {
    box-shadow: 0 12px 48px rgba(0, 0, 0, 0.5);
  }

  .pip-player.dragging {
    cursor: grabbing;
    box-shadow: 0 16px 64px rgba(0, 0, 0, 0.6);
  }

  .pip-content {
    width: 100%;
    height: 100%;
    position: relative;
  }

  .iframe-container {
    width: 100%;
    height: 100%;
    position: relative;
  }

  .iframe-container iframe {
    width: 100%;
    height: 100%;
    border: none;
    opacity: 0;
    transition: opacity 0.3s ease;
  }

  .iframe-container iframe.loaded {
    opacity: 1;
  }

  .yt-player-wrapper {
    position: relative;
    width: 100%;
    height: 100%;
  }

  .yt-player-container {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    opacity: 0;
    transition: opacity 0.3s ease;
  }

  .yt-player-container.loaded {
    opacity: 1;
  }

  .loading-spinner {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    background: black;
  }

  .spinner {
    width: 32px;
    height: 32px;
    border: 2px solid var(--color-border);
    border-top-color: var(--color-primary);
    border-radius: 50%;
    animation: spin 1s linear infinite;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  .direct-player {
    width: 100%;
    height: 100%;
    position: relative;
  }

  .direct-video {
    width: 100%;
    height: 100%;
    background: black;
  }

  /* Audio PiP Player Styles */
  .audio-pip-player {
    width: 100%;
    height: 100%;
    display: flex;
    flex-direction: column;
    background: linear-gradient(135deg, #1a1a2e 0%, #0f3460 100%);
    position: relative;
  }

  .audio-thumbnail {
    width: 100%;
    height: calc(100% - 40px);
    object-fit: cover;
    filter: brightness(0.8);
  }

  .audio-placeholder {
    width: 100%;
    height: calc(100% - 40px);
    display: flex;
    align-items: center;
    justify-content: center;
    background: linear-gradient(135deg, #2d2d44 0%, #1a1a2e 100%);
    color: var(--color-text-muted);
  }

  .pip-audio {
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    height: 40px;
    width: 100%;
    background: rgba(0, 0, 0, 0.8);
  }

  .pip-fallback {
    width: 100%;
    height: 100%;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    position: relative;
  }

  .fallback-thumbnail {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    object-fit: cover;
    filter: brightness(0.4);
  }

  .watch-external {
    position: relative;
    z-index: 1;
    padding: var(--spacing-sm) var(--spacing-md);
    color: white;
    text-decoration: none;
    border-radius: var(--radius-md);
    font-size: 0.85rem;
    font-weight: 500;
    transition: opacity 0.2s ease;
  }

  .watch-external:hover {
    opacity: 0.9;
  }

  /* Controls Overlay */
  .pip-controls {
    position: absolute;
    inset: 0;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    padding: var(--spacing-sm);
    pointer-events: none;
    opacity: 0;
    transition: opacity 0.2s ease;
    background: linear-gradient(
      to bottom,
      rgba(0, 0, 0, 0.6) 0%,
      transparent 25%,
      transparent 100%
    );
  }

  .pip-player:hover .pip-controls {
    opacity: 1;
  }

  .controls-top {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
  }

  .controls-left {
    display: flex;
    align-items: center;
    gap: 4px;
  }

  .platform-badge {
    padding: 2px 6px;
    border-radius: var(--radius-sm);
    color: white;
    font-size: 0.65rem;
    font-weight: 600;
    text-transform: uppercase;
    pointer-events: auto;
  }

  .premium-badge {
    padding: 2px 4px;
    border-radius: var(--radius-sm);
    background: linear-gradient(135deg, #ffd700, #ffb700);
    color: #000;
    font-size: 0.6rem;
    font-weight: 700;
  }

  .controls-right {
    display: flex;
    gap: var(--spacing-xs);
  }

  .control-btn {
    background: rgba(0, 0, 0, 0.5);
    border: none;
    color: white;
    width: 28px;
    height: 28px;
    border-radius: var(--radius-sm);
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: background 0.2s ease;
    pointer-events: auto;
  }

  .control-btn:hover {
    background: rgba(0, 0, 0, 0.8);
  }

  .control-btn.active {
    background: var(--color-primary);
  }

  .close-btn:hover {
    background: var(--color-error);
  }

  .controls-bottom {
    pointer-events: none;
    /* Leave room for video controls at the very bottom */
    margin-bottom: 32px;
  }

  .video-title {
    display: block;
    color: white;
    font-size: 0.75rem;
    font-weight: 500;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    text-shadow: 0 1px 2px rgba(0, 0, 0, 0.5);
  }
</style>
