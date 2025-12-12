<script lang="ts">
  /**
   * MediaViewer - Main wrapper component that renders the appropriate view mode
   * Handles keyboard navigation and delegates to specific view components
   */
  import { onMount } from 'svelte';
  import { mediaViewer } from '$lib/stores/mediaViewer.svelte';
  import LightboxView from './LightboxView.svelte';
  import SidePanelView from './SidePanelView.svelte';

  // Keyboard navigation
  function handleKeydown(event: KeyboardEvent) {
    if (!mediaViewer.isOpen) return;

    switch (event.key) {
      case 'Escape':
        mediaViewer.close();
        break;
      case 'ArrowLeft':
        event.preventDefault();
        mediaViewer.previous();
        break;
      case 'ArrowRight':
        event.preventDefault();
        mediaViewer.next();
        break;
    }
  }

  onMount(() => {
    window.addEventListener('keydown', handleKeydown);
    return () => {
      window.removeEventListener('keydown', handleKeydown);
    };
  });
</script>

{#if mediaViewer.isOpen}
  {#if mediaViewer.viewMode === 'lightbox'}
    <LightboxView />
  {:else if mediaViewer.viewMode === 'sidepanel'}
    <SidePanelView />
  {/if}
{/if}
