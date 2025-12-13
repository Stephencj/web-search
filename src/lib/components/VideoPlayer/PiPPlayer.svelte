<script lang="ts">
  import { videoPlayer, formatDuration } from '$lib/stores/videoPlayer.svelte';
  import { getPlatformName, getPlatformColor } from '$lib/utils/embedUrl';
  import EmbedFallback from './EmbedFallback.svelte';

  // Dragging state
  let isDragging = $state(false);
  let position = $state({ x: 0, y: 0 });
  let dragOffset = $state({ x: 0, y: 0 });
  let playerRef: HTMLDivElement | undefined = $state();
  let iframeLoaded = $state(false);
  let iframeError = $state(false);

  // Size: small (320x180) or medium (480x270)
  let size = $state<'small' | 'medium'>('small');

  // Computed values
  const video = $derived(videoPlayer.currentVideo);
  const isOpen = $derived(videoPlayer.isPiP && video !== null);
  const embedUrl = $derived(video?.embedConfig.embedUrl);
  const canEmbed = $derived(video?.embedConfig.supportsEmbed && !iframeError);
  const platformName = $derived(video ? getPlatformName(video.platform) : '');
  const platformColor = $derived(video ? getPlatformColor(video.platform) : '#666');

  const dimensions = $derived(size === 'small' ? { width: 320, height: 180 } : { width: 480, height: 270 });

  function handleClose() {
    videoPlayer.close();
    iframeLoaded = false;
    iframeError = false;
    position = { x: 0, y: 0 };
  }

  function handleExpand() {
    videoPlayer.switchToModal();
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
    }
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
      {#if canEmbed && embedUrl}
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
        <span class="platform-badge" style="background-color: {platformColor}">
          {platformName}
        </span>
        <div class="controls-right">
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
      transparent 30%,
      transparent 70%,
      rgba(0, 0, 0, 0.6) 100%
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

  .platform-badge {
    padding: 2px 6px;
    border-radius: var(--radius-sm);
    color: white;
    font-size: 0.65rem;
    font-weight: 600;
    text-transform: uppercase;
    pointer-events: auto;
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

  .close-btn:hover {
    background: var(--color-error);
  }

  .controls-bottom {
    pointer-events: auto;
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
