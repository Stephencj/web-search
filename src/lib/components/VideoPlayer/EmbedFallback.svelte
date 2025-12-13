<script lang="ts">
  import { getPlatformName, getPlatformColor } from '$lib/utils/embedUrl';
  import type { VideoItem } from '$lib/stores/videoPlayer.svelte';

  interface Props {
    video: VideoItem;
    reason?: string;
  }

  let { video, reason }: Props = $props();

  const platformName = $derived(getPlatformName(video.platform));
  const platformColor = $derived(getPlatformColor(video.platform));
</script>

<div class="fallback-container">
  {#if video.thumbnailUrl}
    <img src={video.thumbnailUrl} alt={video.title} class="fallback-thumbnail" />
  {:else}
    <div class="no-thumbnail">
      <span class="no-thumbnail-icon">🎬</span>
    </div>
  {/if}

  <div class="fallback-overlay">
    <div class="fallback-content">
      <div class="fallback-icon">
        <svg viewBox="0 0 24 24" fill="currentColor" width="48" height="48">
          <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 14.5v-9l6 4.5-6 4.5z"/>
        </svg>
      </div>

      {#if reason}
        <p class="fallback-reason">{reason}</p>
      {:else}
        <p class="fallback-reason">This video cannot be embedded</p>
      {/if}

      <a
        href={video.videoUrl}
        target="_blank"
        rel="noopener noreferrer"
        class="watch-external-btn"
        style="background-color: {platformColor}"
      >
        Watch on {platformName}
      </a>
    </div>
  </div>
</div>

<style>
  .fallback-container {
    position: relative;
    width: 100%;
    aspect-ratio: 16 / 9;
    background: var(--color-bg);
    border-radius: var(--radius-md);
    overflow: hidden;
  }

  .fallback-thumbnail {
    width: 100%;
    height: 100%;
    object-fit: cover;
    filter: brightness(0.4);
  }

  .no-thumbnail {
    width: 100%;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    background: linear-gradient(135deg, var(--color-bg-secondary) 0%, var(--color-bg) 100%);
  }

  .no-thumbnail-icon {
    font-size: 4rem;
    opacity: 0.3;
  }

  .fallback-overlay {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(0, 0, 0, 0.3);
  }

  .fallback-content {
    text-align: center;
    color: white;
    padding: var(--spacing-lg);
  }

  .fallback-icon {
    margin-bottom: var(--spacing-md);
    opacity: 0.9;
  }

  .fallback-reason {
    margin: 0 0 var(--spacing-lg) 0;
    font-size: 1rem;
    opacity: 0.9;
  }

  .watch-external-btn {
    display: inline-flex;
    align-items: center;
    gap: var(--spacing-sm);
    padding: var(--spacing-md) var(--spacing-xl);
    color: white;
    text-decoration: none;
    border-radius: var(--radius-md);
    font-weight: 600;
    font-size: 1rem;
    transition: opacity 0.2s ease, transform 0.2s ease;
  }

  .watch-external-btn:hover {
    opacity: 0.9;
    transform: scale(1.02);
  }
</style>
