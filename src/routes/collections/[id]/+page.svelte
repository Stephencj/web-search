<script lang="ts">
  import { page } from '$app/stores';
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { api, type CollectionWithItems, type CollectionItem } from '$lib/api/client';
  import {
    loadCollection,
    updateCollection,
    removeItemFromCollection,
    currentCollection,
    loading,
    error,
  } from '$lib/stores/collections';
  import { MediaViewer } from '$lib/components/MediaViewer';
  import { mediaViewer, type MediaItem } from '$lib/stores/mediaViewer.svelte';

  let collectionId = $derived(parseInt($page.params.id));
  let showEditModal = $state(false);
  let editName = $state('');
  let editDescription = $state('');
  let saving = $state(false);
  let deleteConfirmItemId = $state<number | null>(null);
  let deleting = $state(false);

  onMount(() => {
    if (!isNaN(collectionId)) {
      loadCollection(collectionId);
    }
  });

  $effect(() => {
    if (!isNaN(collectionId)) {
      loadCollection(collectionId);
    }
  });

  function openEditModal() {
    if ($currentCollection) {
      editName = $currentCollection.name;
      editDescription = $currentCollection.description || '';
      showEditModal = true;
    }
  }

  async function handleSave() {
    if (!editName.trim() || saving || !$currentCollection) return;

    saving = true;
    try {
      await updateCollection($currentCollection.id, {
        name: editName.trim(),
        description: editDescription.trim() || undefined,
      });
      showEditModal = false;
    } finally {
      saving = false;
    }
  }

  async function handleRemoveItem(itemId: number) {
    if (deleting || !$currentCollection) return;

    deleting = true;
    try {
      await removeItemFromCollection($currentCollection.id, itemId);
      deleteConfirmItemId = null;
    } finally {
      deleting = false;
    }
  }

  async function handleExport() {
    if (!$currentCollection) return;

    try {
      const blob = await api.exportCollection($currentCollection.id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${$currentCollection.slug}-collection.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (e) {
      console.error('Export failed:', e);
    }
  }

  function openMediaViewer(index: number) {
    if (!$currentCollection) return;

    const items: MediaItem[] = $currentCollection.items.map((item) => ({
      type: item.item_type as 'image' | 'video',
      url: item.url,
      thumbnailUrl: item.thumbnail_url || undefined,
      title: item.title || undefined,
      pageUrl: item.source_url || undefined,
      domain: item.domain || undefined,
      embedType: item.embed_type as 'direct' | 'youtube' | 'vimeo' | 'page_link' | undefined,
      videoId: item.video_id || undefined,
    }));
    mediaViewer.open(items, index);
  }
</script>

<MediaViewer />

<div class="collection-detail-page">
  {#if $loading}
    <div class="loading-state">
      <div class="spinner"></div>
      <p>Loading collection...</p>
    </div>
  {:else if $error}
    <div class="error-state">
      <p>{$error}</p>
      <a href="/collections" class="btn btn-secondary">Back to Collections</a>
    </div>
  {:else if $currentCollection}
    <header class="page-header">
      <div class="breadcrumb">
        <a href="/collections">Collections</a>
        <span class="separator">/</span>
        <span class="current">{$currentCollection.name}</span>
      </div>

      <div class="header-main">
        <div class="header-content">
          <h1>{$currentCollection.name}</h1>
          {#if $currentCollection.description}
            <p class="description">{$currentCollection.description}</p>
          {/if}
          <div class="meta">
            <span class="item-count">{$currentCollection.item_count} items</span>
          </div>
        </div>
        <div class="header-actions">
          <button class="btn btn-secondary" onclick={openEditModal}>
            <svg viewBox="0 0 24 24" fill="currentColor" width="18" height="18">
              <path
                d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04c.39-.39.39-1.02 0-1.41l-2.34-2.34c-.39-.39-1.02-.39-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z"
              />
            </svg>
            Edit
          </button>
          <button class="btn btn-secondary" onclick={handleExport}>
            <svg viewBox="0 0 24 24" fill="currentColor" width="18" height="18">
              <path d="M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z" />
            </svg>
            Export
          </button>
        </div>
      </div>
    </header>

    {#if $currentCollection.items.length === 0}
      <div class="empty-state">
        <div class="empty-icon">
          <svg viewBox="0 0 24 24" fill="currentColor" width="64" height="64">
            <path
              d="M21 19V5c0-1.1-.9-2-2-2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2zM8.5 13.5l2.5 3.01L14.5 12l4.5 6H5l3.5-4.5z"
            />
          </svg>
        </div>
        <h2>No Items Yet</h2>
        <p>This collection is empty. Right-click on any image or video to add it here.</p>
        <a href="/" class="btn btn-primary">Go to Search</a>
      </div>
    {:else}
      <div class="items-grid">
        {#each $currentCollection.items as item, index}
          <div class="item-card">
            <button
              type="button"
              class="item-button"
              onclick={() => openMediaViewer(index)}
              title={item.title || 'Click to view'}
            >
              <div class="item-thumbnail">
                {#if item.item_type === 'video'}
                  {#if item.thumbnail_url}
                    <img src={item.thumbnail_url} alt={item.title || 'Video thumbnail'} />
                  {:else}
                    <div class="no-thumbnail">
                      <svg viewBox="0 0 24 24" fill="currentColor" width="32" height="32">
                        <polygon points="5 3 19 12 5 21 5 3"></polygon>
                      </svg>
                    </div>
                  {/if}
                  <div class="play-overlay">
                    <svg viewBox="0 0 24 24" fill="white" width="40" height="40">
                      <polygon points="5 3 19 12 5 21 5 3"></polygon>
                    </svg>
                  </div>
                  {#if item.embed_type && item.embed_type !== 'direct'}
                    <span class="media-badge">{item.embed_type}</span>
                  {/if}
                {:else}
                  <img
                    src={item.thumbnail_url || item.url}
                    alt={item.title || 'Image'}
                    onerror={(e) => {
                      const target = e.target as HTMLImageElement;
                      target.style.display = 'none';
                    }}
                  />
                {/if}
              </div>
              <div class="item-info">
                <div class="item-title">{item.title || 'Untitled'}</div>
                {#if item.domain}
                  <div class="item-domain">{item.domain}</div>
                {/if}
              </div>
            </button>
            <button
              class="remove-btn"
              title="Remove from collection"
              onclick={() => (deleteConfirmItemId = item.id)}
            >
              <svg viewBox="0 0 24 24" fill="currentColor" width="16" height="16">
                <path
                  d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"
                />
              </svg>
            </button>
          </div>
        {/each}
      </div>
    {/if}
  {:else}
    <div class="error-state">
      <p>Collection not found</p>
      <a href="/collections" class="btn btn-secondary">Back to Collections</a>
    </div>
  {/if}
</div>

<!-- Edit Modal -->
{#if showEditModal && $currentCollection}
  <div class="modal-overlay" onclick={() => (showEditModal = false)} role="presentation">
    <div
      class="modal"
      onclick={(e) => e.stopPropagation()}
      role="dialog"
      aria-labelledby="edit-modal-title"
    >
      <header class="modal-header">
        <h2 id="edit-modal-title">Edit Collection</h2>
        <button class="close-btn" onclick={() => (showEditModal = false)}>
          <svg viewBox="0 0 24 24" fill="currentColor" width="24" height="24">
            <path
              d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"
            />
          </svg>
        </button>
      </header>
      <div class="modal-body">
        <div class="form-group">
          <label for="edit-name">Name</label>
          <input
            id="edit-name"
            type="text"
            class="input"
            bind:value={editName}
            onkeydown={(e) => e.key === 'Enter' && handleSave()}
          />
        </div>
        <div class="form-group">
          <label for="edit-description">Description (optional)</label>
          <textarea
            id="edit-description"
            class="input textarea"
            bind:value={editDescription}
            rows="3"
          ></textarea>
        </div>
      </div>
      <footer class="modal-footer">
        <button class="btn btn-secondary" onclick={() => (showEditModal = false)}>Cancel</button>
        <button class="btn btn-primary" onclick={handleSave} disabled={!editName.trim() || saving}>
          {saving ? 'Saving...' : 'Save Changes'}
        </button>
      </footer>
    </div>
  </div>
{/if}

<!-- Delete Item Confirmation Modal -->
{#if deleteConfirmItemId !== null}
  <div class="modal-overlay" onclick={() => (deleteConfirmItemId = null)} role="presentation">
    <div
      class="modal modal-sm"
      onclick={(e) => e.stopPropagation()}
      role="dialog"
      aria-labelledby="delete-item-modal-title"
    >
      <header class="modal-header">
        <h2 id="delete-item-modal-title">Remove Item</h2>
      </header>
      <div class="modal-body">
        <p>Are you sure you want to remove this item from the collection?</p>
      </div>
      <footer class="modal-footer">
        <button class="btn btn-secondary" onclick={() => (deleteConfirmItemId = null)}
          >Cancel</button
        >
        <button
          class="btn btn-danger"
          onclick={() => deleteConfirmItemId && handleRemoveItem(deleteConfirmItemId)}
          disabled={deleting}
        >
          {deleting ? 'Removing...' : 'Remove'}
        </button>
      </footer>
    </div>
  </div>
{/if}

<style>
  .collection-detail-page {
    max-width: 1200px;
    margin: 0 auto;
  }

  .loading-state,
  .error-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: var(--spacing-xl) * 2;
    color: var(--color-text-secondary);
    text-align: center;
  }

  .spinner {
    width: 32px;
    height: 32px;
    border: 3px solid var(--color-border);
    border-top-color: var(--color-primary);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
    margin-bottom: var(--spacing-md);
  }

  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }

  .breadcrumb {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    margin-bottom: var(--spacing-md);
    font-size: 0.9rem;
  }

  .breadcrumb a {
    color: var(--color-primary);
    text-decoration: none;
  }

  .breadcrumb a:hover {
    text-decoration: underline;
  }

  .separator {
    color: var(--color-text-secondary);
  }

  .current {
    color: var(--color-text-secondary);
  }

  .page-header {
    margin-bottom: var(--spacing-xl);
  }

  .header-main {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: var(--spacing-lg);
    flex-wrap: wrap;
  }

  .header-content h1 {
    font-size: 2rem;
    margin-bottom: var(--spacing-xs);
  }

  .description {
    color: var(--color-text-secondary);
    margin-bottom: var(--spacing-sm);
    max-width: 600px;
  }

  .meta {
    font-size: 0.9rem;
    color: var(--color-text-secondary);
  }

  .header-actions {
    display: flex;
    gap: var(--spacing-sm);
  }

  .header-actions .btn {
    display: flex;
    align-items: center;
    gap: var(--spacing-xs);
  }

  .empty-state {
    text-align: center;
    padding: var(--spacing-xl) * 2;
  }

  .empty-icon {
    color: var(--color-text-secondary);
    opacity: 0.3;
    margin-bottom: var(--spacing-lg);
  }

  .empty-state h2 {
    margin-bottom: var(--spacing-sm);
  }

  .empty-state p {
    color: var(--color-text-secondary);
    margin-bottom: var(--spacing-lg);
  }

  .items-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: var(--spacing-md);
  }

  .item-card {
    position: relative;
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    overflow: hidden;
    transition: transform 0.2s, box-shadow 0.2s;
  }

  .item-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  }

  .item-button {
    display: block;
    width: 100%;
    padding: 0;
    border: none;
    background: none;
    cursor: pointer;
    text-align: left;
  }

  .item-thumbnail {
    aspect-ratio: 1;
    background: var(--color-bg);
    display: flex;
    align-items: center;
    justify-content: center;
    position: relative;
    overflow: hidden;
  }

  .item-thumbnail img {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }

  .no-thumbnail {
    color: var(--color-text-secondary);
    opacity: 0.3;
  }

  .play-overlay {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba(0, 0, 0, 0.3);
    opacity: 0.8;
    transition: opacity 0.2s;
  }

  .item-card:hover .play-overlay {
    opacity: 1;
  }

  .media-badge {
    position: absolute;
    top: 8px;
    right: 8px;
    background: rgba(0, 0, 0, 0.7);
    color: white;
    padding: 2px 8px;
    border-radius: 4px;
    font-size: 0.7rem;
    text-transform: uppercase;
    font-weight: 600;
  }

  .item-info {
    padding: var(--spacing-sm);
  }

  .item-title {
    font-size: 0.85rem;
    font-weight: 500;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    margin-bottom: var(--spacing-xs);
    color: var(--color-text);
  }

  .item-domain {
    font-size: 0.75rem;
    color: var(--color-text-secondary);
  }

  .remove-btn {
    position: absolute;
    top: 8px;
    left: 8px;
    background: rgba(0, 0, 0, 0.6);
    border: none;
    border-radius: 50%;
    width: 28px;
    height: 28px;
    cursor: pointer;
    color: white;
    display: flex;
    align-items: center;
    justify-content: center;
    opacity: 0;
    transition: opacity 0.2s, background 0.2s;
  }

  .item-card:hover .remove-btn {
    opacity: 1;
  }

  .remove-btn:hover {
    background: var(--color-error);
  }

  /* Modal Styles */
  .modal-overlay {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
    padding: var(--spacing-md);
  }

  .modal {
    background: var(--color-surface);
    border-radius: var(--radius-lg);
    width: 100%;
    max-width: 480px;
    max-height: 90vh;
    overflow: auto;
    box-shadow: 0 20px 40px rgba(0, 0, 0, 0.3);
  }

  .modal-sm {
    max-width: 400px;
  }

  .modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: var(--spacing-lg);
    border-bottom: 1px solid var(--color-border);
  }

  .modal-header h2 {
    font-size: 1.25rem;
    margin: 0;
  }

  .close-btn {
    background: none;
    border: none;
    cursor: pointer;
    color: var(--color-text-secondary);
    padding: var(--spacing-xs);
    border-radius: var(--radius-sm);
    transition: color 0.2s;
  }

  .close-btn:hover {
    color: var(--color-text);
  }

  .modal-body {
    padding: var(--spacing-lg);
  }

  .modal-footer {
    display: flex;
    justify-content: flex-end;
    gap: var(--spacing-sm);
    padding: var(--spacing-lg);
    border-top: 1px solid var(--color-border);
  }

  .form-group {
    margin-bottom: var(--spacing-md);
  }

  .form-group:last-child {
    margin-bottom: 0;
  }

  .form-group label {
    display: block;
    margin-bottom: var(--spacing-xs);
    font-weight: 500;
    font-size: 0.9rem;
  }

  .input {
    width: 100%;
    padding: var(--spacing-sm) var(--spacing-md);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    background: var(--color-bg);
    color: var(--color-text);
    font-size: 1rem;
    transition: border-color 0.2s;
  }

  .input:focus {
    outline: none;
    border-color: var(--color-primary);
  }

  .textarea {
    resize: vertical;
    font-family: inherit;
  }

  .btn-secondary {
    background: var(--color-bg);
    color: var(--color-text);
    border: 1px solid var(--color-border);
  }

  .btn-secondary:hover {
    background: var(--color-surface);
  }

  .btn-danger {
    background: var(--color-error);
    color: white;
  }

  .btn-danger:hover {
    opacity: 0.9;
  }

  /* Mobile Styles */
  @media (max-width: 768px) {
    .header-main {
      flex-direction: column;
    }

    .header-content h1 {
      font-size: 1.5rem;
    }

    .header-actions {
      width: 100%;
    }

    .header-actions .btn {
      flex: 1;
      justify-content: center;
    }

    .items-grid {
      grid-template-columns: repeat(2, 1fr);
      gap: var(--spacing-sm);
    }

    .item-info {
      padding: var(--spacing-xs);
    }

    .item-title {
      font-size: 0.75rem;
    }

    .item-domain {
      font-size: 0.65rem;
    }
  }
</style>
