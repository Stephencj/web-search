<script lang="ts">
  /**
   * ImageDisplay - Renders an image with loading state and error handling
   */
  import type { MediaItem } from '$lib/stores/mediaViewer';

  interface Props {
    item: MediaItem;
  }

  let { item }: Props = $props();

  let loading = $state(true);
  let error = $state(false);

  function handleLoad() {
    loading = false;
    error = false;
  }

  function handleError() {
    loading = false;
    error = true;
  }

  // Reset state when item changes
  $effect(() => {
    if (item) {
      loading = true;
      error = false;
    }
  });
</script>

<div class="image-display">
  {#if loading}
    <div class="loading">
      <div class="spinner"></div>
    </div>
  {/if}

  {#if error}
    <div class="error">
      <svg xmlns="http://www.w3.org/2000/svg" width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
        <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
        <circle cx="8.5" cy="8.5" r="1.5"></circle>
        <polyline points="21 15 16 10 5 21"></polyline>
      </svg>
      <p>Failed to load image</p>
    </div>
  {:else}
    <img
      src={item.url}
      alt={item.alt || item.title || 'Image'}
      class:hidden={loading}
      onload={handleLoad}
      onerror={handleError}
    />
  {/if}
</div>

<style>
  .image-display {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 100%;
    height: 100%;
    position: relative;
  }

  img {
    max-width: 100%;
    max-height: 100%;
    object-fit: contain;
    transition: opacity 0.2s ease;
  }

  img.hidden {
    opacity: 0;
    position: absolute;
  }

  .loading, .error {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 1rem;
    color: #888;
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
</style>
