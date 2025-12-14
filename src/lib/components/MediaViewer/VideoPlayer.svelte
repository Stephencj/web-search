<script lang="ts">
  /**
   * VideoPlayer - Handles YouTube, Vimeo, and direct video playback
   */
  import type { MediaItem } from '$lib/stores/mediaViewer.svelte';
  import { loadYouTubeAPI, createYouTubePlayer, type YouTubePlayer } from '$lib/utils/youtubeApi';
  import Hls from 'hls.js';
  import { onDestroy } from 'svelte';

  interface Props {
    item: MediaItem;
    onEnded?: () => void;
  }

  let { item, onEnded }: Props = $props();

  let loading = $state(true);
  let error = $state(false);
  let videoElement: HTMLVideoElement | null = $state(null);
  let hlsInstance: Hls | null = null;

  // YouTube API state
  let ytPlayer: YouTubePlayer | null = null;
  let ytPlayerReady = $state(false);
  let ytApiLoading = $state(false);
  let useYouTubeApi = $state(true);

  // Build embed URL based on type
  const embedUrl = $derived(() => {
    if (item.embedType === 'youtube' && item.videoId) {
      return `https://www.youtube.com/embed/${item.videoId}?autoplay=1&rel=0`;
    }
    if (item.embedType === 'vimeo' && item.videoId) {
      return `https://player.vimeo.com/video/${item.videoId}?autoplay=1`;
    }
    return null;
  });

  const isYouTube = $derived(item.embedType === 'youtube' && !!item.videoId);
  const isVimeo = $derived(item.embedType === 'vimeo' && !!item.videoId);
  const isEmbed = $derived(isYouTube || isVimeo);
  const isPageLink = $derived(item.embedType === 'page_link');
  const isHlsUrl = $derived(item.url?.includes('.m3u8'));

  // Use YouTube API for YouTube videos (for end detection)
  const shouldUseYtApi = $derived(isYouTube && useYouTubeApi);

  function handleLoad() {
    loading = false;
    error = false;
  }

  function handleError() {
    loading = false;
    error = true;
  }

  function handleVideoEnded() {
    console.log('[MediaViewer VideoPlayer] Video ended');
    onEnded?.();
  }

  // YouTube API functions
  async function initYouTubePlayer() {
    if (!item.videoId || ytApiLoading || ytPlayerReady) return;

    ytApiLoading = true;
    console.log('[MediaViewer] Initializing YouTube API player for:', item.videoId);

    try {
      await loadYouTubeAPI();

      // Clean up any existing player
      cleanupYouTubePlayer();

      const player = createYouTubePlayer('mv-yt-player-container', item.videoId, {
        onReady: () => {
          ytPlayerReady = true;
          loading = false;
          console.log('[MediaViewer] YouTube player ready');
        },
        onEnded: () => {
          console.log('[MediaViewer] YouTube video ended');
          handleVideoEnded();
        },
        onError: (errorCode) => {
          console.warn('[MediaViewer] YouTube player error:', errorCode);
          // Fall back to iframe embed
          useYouTubeApi = false;
          ytApiLoading = false;
        },
      });

      if (player) {
        ytPlayer = player;
      } else {
        useYouTubeApi = false;
      }
    } catch (err) {
      console.warn('[MediaViewer] Failed to load YouTube API:', err);
      useYouTubeApi = false;
    } finally {
      ytApiLoading = false;
    }
  }

  function cleanupYouTubePlayer() {
    if (ytPlayer) {
      try {
        ytPlayer.destroy();
      } catch (e) {
        // Ignore destroy errors
      }
      ytPlayer = null;
    }
    ytPlayerReady = false;
  }

  // Initialize HLS player for .m3u8 URLs
  function initHlsPlayer(video: HTMLVideoElement, src: string) {
    if (hlsInstance) {
      hlsInstance.destroy();
      hlsInstance = null;
    }

    if (Hls.isSupported()) {
      hlsInstance = new Hls({
        enableWorker: true,
        lowLatencyMode: false,
      });
      hlsInstance.loadSource(src);
      hlsInstance.attachMedia(video);
      hlsInstance.on(Hls.Events.MANIFEST_PARSED, () => {
        video.play().catch(() => {});
      });
      hlsInstance.on(Hls.Events.ERROR, (event, data) => {
        if (data.fatal) {
          handleError();
        }
      });
    } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
      video.src = src;
      video.play().catch(() => {});
    } else {
      error = true;
    }
  }

  // Watch for video element and HLS URL changes
  $effect(() => {
    if (videoElement && isHlsUrl && item.url) {
      initHlsPlayer(videoElement, item.url);
    }
  });

  // Cleanup HLS and YouTube instances on destroy
  onDestroy(() => {
    if (hlsInstance) {
      hlsInstance.destroy();
      hlsInstance = null;
    }
    cleanupYouTubePlayer();
  });

  // Initialize YouTube API player when needed
  $effect(() => {
    if (shouldUseYtApi && item.videoId) {
      initYouTubePlayer();
    }
  });

  // Cleanup YouTube player when switching away or closing
  $effect(() => {
    if (!shouldUseYtApi) {
      cleanupYouTubePlayer();
    }
  });

  // Reset state when item changes
  $effect(() => {
    if (item) {
      loading = true;
      error = false;
      useYouTubeApi = true; // Reset to try YT API for new video
      if (hlsInstance) {
        hlsInstance.destroy();
        hlsInstance = null;
      }
      cleanupYouTubePlayer();
    }
  });
