<script lang="ts">
  import { fade } from 'svelte/transition';
  import {
    collections,
    loadCollections,
    quickAddToFavorites,
    addItemToCollection,
    createCollection,
  } from '$lib/stores/collections';
  import type { CollectionItemCreate } from '$lib/api/client';

  interface Props {
    mediaType: 'image' | 'video';
    mediaUrl: string;
    thumbnailUrl?: string | null;
    title?: string | null;
    sourceUrl?: string | null;
    domain?: string | null;
    embedType?: string | null;
    videoId?: string | null;
    onsaved?: (event: { collectionName: string }) => void;
  }

  let {
    mediaType,
    mediaUrl,
    thumbnailUrl = null,
    title = null,
    sourceUrl = null,
    domain = null,
    embedType = null,
    videoId = null,
    onsaved,
  }: Props = $props();

  let showModal = $state(false);
  let showNewCollectionInput = $state(false);
  let newCollectionName = $state('');
  let saving = $state(false);
  let savingToCollection = $state<number | null>(null);

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

  function openModal(e: MouseEvent | TouchEvent) {
    e.preventDefault();
    e.stopPropagation();
    if ($collections.length === 0) {
      loadCollections();
    }
    showModal = true;
  }

  function closeModal() {
    showModal = false;
    showNewCollectionInput = false;
    newCollectionName = '';
  }

  async function handleAddToFavorites() {
    if (saving) return;
    saving = true;
    try {
      const result = await quickAddToFavorites(getItemData());
      if (result) {
        onsaved?.({ collectionName: 'Favorites' });
        closeModal();
      }
    } finally {
      saving = false;
    }
  }

  async function handleAddToCollection(collectionId: number, collectionName: string) {
    if (savingToCollection !== null) return;
    savingToCollection = collectionId;
    try {
      const result = await addItemToCollection(collectionId, getItemData());
      if (result) {
        onsaved?.({ collectionName });
        closeModal();
      }
    } finally {
      savingToCollection = null;
    }
  }

  async function handleCreateAndAdd() {
    if (!newCollectionName.trim() || saving) return;
    saving = true;
    try {
      const collection = await createCollection(newCollectionName.trim());
      if (collection) {
        await handleAddToCollection(collection.id, collection.name);
      }
    } finally {
      saving = false;
      showNewCollectionInput = false;
      newCollectionName = '';
    }
  }
</script>

<button
  type="button"
  class="save-btn"
  onclick={openModal}
  title="Save to collection"
  aria-label="Save to collection"
>
  <svg viewBox="0 0 24 24" fill="currentColor" width="18" height="18">
    <path d="M17 3H7c-1.1 0-2 .9-2 2v16l7-3 7 3V5c0-1.1-.9-2-2-2z" />
  </svg>
</button>

