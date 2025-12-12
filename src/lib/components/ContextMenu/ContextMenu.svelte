<script lang="ts">
  import { onMount, onDestroy, createEventDispatcher } from 'svelte';
  import { fade } from 'svelte/transition';

  export let x: number;
  export let y: number;
  export let visible = false;

  const dispatch = createEventDispatcher<{ close: void }>();

  let menuRef: HTMLDivElement;
  let adjustedX = x;
  let adjustedY = y;

  function handleClickOutside(event: MouseEvent) {
    if (menuRef && !menuRef.contains(event.target as Node)) {
      close();
    }
  }

  function handleKeydown(event: KeyboardEvent) {
    if (event.key === 'Escape') {
      close();
    }
  }

  function close() {
    visible = false;
    dispatch('close');
  }

  function adjustPosition() {
    if (!menuRef) return;

    const rect = menuRef.getBoundingClientRect();
    const viewportWidth = window.innerWidth;
    const viewportHeight = window.innerHeight;

    // Adjust horizontal position if menu would overflow right edge
    if (x + rect.width > viewportWidth - 10) {
      adjustedX = viewportWidth - rect.width - 10;
    } else {
      adjustedX = x;
    }

    // Adjust vertical position if menu would overflow bottom edge
    if (y + rect.height > viewportHeight - 10) {
      adjustedY = viewportHeight - rect.height - 10;
    } else {
      adjustedY = y;
    }
  }

  onMount(() => {
    document.addEventListener('click', handleClickOutside);
    document.addEventListener('keydown', handleKeydown);
    // Allow a small delay for the menu to render before adjusting position
    requestAnimationFrame(adjustPosition);
  });

  onDestroy(() => {
    document.removeEventListener('click', handleClickOutside);
    document.removeEventListener('keydown', handleKeydown);
  });

  $: if (visible && menuRef) {
    requestAnimationFrame(adjustPosition);
  }
</script>

{#if visible}
  <div
    bind:this={menuRef}
    class="context-menu"
    style="left: {adjustedX}px; top: {adjustedY}px;"
    transition:fade={{ duration: 100 }}
    role="menu"
    tabindex="-1"
  >
    <slot />
  </div>
{/if}

<style>
  .context-menu {
    position: fixed;
    z-index: 1000;
    min-width: 180px;
    background: var(--card-bg, #1a1a2e);
    border: 1px solid var(--border-color, #2a2a4a);
    border-radius: 8px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
    padding: 4px 0;
    overflow: hidden;
  }

  :global(.context-menu-item) {
    display: flex;
    align-items: center;
    gap: 10px;
    padding: 10px 14px;
    color: var(--text-secondary, #a0a0c0);
    cursor: pointer;
    transition: background-color 0.15s, color 0.15s;
    font-size: 14px;
  }

  :global(.context-menu-item:hover) {
    background: var(--hover-bg, #2a2a4a);
    color: var(--text-primary, #fff);
  }

  :global(.context-menu-item.danger) {
    color: #f87171;
  }

  :global(.context-menu-item.danger:hover) {
    background: rgba(248, 113, 113, 0.15);
    color: #f87171;
  }

  :global(.context-menu-item svg) {
    width: 16px;
    height: 16px;
    flex-shrink: 0;
  }

  :global(.context-menu-separator) {
    height: 1px;
    background: var(--border-color, #2a2a4a);
    margin: 4px 0;
  }

  :global(.context-menu-submenu) {
    position: relative;
  }

  :global(.context-menu-submenu-trigger) {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 14px;
    color: var(--text-secondary, #a0a0c0);
    cursor: pointer;
    transition: background-color 0.15s, color 0.15s;
    font-size: 14px;
  }

  :global(.context-menu-submenu-trigger:hover) {
    background: var(--hover-bg, #2a2a4a);
    color: var(--text-primary, #fff);
  }

  :global(.context-menu-submenu-content) {
    position: absolute;
    left: 100%;
    top: 0;
    min-width: 160px;
    background: var(--card-bg, #1a1a2e);
    border: 1px solid var(--border-color, #2a2a4a);
    border-radius: 8px;
    box-shadow: 0 4px 20px rgba(0, 0, 0, 0.4);
    padding: 4px 0;
    margin-left: 2px;
  }

  :global(.context-menu-label) {
    display: flex;
    align-items: center;
    gap: 10px;
  }
</style>
