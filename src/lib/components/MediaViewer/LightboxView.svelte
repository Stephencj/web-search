<script lang="ts">
  /**
   * LightboxView - Modal overlay for viewing media
   */
  import { mediaViewer } from '$lib/stores/mediaViewer.svelte';
  import ImageDisplay from './ImageDisplay.svelte';
  import VideoPlayer from './VideoPlayer.svelte';
  import ViewModeToggle from './ViewModeToggle.svelte';

  function handleBackdropClick(event: MouseEvent) {
    // Only close if clicking the backdrop itself, not its children
    if (event.target === event.currentTarget) {
      mediaViewer.close();
    }
  }

  function handleVideoEnded() {
    console.log('[LightboxView] Video ended, hasNext:', mediaViewer.hasNext);
    if (mediaViewer.hasNext) {
      mediaViewer.next();
    } else {
      // No more items, close the viewer
      mediaViewer.close();
    }
  }
</script>

<div class="lightbox-overlay" onclick={handleBackdropClick} role="dialog" aria-modal="true">
  <div class="lightbox-container">
    <!-- Close button -->
    <button class="close-button" onclick={() => mediaViewer.close()} aria-label="Close">
      <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <line x1="18" y1="6" x2="6" y2="18"></line>
        <line x1="6" y1="6" x2="18" y2="18"></line>
      </svg>
    </button>

    <!-- Previous button -->
    {#if mediaViewer.hasPrevious}
      <button class="nav-button prev" onclick={() => mediaViewer.previous()} aria-label="Previous">
        <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="15 18 9 12 15 6"></polyline>
        </svg>
      </button>
    {/if}

    <!-- Media content -->
    <div class="media-content">
      {#if mediaViewer.currentItem}
        {#if mediaViewer.currentItem.type === 'image'}
          <ImageDisplay item={mediaViewer.currentItem} />
        {:else if mediaViewer.currentItem.type === 'video'}
          <VideoPlayer item={mediaViewer.currentItem} onEnded={handleVideoEnded} />
        {/if}
      {/if}
    </div>

    <!-- Next button -->
    {#if mediaViewer.hasNext}
      <button class="nav-button next" onclick={() => mediaViewer.next()} aria-label="Next">
        <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <polyline points="9 18 15 12 9 6"></polyline>
        </svg>
      </button>
    {/if}

    <!-- Bottom bar -->
    <div class="bottom-bar">
      <div class="info">
        {#if mediaViewer.currentItem?.title}
          <span class="title">{mediaViewer.currentItem.title}</span>
        {/if}
        {#if mediaViewer.currentItem?.pageUrl}
          <a
            href={mediaViewer.currentItem.pageUrl}
            target="_blank"
            rel="noopener noreferrer"
            class="source-link"
          >
            {mediaViewer.currentItem.domain || 'View source'}
          </a>
        {/if}
      </div>

      <div class="controls">
        <span class="counter">
          {mediaViewer.currentIndex + 1} / {mediaViewer.totalItems}
        </span>
        <ViewModeToggle />
      </div>
    </div>
  </div>
</div>

<style>
  .lightbox-overlay {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.9);
    z-index: 1000;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .lightbox-container {
    position: relative;
    width: 100%;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .close-button {
    position: absolute;
    top: 1rem;
    right: 1rem;
    background: rgba(255, 255, 255, 0.1);
    border: none;
    color: white;
    width: 40px;
    height: 40px;
    border-radius: 50%;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: background-color 0.2s;
    z-index: 10;
  }

  .close-button:hover {
    background: rgba(255, 255, 255, 0.2);
  }

  .nav-button {
    position: absolute;
    top: 50%;
    transform: translateY(-50%);
    background: rgba(255, 255, 255, 0.1);
    border: none;
    color: white;
    width: 48px;
    height: 48px;
    border-radius: 50%;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: background-color 0.2s;
    z-index: 10;
  }

  .nav-button:hover {
    background: rgba(255, 255, 255, 0.2);
  }

  .nav-button.prev {
    left: 1rem;
  }

  .nav-button.next {
    right: 1rem;
  }

  .media-content {
    max-width: calc(100% - 120px);
    max-height: calc(100% - 120px);
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .bottom-bar {
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    padding: 1rem 1.5rem;
    background: linear-gradient(transparent, rgba(0, 0, 0, 0.8));
    display: flex;
    justify-content: space-between;
    align-items: center;
    color: white;
  }

  .info {
    display: flex;
    flex-direction: column;
    gap: 0.25rem;
    max-width: 60%;
  }

  .title {
    font-size: 1rem;
    font-weight: 500;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .source-link {
    color: rgba(255, 255, 255, 0.7);
    text-decoration: none;
    font-size: 0.875rem;
  }

  .source-link:hover {
    color: white;
    text-decoration: underline;
  }

  .controls {
    display: flex;
    align-items: center;
    gap: 1rem;
  }

  .counter {
    color: rgba(255, 255, 255, 0.7);
    font-size: 0.875rem;
  }

  /* Mobile styles */
  @media (max-width: 768px) {
    .close-button {
      top: 0.5rem;
      right: 0.5rem;
      width: 36px;
      height: 36px;
    }

    .nav-button {
      width: 40px;
      height: 40px;
    }

    .nav-button.prev {
      left: 0.5rem;
    }

    .nav-button.next {
      right: 0.5rem;
    }

    .nav-button svg {
      width: 24px;
      height: 24px;
    }

    .media-content {
      max-width: calc(100% - 20px);
      max-height: calc(100% - 100px);
    }

    .bottom-bar {
      flex-direction: column;
      align-items: flex-start;
      gap: 0.5rem;
      padding: 0.75rem 1rem;
    }

    .info {
      max-width: 100%;
      width: 100%;
    }

    .title {
      font-size: 0.875rem;
    }

    .source-link {
      font-size: 0.75rem;
    }

    .controls {
      width: 100%;
      justify-content: space-between;
    }

    .counter {
      font-size: 0.75rem;
    }
  }
</style>