{#if showModal}
  <!-- Backdrop -->
  <div
    class="modal-backdrop"
    onclick={closeModal}
    onkeydown={(e) => e.key === 'Escape' && closeModal()}
    role="presentation"
    transition:fade={{ duration: 150 }}
  ></div>

  <!-- Bottom Sheet Modal -->
  <div class="bottom-sheet" role="dialog" aria-label="Save to collection">
    <div class="sheet-header">
      <div class="sheet-handle"></div>
      <h3>Save to Collection</h3>
      <button class="close-btn" onclick={closeModal} aria-label="Close">
        <svg viewBox="0 0 24 24" fill="currentColor" width="24" height="24">
          <path
            d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"
          />
        </svg>
      </button>
    </div>

    <div class="sheet-content">
      <!-- Quick Add to Favorites -->
      <button class="collection-option favorites" onclick={handleAddToFavorites} disabled={saving}>
        <span class="option-icon favorites-icon">
          <svg viewBox="0 0 24 24" fill="currentColor" width="24" height="24">
            <path
              d="M12 17.27L18.18 21l-1.64-7.03L22 9.24l-7.19-.61L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21z"
            />
          </svg>
        </span>
        <span class="option-text">
          <span class="option-name">{saving ? 'Adding...' : 'Add to Favorites'}</span>
          <span class="option-desc">Quick save to your favorites</span>
        </span>
      </button>

      {#if $collections.length > 0}
        <div class="divider">
          <span>Or choose a collection</span>
        </div>

        <div class="collections-list">
          {#each $collections as collection}
            <button
              class="collection-option"
              onclick={() => handleAddToCollection(collection.id, collection.name)}
              disabled={savingToCollection === collection.id}
            >
              <span class="option-icon">
                {#if collection.cover_url}
                  <img src={collection.cover_url} alt="" />
                {:else}
                  <svg viewBox="0 0 24 24" fill="currentColor" width="24" height="24">
                    <path
                      d="M20 6h-8l-2-2H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2zm0 12H4V8h16v10z"
                    />
                  </svg>
                {/if}
              </span>
              <span class="option-text">
                <span class="option-name">
                  {savingToCollection === collection.id ? 'Adding...' : collection.name}
                </span>
                <span class="option-desc">{collection.item_count} items</span>
              </span>
            </button>
          {/each}
        </div>
      {/if}

      <div class="divider"></div>

      <!-- Create New Collection -->
      {#if showNewCollectionInput}
        <div class="new-collection-form">
          <input
            type="text"
            placeholder="Collection name..."
            bind:value={newCollectionName}
            onkeydown={(e) => {
              if (e.key === 'Enter') handleCreateAndAdd();
              if (e.key === 'Escape') {
                showNewCollectionInput = false;
                newCollectionName = '';
              }
            }}
            autofocus
          />
          <button
            class="create-btn"
            onclick={handleCreateAndAdd}
            disabled={!newCollectionName.trim() || saving}
          >
            {saving ? 'Creating...' : 'Create & Add'}
          </button>
        </div>
      {:else}
        <button class="collection-option new-collection" onclick={() => (showNewCollectionInput = true)}>
          <span class="option-icon add-icon">
            <svg viewBox="0 0 24 24" fill="currentColor" width="24" height="24">
              <path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z" />
            </svg>
          </span>
          <span class="option-text">
            <span class="option-name">New Collection</span>
            <span class="option-desc">Create a new collection</span>
          </span>
        </button>
      {/if}
    </div>
  </div>
{/if}

<style>
  .save-btn {
    position: absolute;
    top: 6px;
    right: 6px;
    width: 32px;
    height: 32px;
    border-radius: 50%;
    background: rgba(0, 0, 0, 0.6);
    border: none;
    color: white;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    opacity: 0;
    transition: opacity 0.2s, background 0.2s, transform 0.2s;
    z-index: 10;
  }

  .save-btn:hover {
    background: var(--color-primary, #6366f1);
    transform: scale(1.1);
  }

  .save-btn:active {
    transform: scale(0.95);
  }

  /* Show on hover for parent (desktop) */
  :global(.image-card:hover) .save-btn,
  :global(.video-card:hover) .save-btn {
    opacity: 1;
  }

  /* Always show on mobile */
  @media (max-width: 768px) {
    .save-btn {
      opacity: 1;
      width: 28px;
      height: 28px;
    }

    .save-btn svg {
      width: 16px;
      height: 16px;
    }
  }

  /* Modal Backdrop */
  .modal-backdrop {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.5);
    z-index: 1000;
  }

  /* Bottom Sheet */
  .bottom-sheet {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    background: var(--color-surface, #1a1a2e);
    border-radius: 16px 16px 0 0;
    z-index: 1001;
    max-height: 80vh;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    animation: slideUp 0.3s ease-out;
  }

  @keyframes slideUp {
    from {
      transform: translateY(100%);
    }
    to {
      transform: translateY(0);
    }
  }

  /* Desktop: Center modal instead of bottom sheet */
  @media (min-width: 769px) {
    .bottom-sheet {
      bottom: auto;
      top: 50%;
      left: 50%;
      transform: translate(-50%, -50%);
      border-radius: 12px;
      width: 100%;
      max-width: 400px;
      animation: fadeIn 0.2s ease-out;
    }

    @keyframes fadeIn {
      from {
        opacity: 0;
        transform: translate(-50%, -48%);
      }
      to {
        opacity: 1;
        transform: translate(-50%, -50%);
      }
    }
  }

  .sheet-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 16px 20px;
    border-bottom: 1px solid var(--color-border, #2a2a4a);
    position: relative;
  }

  .sheet-handle {
    position: absolute;
    top: 8px;
    left: 50%;
    transform: translateX(-50%);
    width: 40px;
    height: 4px;
    background: var(--color-border, #3a3a5a);
    border-radius: 2px;
  }

  @media (min-width: 769px) {
    .sheet-handle {
      display: none;
    }
  }

  .sheet-header h3 {
    font-size: 1.1rem;
    font-weight: 600;
    margin: 0;
  }

  .close-btn {
    background: none;
    border: none;
    color: var(--color-text-secondary, #a0a0c0);
    cursor: pointer;
    padding: 4px;
    border-radius: 4px;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .close-btn:hover {
    color: var(--color-text, #fff);
  }

  .sheet-content {
    padding: 12px 0;
    overflow-y: auto;
    flex: 1;
  }

  .collection-option {
    display: flex;
    align-items: center;
    gap: 12px;
    width: 100%;
    padding: 12px 20px;
    background: none;
    border: none;
    cursor: pointer;
    text-align: left;
    transition: background 0.15s;
    color: var(--color-text, #fff);
  }

  .collection-option:hover:not(:disabled) {
    background: var(--hover-bg, #2a2a4a);
  }

  .collection-option:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .collection-option.favorites {
    background: linear-gradient(90deg, rgba(251, 191, 36, 0.1), transparent);
  }

  .collection-option.favorites:hover:not(:disabled) {
    background: linear-gradient(90deg, rgba(251, 191, 36, 0.2), rgba(251, 191, 36, 0.05));
  }

  .collection-option.new-collection {
    color: var(--color-primary, #6366f1);
  }

  .option-icon {
    width: 40px;
    height: 40px;
    border-radius: 8px;
    background: var(--color-bg, #0f0f1a);
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    overflow: hidden;
  }

  .option-icon img {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }

  .option-icon svg {
    color: var(--color-text-secondary, #a0a0c0);
  }

  .option-icon.favorites-icon {
    background: linear-gradient(135deg, #fbbf24, #f59e0b);
  }

  .option-icon.favorites-icon svg {
    color: white;
  }

  .option-icon.add-icon {
    background: var(--color-primary, #6366f1);
  }

  .option-icon.add-icon svg {
    color: white;
  }

  .option-text {
    display: flex;
    flex-direction: column;
    gap: 2px;
    min-width: 0;
  }

  .option-name {
    font-weight: 500;
    font-size: 0.95rem;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .option-desc {
    font-size: 0.8rem;
    color: var(--color-text-secondary, #a0a0c0);
  }

  .divider {
    display: flex;
    align-items: center;
    padding: 12px 20px;
    font-size: 0.75rem;
    color: var(--color-text-secondary, #a0a0c0);
    text-transform: uppercase;
    letter-spacing: 0.5px;
  }

  .divider span {
    flex-shrink: 0;
  }

  .divider::before,
  .divider::after {
    content: '';
    flex: 1;
    height: 1px;
    background: var(--color-border, #2a2a4a);
  }

  .divider::before {
    margin-right: 12px;
  }

  .divider::after {
    margin-left: 12px;
  }

  .divider:empty::before {
    margin-right: 0;
  }

  .divider:empty::after {
    margin-left: 0;
  }

  .collections-list {
    max-height: 200px;
    overflow-y: auto;
  }

  .new-collection-form {
    display: flex;
    gap: 8px;
    padding: 12px 20px;
  }

  .new-collection-form input {
    flex: 1;
    padding: 10px 14px;
    border: 1px solid var(--color-border, #3a3a5a);
    border-radius: 8px;
    background: var(--color-bg, #0f0f1a);
    color: var(--color-text, #fff);
    font-size: 0.95rem;
  }

  .new-collection-form input:focus {
    outline: none;
    border-color: var(--color-primary, #6366f1);
  }

  .create-btn {
    padding: 10px 16px;
    background: var(--color-primary, #6366f1);
    color: white;
    border: none;
    border-radius: 8px;
    font-weight: 500;
    cursor: pointer;
    white-space: nowrap;
    transition: opacity 0.15s;
  }

  .create-btn:hover:not(:disabled) {
    opacity: 0.9;
  }

  .create-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }
</style>