</script>

<div class="video-player">
  {#if loading}
    <div class="loading">
      <div class="spinner"></div>
    </div>
  {/if}

  {#if error}
    <div class="error">
      <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <polygon points="5 3 19 12 5 21 5 3"></polygon>
      </svg>
      <p>Failed to load video</p>
      <a href={item.url} target="_blank" rel="noopener noreferrer" class="external-link">
        Open in new tab
      </a>
    </div>
  {:else if isPageLink}
    <!-- Video page link - show thumbnail with link to source -->
    <div class="page-link-preview">
      {#if item.thumbnailUrl}
        <img
          src={item.thumbnailUrl}
          alt={item.title || 'Video thumbnail'}
          class="preview-thumbnail"
        />
      {/if}
      <div class="play-overlay">
        <div class="button-group">
          <a href={item.url} target="_blank" rel="noopener noreferrer" class="external-link-btn">
            Watch on {item.domain || 'source site'}
          </a>
        </div>
      </div>
    </div>
  {:else if shouldUseYtApi}
    <!-- YouTube video using IFrame API for end detection -->
    <div class="yt-player-wrapper" class:hidden={loading || ytApiLoading}>
      <div id="mv-yt-player-container" class="yt-player-container"></div>
    </div>
  {:else if isVimeo && embedUrl()}
    <!-- Vimeo iframe (no API integration yet) -->
    <iframe
      src={embedUrl()}
      title={item.title || 'Video'}
      allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
      allowfullscreen
      class:hidden={loading}
      onload={handleLoad}
      onerror={handleError}
    ></iframe>
  {:else if isYouTube && !useYouTubeApi && embedUrl()}
    <!-- YouTube fallback iframe (when API fails) -->
    <iframe
      src={embedUrl()}
      title={item.title || 'Video'}
      allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture"
      allowfullscreen
      class:hidden={loading}
      onload={handleLoad}
      onerror={handleError}
    ></iframe>
  {:else if isHlsUrl}
    <!-- HLS video -->
    <video
      bind:this={videoElement}
      controls
      class:hidden={loading}
      onloadeddata={handleLoad}
      onerror={handleError}
      onended={handleVideoEnded}
    >
      <track kind="captions" />
      Your browser does not support the video tag.
    </video>
  {:else}
    <!-- Direct video file -->
    <video
      controls
      autoplay
      class:hidden={loading}
      onloadeddata={handleLoad}
      onerror={handleError}
      onended={handleVideoEnded}
    >
      <source src={item.url} />
      <track kind="captions" />
      Your browser does not support the video tag.
    </video>
  {/if}
</div>

<style>
  .video-player {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 100%;
    height: 100%;
    position: relative;
    background: #000;
  }

  iframe, video {
    width: 100%;
    height: 100%;
    max-width: 100%;
    max-height: 100%;
    border: none;
    transition: opacity 0.2s ease;
  }

  iframe.hidden, video.hidden, .yt-player-wrapper.hidden {
    opacity: 0;
    position: absolute;
  }

  .yt-player-wrapper {
    width: 100%;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .yt-player-container {
    width: 100%;
    height: 100%;
  }

  .yt-player-container :global(iframe) {
    width: 100% !important;
    height: 100% !important;
  }

  .loading, .error {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 1rem;
    color: #888;
    position: absolute;
    inset: 0;
    background: rgba(0, 0, 0, 0.8);
  }

  .spinner {
    width: 40px;
    height: 40px;
    border: 3px solid rgba(255, 255, 255, 0.1);
    border-top-color: #666;
    border-radius: 50%;
    animation: spin 1s linear infinite;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  .error svg {
    opacity: 0.5;
  }

  .error p {
    margin: 0;
    font-size: 0.875rem;
  }

  .external-link {
    color: #6b9fff;
    text-decoration: none;
    font-size: 0.875rem;
    padding: 0.5rem 1rem;
    border: 1px solid #6b9fff;
    border-radius: 4px;
    transition: background-color 0.2s;
  }

  .external-link:hover {
    background-color: rgba(107, 159, 255, 0.1);
  }

  .page-link-preview {
    position: relative;
    width: 100%;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    background: #000;
  }

  .preview-thumbnail {
    max-width: 100%;
    max-height: 100%;
    object-fit: contain;
  }

  .play-overlay {
    position: absolute;
    inset: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 1rem;
    background: rgba(0, 0, 0, 0.4);
    transition: background 0.2s;
  }

  .play-overlay:hover {
    background: rgba(0, 0, 0, 0.6);
  }

  .button-group {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.75rem;
  }

  .external-link-btn {
    color: #fff;
    text-decoration: none;
    font-size: 0.875rem;
    padding: 0.5rem 1rem;
    background: rgba(255, 255, 255, 0.15);
    border: 1px solid rgba(255, 255, 255, 0.3);
    border-radius: 4px;
    transition: background-color 0.2s;
  }

  .external-link-btn:hover {
    background-color: rgba(255, 255, 255, 0.25);
  }
</style>
