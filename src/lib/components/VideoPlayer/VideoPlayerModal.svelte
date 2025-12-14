<script lang="ts">
  import { videoPlayer, formatDuration } from '$lib/stores/videoPlayer.svelte';
  import { playbackPreferences } from '$lib/stores/playbackPreferences.svelte';
  import { getPlatformName, getPlatformColor } from '$lib/utils/embedUrl';
  import { loadYouTubeAPI, createYouTubePlayer, isYouTubeAPIReady, type YouTubePlayer } from '$lib/utils/youtubeApi';
  import EmbedFallback from './EmbedFallback.svelte';

  interface Props {
    onMarkWatched?: () => void;
  }

  interface StreamInfo {
    video_id: string;
    platform: string;
    title?: string;
    stream_url?: string;
    audio_url?: string;
    is_authenticated: boolean;
    is_premium: boolean;
    quality?: string;
    error?: string;
  }

  let { onMarkWatched }: Props = $props();

  let iframeLoaded = $state(false);
  let iframeError = $state(false);
  let streamInfo = $state<StreamInfo | null>(null);
  let loadingStream = $state(false);
  let useDirectStream = $state(false);
  let videoElement: HTMLVideoElement | null = null;

  // YouTube API player
  let ytPlayer: YouTubePlayer | null = null;
  let ytPlayerReady = $state(false);
  let ytApiLoading = $state(false);
  let useYouTubeApi = $state(true); // Default to using YT API for better end detection

  // Computed values
  const video = $derived(videoPlayer.currentVideo);
  const isOpen = $derived(videoPlayer.isModal && video !== null);
  const embedUrl = $derived(video?.embedConfig.embedUrl);
  const canEmbed = $derived(video?.embedConfig.supportsEmbed && !iframeError);
  const platformName = $derived(video ? getPlatformName(video.platform) : '');
  const platformColor = $derived(video ? getPlatformColor(video.platform) : '#666');
  const hasDirectStream = $derived(streamInfo?.stream_url && useDirectStream);
  const isPremium = $derived(streamInfo?.is_premium ?? false);
  const isYouTube = $derived(video?.platform === 'youtube');
  const shouldUseYtApi = $derived(isYouTube && useYouTubeApi && canEmbed && !hasDirectStream);
  const videoKey = $derived(videoPlayer.videoKey);
  const savedPlayhead = $derived(videoPlayer.savedPlayhead);
  const theaterMode = $derived(playbackPreferences.theaterMode);
  const backgroundPlayback = $derived(playbackPreferences.backgroundPlayback);

  function handleClose() {
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
  }

  async function fetchStreamInfo() {
    if (!video || video.platform !== 'youtube') return;

    loadingStream = true;
    try {
      const response = await fetch(`/api/stream/${video.platform}/${video.videoId}`);
      if (response.ok) {
        streamInfo = await response.json();
      }
    } catch {
      // Stream API not available, continue with embed
    } finally {
      loadingStream = false;
    }
  }

  function toggleDirectStream() {
    if (streamInfo?.stream_url) {
      useDirectStream = !useDirectStream;
    }
  }

  function handleSwitchToPiP() {
    // Save current playhead position before switching
    let currentTime = 0;
    if (ytPlayer && ytPlayerReady) {
      try {
        currentTime = ytPlayer.getCurrentTime();
      } catch {}
    } else if (videoElement) {
      currentTime = videoElement.currentTime;
    }
    videoPlayer.savePlayhead(currentTime);
    videoPlayer.switchToPiP();
  }

  function toggleTheaterMode() {
    playbackPreferences.toggleTheaterMode();
  }

  /**
   * Request native browser PiP for background audio playback
   * This allows audio to continue when screen is off on mobile
   */
  async function requestNativePiP() {
    if (!videoElement) return false;

    try {
      if (document.pictureInPictureEnabled && !document.pictureInPictureElement) {
        await videoElement.requestPictureInPicture();
        return true;
      }
    } catch (e) {
      console.warn('[Modal] Native PiP request failed:', e);
    }
    return false;
  }

  function handleBackdropClick(event: MouseEvent) {
    if (event.target === event.currentTarget) {
      handleClose();
    }
  }

  // Queue-related derived values
  const hasNext = $derived(videoPlayer.hasNext);
  const hasPrevious = $derived(videoPlayer.hasPrevious);
  const queuePosition = $derived(
    videoPlayer.queueLength > 0
      ? `${videoPlayer.currentIndex + 1}/${videoPlayer.queueLength}`
      : null
  );

  function handlePrevious() {
    videoPlayer.playPrevious();
  }

  function handleNext() {
    videoPlayer.playNext();
  }

  function handleVideoEnded() {
    // Auto-advance to next video in queue
    if (!videoPlayer.playNext()) {
      // No more videos, close the player
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

      const container = document.getElementById('yt-player-container');
      if (!container) {
        console.warn('[Modal] YouTube player container not found');
        useYouTubeApi = false;
        return;
      }

      const startTime = savedPlayhead;

      ytPlayer = createYouTubePlayer('yt-player-container', video.videoId, {
        onReady: () => {
          ytPlayerReady = true;
          console.log('[Modal] YouTube player ready');
          // Seek to saved position if any
          if (startTime > 0 && ytPlayer) {
            try {
              ytPlayer.seekTo(startTime, true);
              videoPlayer.clearSavedPlayhead();
            } catch {}
          }
        },
        onEnded: () => {
          console.log('[Modal] YouTube video ended');
          handleVideoEnded();
        },
        onError: (error) => {
          console.warn('[Modal] YouTube player error:', error);
          // Fall back to iframe on error
          useYouTubeApi = false;
        },
      });
    } catch (error) {
      console.warn('[Modal] Failed to init YouTube API:', error);
      useYouTubeApi = false;
    } finally {
      ytApiLoading = false;
    }
  }

  function handleKeydown(event: KeyboardEvent) {
    if (event.key === 'Escape') {
      handleClose();
    } else if (event.key === 'p' || event.key === 'P') {
      handleSwitchToPiP();
    } else if (event.key === 't' || event.key === 'T') {
      toggleTheaterMode();
    } else if (event.key === 'ArrowLeft' && hasPrevious) {
      handlePrevious();
    } else if (event.key === 'ArrowRight' && hasNext) {
      handleNext();
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
      onMarkWatched?.();
      // Fetch stream info for authenticated playback
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

  // Restore playhead for direct video element
  $effect(() => {
    if (videoElement && savedPlayhead > 0 && hasDirectStream) {
      videoElement.currentTime = savedPlayhead;
      videoPlayer.clearSavedPlayhead();
    }
  });

  // Cleanup YouTube player when switching modes or closing
  $effect(() => {
    return () => {
      if (ytPlayer) {
        try {
          ytPlayer.destroy();
        } catch {}
        ytPlayer = null;
      }
    };
  });

  // Handle visibility changes for background playback
  $effect(() => {
    if (!isOpen) return;

    function handleVisibilityChange() {
      if (document.hidden && playbackPreferences.backgroundPlayback) {
        // Tab became hidden and background playback is enabled
        if (useDirectStream && videoElement) {
          // For direct video: try to enter PiP mode to continue playback
          if (document.pictureInPictureEnabled && !document.pictureInPictureElement) {
            videoElement.requestPictureInPicture().catch(() => {
              // PiP not available, video continues in background anyway for direct streams
            });
          }
        } else if (canEmbed) {
          // For embeds: switch to PiP player which handles background playback better
          videoPlayer.switchToPiP();
        }
      } else if (!document.hidden && videoElement) {
        // Tab became visible again - exit PiP if we entered it automatically
        if (document.pictureInPictureElement === videoElement) {
          document.exitPictureInPicture().catch(() => {});
        }
      }
    }

    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => document.removeEventListener('visibilitychange', handleVisibilityChange);
  });
</script>

<svelte:window onkeydown={handleKeydown} />

{#if isOpen && video}
  <div
    class="player-overlay"
    onclick={handleBackdropClick}
    role="dialog"
    aria-modal="true"
    aria-labelledby="video-title"
  >
    <div class="player-modal" class:theater={theaterMode}>
      <!-- Header -->
      <div class="player-header">
        <div class="header-left">
          <span class="platform-badge" style="background-color: {platformColor}">
            {platformName}
          </span>
          {#if isPremium}
            <span class="premium-badge" title="Authenticated playback">
              <svg viewBox="0 0 24 24" fill="currentColor" width="14" height="14">
                <path d="M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4zm-2 16l-4-4 1.41-1.41L10 14.17l6.59-6.59L18 9l-8 8z"/>
              </svg>
              Premium
            </span>
          {/if}
          {#if queuePosition}
            <div class="queue-controls">
              <button
                class="header-btn nav-btn"
                onclick={handlePrevious}
                disabled={!hasPrevious}
                title="Previous (Left Arrow)"
              >
                <svg viewBox="0 0 24 24" fill="currentColor" width="18" height="18">
                  <path d="M15.41 7.41L14 6l-6 6 6 6 1.41-1.41L10.83 12z"/>
                </svg>
              </button>
              <span class="queue-position">{queuePosition}</span>
              <button
                class="header-btn nav-btn"
                onclick={handleNext}
                disabled={!hasNext}
                title="Next (Right Arrow)"
              >
                <svg viewBox="0 0 24 24" fill="currentColor" width="18" height="18">
                  <path d="M8.59 16.59L10 18l6-6-6-6-1.41 1.41L13.17 12z"/>
                </svg>
              </button>
            </div>
          {/if}
          {#if video.duration}
            <span class="duration">{formatDuration(video.duration)}</span>
          {/if}
        </div>
        <div class="header-right">
          {#if streamInfo?.stream_url}
            <button
              class="header-btn stream-toggle"
              class:active={useDirectStream}
              onclick={toggleDirectStream}
              title={useDirectStream ? 'Switch to embed player' : 'Switch to direct stream (no ads)'}
            >
              <svg viewBox="0 0 24 24" fill="currentColor" width="18" height="18">
                <path d="M21 3H3c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h18c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm0 16H3V5h18v14zM9 8l7 4-7 4V8z"/>
              </svg>
              <span class="stream-label">{useDirectStream ? 'Direct' : 'Embed'}</span>
            </button>
          {/if}
          <button
            class="header-btn theater-btn"
            class:active={theaterMode}
            onclick={toggleTheaterMode}
            title={theaterMode ? 'Exit Theater Mode (T)' : 'Theater Mode (T)'}
          >
            <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
              {#if theaterMode}
                <path d="M5 16h3v3h2v-5H5v2zm3-8H5v2h5V5H8v3zm6 11h2v-3h3v-2h-5v5zm2-11V5h-2v5h5V8h-3z"/>
              {:else}
                <path d="M7 14H5v5h5v-2H7v-3zm-2-4h2V7h3V5H5v5zm12 7h-3v2h5v-5h-2v3zM14 5v2h3v3h2V5h-5z"/>
              {/if}
            </svg>
          </button>
          <button
            class="header-btn pip-btn"
            onclick={handleSwitchToPiP}
            title="Mini Player (P)"
          >
            <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
              <path d="M19 7h-8v6h8V7zm2-4H3c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h18c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm0 16H3V5h18v14z"/>
            </svg>
          </button>
          <button
            class="header-btn close-btn"
            onclick={handleClose}
            title="Close (Escape)"
          >
            <svg viewBox="0 0 24 24" fill="currentColor" width="24" height="24">
              <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
            </svg>
          </button>
        </div>
      </div>

      <!-- Video Content -->
      <div class="player-content">
        {#if hasDirectStream && streamInfo?.stream_url}
          <!-- Direct stream playback (no ads, premium quality) -->
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
            {#if streamInfo.quality}
              <span class="quality-badge">{streamInfo.quality}</span>
            {/if}
          </div>
        {:else if shouldUseYtApi}
          <!-- YouTube API player for auto-advance detection -->
          <div class="yt-player-wrapper">
            {#if !ytPlayerReady || ytApiLoading}
              <div class="loading-spinner">
                <div class="spinner"></div>
              </div>
            {/if}
            <div id="yt-player-container" class="yt-player-container" class:loaded={ytPlayerReady}></div>
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
              allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share"
              allowfullscreen
              onload={handleIframeLoad}
              onerror={handleIframeError}
              class:loaded={iframeLoaded}
            ></iframe>
          </div>
        {:else}
          <EmbedFallback
            {video}
            reason={video.embedConfig.fallbackReason}
          />
        {/if}
      </div>

      <!-- Video Info -->
      <div class="player-info">
        <h2 id="video-title" class="video-title">{video.title}</h2>
        <div class="video-meta">
          {#if video.channelName}
            {#if video.channelUrl}
              <a href={video.channelUrl} target="_blank" rel="noopener noreferrer" class="channel-link">
                {video.channelName}
              </a>
            {:else}
              <span class="channel-name">{video.channelName}</span>
            {/if}
          {/if}
          <a
            href={video.videoUrl}
            target="_blank"
            rel="noopener noreferrer"
            class="external-link"
          >
            Open on {platformName}
          </a>
        </div>
      </div>
    </div>
  </div>
{/if}

<style>
  .player-overlay {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.85);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
    padding: var(--spacing-lg);
  }

  .player-modal {
    width: 100%;
    max-width: 1200px;
    max-height: 90vh;
    background: var(--color-bg-secondary);
    border-radius: var(--radius-lg);
    overflow: hidden;
    display: flex;
    flex-direction: column;
    transition: max-width 0.2s ease, max-height 0.2s ease, border-radius 0.2s ease;
  }

  /* Theater mode - fills the entire screen */
  .player-modal.theater {
    max-width: 100%;
    max-height: 100%;
    border-radius: 0;
  }

  .player-overlay:has(.player-modal.theater) {
    padding: 0;
    background: black;
  }

  /* Header */
  .player-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: var(--spacing-sm) var(--spacing-md);
    background: var(--color-bg);
    border-bottom: 1px solid var(--color-border);
  }

  .header-left {
    display: flex;
    align-items: center;
    gap: var(--spacing-md);
  }

  .platform-badge {
    padding: 2px 8px;
    border-radius: var(--radius-sm);
    color: white;
    font-size: 0.75rem;
    font-weight: 600;
    text-transform: uppercase;
  }

  .duration {
    color: var(--color-text-secondary);
    font-size: 0.875rem;
  }

  .queue-controls {
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 2px 6px;
    background: var(--color-bg-secondary);
    border-radius: var(--radius-md);
  }

  .queue-position {
    font-size: 0.75rem;
    color: var(--color-text-secondary);
    min-width: 2.5em;
    text-align: center;
  }

  .nav-btn {
    padding: 2px !important;
  }

  .nav-btn:disabled {
    opacity: 0.3;
    cursor: not-allowed;
  }

  .header-right {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
  }

  .header-btn {
    background: transparent;
    border: none;
    color: var(--color-text-secondary);
    padding: var(--spacing-xs);
    border-radius: var(--radius-sm);
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: color 0.2s, background 0.2s;
  }

  .header-btn:hover {
    color: var(--color-text);
    background: var(--color-bg-secondary);
  }

  .premium-badge {
    display: flex;
    align-items: center;
    gap: 4px;
    padding: 2px 8px;
    border-radius: var(--radius-sm);
    background: linear-gradient(135deg, #ffd700, #ffb700);
    color: #000;
    font-size: 0.7rem;
    font-weight: 600;
    text-transform: uppercase;
  }

  .stream-toggle {
    display: flex;
    align-items: center;
    gap: 4px;
    padding: var(--spacing-xs) var(--spacing-sm);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
  }

  .stream-toggle.active {
    background: var(--color-primary);
    color: white;
    border-color: var(--color-primary);
  }

  .theater-btn.active {
    color: var(--color-primary);
  }

  .stream-label {
    font-size: 0.75rem;
    font-weight: 500;
  }

  /* Video Content */
  .player-content {
    position: relative;
    width: 100%;
    aspect-ratio: 16 / 9;
    background: black;
    flex: 1;
    min-height: 0;
  }

  /* In theater mode, video fills available space */
  .player-modal.theater .player-content {
    aspect-ratio: unset;
    height: 100%;
  }

  .direct-player {
    position: relative;
    width: 100%;
    height: 100%;
  }

  .direct-video {
    width: 100%;
    height: 100%;
    background: black;
  }

  .quality-badge {
    position: absolute;
    top: var(--spacing-sm);
    right: var(--spacing-sm);
    padding: 2px 6px;
    background: rgba(0, 0, 0, 0.75);
    color: white;
    font-size: 0.7rem;
    font-weight: 600;
    border-radius: var(--radius-sm);
    pointer-events: none;
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

  .iframe-container {
    position: relative;
    width: 100%;
    height: 100%;
  }

  .iframe-container iframe {
    position: absolute;
    inset: 0;
    width: 100%;
    height: 100%;
    border: none;
    opacity: 0;
    transition: opacity 0.3s ease;
  }

  .iframe-container iframe.loaded {
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
    width: 48px;
    height: 48px;
    border: 3px solid var(--color-border);
    border-top-color: var(--color-primary);
    border-radius: 50%;
    animation: spin 1s linear infinite;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  /* Video Info */
  .player-info {
    padding: var(--spacing-md);
    background: var(--color-bg-secondary);
  }

  .video-title {
    font-size: 1.1rem;
    font-weight: 600;
    margin: 0 0 var(--spacing-sm) 0;
    color: var(--color-text);
    line-height: 1.3;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  .video-meta {
    display: flex;
    align-items: center;
    gap: var(--spacing-md);
    font-size: 0.875rem;
  }

  .channel-link,
  .channel-name {
    color: var(--color-text-secondary);
  }

  .channel-link:hover {
    color: var(--color-primary);
  }

  .external-link {
    color: var(--color-primary);
    text-decoration: none;
  }

  .external-link:hover {
    text-decoration: underline;
  }

  /* Mobile */
  @media (max-width: 768px) {
    .player-overlay {
      padding: 0;
      align-items: flex-start;
    }

    .player-modal {
      max-width: 100%;
      max-height: 100vh;
      border-radius: 0;
    }

    .video-title {
      font-size: 1rem;
    }

    .video-meta {
      flex-direction: column;
      align-items: flex-start;
      gap: var(--spacing-xs);
    }
  }
</style>
