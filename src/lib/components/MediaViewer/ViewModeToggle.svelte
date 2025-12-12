<script lang="ts">
  /**
   * ViewModeToggle - Buttons to switch between lightbox and sidepanel views
   */
  import { mediaViewer, type ViewMode } from '$lib/stores/mediaViewer.svelte';

  const modes: { value: ViewMode; icon: string; label: string }[] = [
    { value: 'lightbox', icon: 'maximize', label: 'Lightbox' },
    { value: 'sidepanel', icon: 'sidebar', label: 'Side Panel' },
  ];
</script>

<div class="view-mode-toggle">
  {#each modes as mode}
    <button
      class:active={mediaViewer.viewMode === mode.value}
      onclick={() => mediaViewer.setViewMode(mode.value)}
      title={mode.label}
    >
      {#if mode.icon === 'maximize'}
        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3"></path>
        </svg>
      {:else if mode.icon === 'sidebar'}
        <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
          <rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect>
          <line x1="9" y1="3" x2="9" y2="21"></line>
        </svg>
      {/if}
    </button>
  {/each}
</div>

<style>
  .view-mode-toggle {
    display: flex;
    gap: 0.25rem;
    background: rgba(255, 255, 255, 0.1);
    border-radius: 6px;
    padding: 0.25rem;
  }

  button {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 32px;
    height: 32px;
    border: none;
    background: transparent;
    color: rgba(255, 255, 255, 0.6);
    border-radius: 4px;
    cursor: pointer;
    transition: all 0.2s;
  }

  button:hover {
    background: rgba(255, 255, 255, 0.1);
    color: white;
  }

  button.active {
    background: rgba(255, 255, 255, 0.2);
    color: white;
  }
</style>
