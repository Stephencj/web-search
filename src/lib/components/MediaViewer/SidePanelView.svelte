<script lang="ts">
  /**
   * SidePanelView - Slide-in panel from the right for viewing media
   * Allows search results to remain visible on the left
   */
  import { mediaViewer } from '$lib/stores/mediaViewer.svelte';
  import ImageDisplay from './ImageDisplay.svelte';
  import VideoPlayer from './VideoPlayer.svelte';
  import ViewModeToggle from './ViewModeToggle.svelte';

  function handleBackdropClick(event: MouseEvent) {
    if (event.target === event.currentTarget) {
      mediaViewer.close();
    }
  }

  function handleVideoEnded() {
    console.log('[SidePanelView] Video ended, hasNext:', mediaViewer.hasNext);
    if (mediaViewer.hasNext) {
      mediaViewer.next();
    } else {
      // No more items, close the viewer
      mediaViewer.close();
    }
  }
</script>

<div class="sidepanel-overlay" onclick={handleBackdropClick} role="dialog" aria-modal="true">
  <div class="sidepanel">
    <!-- Header -->
    <div class="header">
      <div class="nav-controls">
        <button
          class="nav-button"
          onclick={() => mediaViewer.previous()}
          disabled={!mediaViewer.hasPrevious}
          aria-label="Previous"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="15 18 9 12 15 6"></polyline>
          </svg>
        </button>
        <span class="counter">
          {mediaViewer.currentIndex + 1} / {mediaViewer.totalItems}
        </span>
        <button
          class="nav-button"
          onclick={() => mediaViewer.next()}
          disabled={!mediaViewer.hasNext}
          aria-label="Next"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <polyline points="9 18 15 12 9 6"></polyline>
          </svg>
        </button>
      </div>

      <div class="header-controls">
        <ViewModeToggle />
        <button class="close-button" onclick={() => mediaViewer.close()} aria-label="Close">
          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"></line>
            <line x1="6" y1="6" x2="18" y2="18"></line>
          </svg>
        </button>
      </div>
    </div>

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

    <!-- Info footer -->
    <div class="footer">
      {#if mediaViewer.currentItem?.title}
        <h3 class="title">{mediaViewer.currentItem.title}</h3>
      {/if}
      {#if mediaViewer.currentItem?.pageUrl}
        <a
          href={mediaViewer.currentItem.pageUrl}
          target="_blank"
          rel="noopener noreferrer"
          class="source-link"
        >
          <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"></path>
            <polyline points="15 3 21 3 21 9"></polyline>
            <line x1="10" y1="14" x2="21" y2="3"></line>
          </svg>
          {mediaViewer.currentItem.domain || 'View source'}
        </a>
      {/if}
    </div>
  </div>
</div>

<style>
  .sidepanel-overlay {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.5);
    z-index: 1000;
    display: flex;
    justify-content: flex-end;
  }

  .sidepanel {
    width: 50%;
    min-width: 400px;
    max-width: 800px;
    height: 100%;
    background: #1a1a1a;
    display: flex;
    flex-direction: column;
    animation: slideIn 0.2s ease-out;
  }

  @keyframes slideIn {
    from {
      transform: translateX(100%);
    }
    to {
      transform: translateX(0);
    }
  }

  .header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 0.75rem 1rem;
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    background: rgba(0, 0, 0, 0.3);
  }

  .nav-controls {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .header-controls {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .nav-button {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    border: none;
    background: rgba(255, 255, 255, 0.1);
    color: white;
    border-radius: 4px;
    cursor: pointer;
    transition: background-color 0.2s;
  }

  .nav-button:hover:not(:disabled) {
    background: rgba(255, 255, 255, 0.2);
  }

  .nav-button:disabled {
    opacity: 0.3;
    cursor: not-allowed;
  }

  .counter {
    color: rgba(255, 255, 255, 0.7);
    font-size: 0.875rem;
    min-width: 60px;
    text-align: center;
  }

  .close-button {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    border: none;
    background: rgba(255, 255, 255, 0.1);
    color: white;
    border-radius: 4px;
    cursor: pointer;
    transition: background-color 0.2s;
  }

  .close-button:hover {
    background: rgba(255, 255, 255, 0.2);
  }

  .media-content {
    flex: 1;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 1rem;
    overflow: hidden;
  }

  .footer {
    padding: 1rem;
    border-top: 1px solid rgba(255, 255, 255, 0.1);
    background: rgba(0, 0, 0, 0.3);
  }

  .title {
    margin: 0 0 0.5rem 0;
    font-size: 1rem;
    font-weight: 500;
    color: white;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .source-link {
    display: inline-flex;
    align-items: center;
    gap: 0.375rem;
    color: rgba(255, 255, 255, 0.7);
    text-decoration: none;
    font-size: 0.875rem;
  }

  .source-link:hover {
    color: white;
    text-decoration: underline;
  }

  @media (max-width: 768px) {
    .sidepanel {
      width: 100%;
      min-width: unset;
      max-width: unset;
    }
  }
</style>
