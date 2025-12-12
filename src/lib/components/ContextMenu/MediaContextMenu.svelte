<script lang="ts">
  import { onMount, createEventDispatcher } from 'svelte';
  import { fade } from 'svelte/transition';
  import ContextMenu from './ContextMenu.svelte';
  import {
    collections,
    loadCollections,
    quickAddToFavorites,
    addItemToCollection,
    createCollection,
  } from '$lib/stores/collections';
  import type { CollectionItemCreate } from '$lib/api/client';

  export let x: number;
  export let y: number;
  export let visible = false;
  export let mediaType: 'image' | 'video';
  export let mediaUrl: string;
  export let thumbnailUrl: string | null = null;
  export let title: string | null = null;
  export let sourceUrl: string | null = null;
  export let domain: string | null = null;
  export let embedType: string | null = null;
  export let videoId: string | null = null;

  const dispatch = createEventDispatcher<{
    close: void;
    added: { collectionName: string };
  }>();

  let showSubmenu = false;
  let showNewCollectionInput = false;
  let newCollectionName = '';
  let addingToFavorites = false;
  let addingToCollection: number | null = null;

  function getItemData(): CollectionItemCreate {
    return {
      item_type: mediaType,
      url: mediaUrl,
      thumbnail_url: thumbnailUrl,
      title: title,
      source_url: sourceUrl,
      domain: domain,
      embed_type: embedType,
      video_id: videoId,
    };
  }

  async function handleAddToFavorites() {
    addingToFavorites = true;
    try {
      const result = await quickAddToFavorites(getItemData());
      if (result) {
        dispatch('added', { collectionName: 'Favorites' });
        close();
      }
    } finally {
      addingToFavorites = false;
    }
  }

  async function handleAddToCollection(collectionId: number, collectionName: string) {
    addingToCollection = collectionId;
    try {
      const result = await addItemToCollection(collectionId, getItemData());
      if (result) {
        dispatch('added', { collectionName });
        close();
      }
    } finally {
      addingToCollection = null;
    }
  }

  async function handleCreateAndAdd() {
    if (!newCollectionName.trim()) return;

    const collection = await createCollection(newCollectionName.trim());
    if (collection) {
      await handleAddToCollection(collection.id, collection.name);
    }
    showNewCollectionInput = false;
    newCollectionName = '';
  }

  function handleOpenInNewTab() {
    window.open(mediaUrl, '_blank');
    close();
  }

  function handleCopyUrl() {
    navigator.clipboard.writeText(mediaUrl);
    close();
  }

  function close() {
    visible = false;
    showSubmenu = false;
    showNewCollectionInput = false;
    dispatch('close');
  }

  onMount(() => {
    // Load collections if not already loaded
    if ($collections.length === 0) {
      loadCollections();
    }
  });
</script>

<ContextMenu {x} {y} {visible} on:close={close}>
  <!-- Add to Favorites -->
  <button
    class="context-menu-item"
    on:click={handleAddToFavorites}
    disabled={addingToFavorites}
  >
    <svg viewBox="0 0 24 24" fill="currentColor">
      <path d="M12 17.27L18.18 21l-1.64-7.03L22 9.24l-7.19-.61L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21z" />
    </svg>
    <span class="context-menu-label">
      {addingToFavorites ? 'Adding...' : 'Add to Favorites'}
    </span>
  </button>

  <!-- Add to Collection submenu -->
  <div
    class="context-menu-submenu"
    on:mouseenter={() => (showSubmenu = true)}
    on:mouseleave={() => {
      if (!showNewCollectionInput) showSubmenu = false;
    }}
    role="menuitem"
  >
    <div class="context-menu-submenu-trigger">
      <span class="context-menu-label">
        <svg viewBox="0 0 24 24" fill="currentColor">
          <path d="M20 6h-8l-2-2H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2zm0 12H4V8h16v10z" />
        </svg>
        Add to Collection
      </span>
      <svg viewBox="0 0 24 24" fill="currentColor" width="16" height="16">
        <path d="M10 6L8.59 7.41 13.17 12l-4.58 4.59L10 18l6-6z" />
      </svg>
    </div>

    {#if showSubmenu}
      <div class="context-menu-submenu-content" transition:fade={{ duration: 100 }}>
        {#each $collections as collection}
          <button
            class="context-menu-item"
            on:click={() => handleAddToCollection(collection.id, collection.name)}
            disabled={addingToCollection === collection.id}
          >
            {addingToCollection === collection.id ? 'Adding...' : collection.name}
            <span class="item-count">({collection.item_count})</span>
          </button>
        {/each}

        {#if $collections.length > 0}
          <div class="context-menu-separator" />
        {/if}

        {#if showNewCollectionInput}
          <div class="new-collection-input">
            <input
              type="text"
              placeholder="Collection name..."
              bind:value={newCollectionName}
              on:keydown={(e) => {
                if (e.key === 'Enter') handleCreateAndAdd();
                if (e.key === 'Escape') {
                  showNewCollectionInput = false;
                  newCollectionName = '';
                }
              }}
              autofocus
            />
            <button class="create-btn" on:click={handleCreateAndAdd}>
              <svg viewBox="0 0 24 24" fill="currentColor">
                <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z" />
              </svg>
            </button>
          </div>
        {:else}
          <button
            class="context-menu-item new-collection"
            on:click={() => (showNewCollectionInput = true)}
          >
            <svg viewBox="0 0 24 24" fill="currentColor">
              <path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z" />
            </svg>
            New Collection...
          </button>
        {/if}
      </div>
    {/if}
  </div>

  <div class="context-menu-separator" />

  <!-- Open in New Tab -->
  <button class="context-menu-item" on:click={handleOpenInNewTab}>
    <svg viewBox="0 0 24 24" fill="currentColor">
      <path d="M19 19H5V5h7V3H5c-1.11 0-2 .9-2 2v14c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2v-7h-2v7zM14 3v2h3.59l-9.83 9.83 1.41 1.41L19 6.41V10h2V3h-7z" />
    </svg>
    <span class="context-menu-label">Open in New Tab</span>
  </button>

  <!-- Copy URL -->
  <button class="context-menu-item" on:click={handleCopyUrl}>
    <svg viewBox="0 0 24 24" fill="currentColor">
      <path d="M16 1H4c-1.1 0-2 .9-2 2v14h2V3h12V1zm3 4H8c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h11c1.1 0 2-.9 2-2V7c0-1.1-.9-2-2-2zm0 16H8V7h11v14z" />
    </svg>
    <span class="context-menu-label">Copy URL</span>
  </button>
</ContextMenu>

<style>
  .item-count {
    margin-left: auto;
    font-size: 12px;
    opacity: 0.6;
  }

  .new-collection {
    color: var(--accent-color, #6366f1);
  }

  .new-collection-input {
    display: flex;
    align-items: center;
    padding: 6px 10px;
    gap: 6px;
  }

  .new-collection-input input {
    flex: 1;
    background: var(--input-bg, #2a2a4a);
    border: 1px solid var(--border-color, #3a3a5a);
    border-radius: 4px;
    padding: 6px 10px;
    color: var(--text-primary, #fff);
    font-size: 13px;
  }

  .new-collection-input input:focus {
    outline: none;
    border-color: var(--accent-color, #6366f1);
  }

  .create-btn {
    background: var(--accent-color, #6366f1);
    border: none;
    border-radius: 4px;
    padding: 6px;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .create-btn svg {
    width: 16px;
    height: 16px;
    color: white;
  }

  .create-btn:hover {
    opacity: 0.9;
  }
</style>
