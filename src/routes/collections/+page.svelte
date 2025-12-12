<script lang="ts">
  import { onMount } from 'svelte';
  import { api, type Collection } from '$lib/api/client';
  import {
    collections,
    loadCollections,
    createCollection,
    deleteCollection,
    loading,
    error,
  } from '$lib/stores/collections';

  let showCreateModal = $state(false);
  let newCollectionName = $state('');
  let newCollectionDescription = $state('');
  let creating = $state(false);
  let deleteConfirmId = $state<number | null>(null);
  let deleting = $state(false);

  onMount(() => {
    loadCollections();
  });

  async function handleCreate() {
    if (!newCollectionName.trim() || creating) return;

    creating = true;
    try {
      const result = await createCollection(
        newCollectionName.trim(),
        newCollectionDescription.trim() || undefined
      );
      if (result) {
        showCreateModal = false;
        newCollectionName = '';
        newCollectionDescription = '';
      }
    } finally {
      creating = false;
    }
  }

  async function handleDelete(id: number) {
    if (deleting) return;

    deleting = true;
    try {
      await deleteCollection(id);
      deleteConfirmId = null;
    } finally {
      deleting = false;
    }
  }

  async function handleExport(collection: Collection) {
    try {
      const blob = await api.exportCollection(collection.id);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${collection.slug}-collection.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (e) {
      console.error('Export failed:', e);
    }
  }
</script>

<div class="collections-page">
  <header class="page-header">
    <div class="header-content">
      <h1>Collections</h1>
      <p class="subtitle">Organize and manage your saved images and videos</p>
    </div>
    <button class="btn btn-primary" onclick={() => (showCreateModal = true)}>
      <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
        <path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z" />
      </svg>
      New Collection
    </button>
  </header>

  {#if $error}
    <div class="error-message">
      {$error}
    </div>
  {/if}

  {#if $loading}
    <div class="loading-state">
      <div class="spinner"></div>
      <p>Loading collections...</p>
    </div>
  {:else if $collections.length === 0}
    <div class="empty-state">
      <div class="empty-icon">
        <svg viewBox="0 0 24 24" fill="currentColor" width="64" height="64">
          <path
            d="M20 6h-8l-2-2H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2zm0 12H4V8h16v10z"
          />
        </svg>
      </div>
      <h2>No Collections Yet</h2>
      <p>Create your first collection to start organizing your favorite media.</p>
      <p class="hint">Right-click on any image or video to add it to a collection.</p>
      <button class="btn btn-primary" onclick={() => (showCreateModal = true)}>
        Create Your First Collection
      </button>
    </div>
  {:else}
    <div class="collections-grid">
      {#each $collections as collection}
        <div class="collection-card">
          <a href="/collections/{collection.id}" class="card-link">
            <div class="card-thumbnail">
              {#if collection.cover_url}
                <img src={collection.cover_url} alt={collection.name} />
              {:else}
                <div class="no-cover">
                  <svg viewBox="0 0 24 24" fill="currentColor" width="48" height="48">
                    <path
                      d="M20 6h-8l-2-2H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V8c0-1.1-.9-2-2-2zm0 12H4V8h16v10z"
                    />
                  </svg>
                </div>
              {/if}
              {#if collection.name === 'Favorites'}
                <span class="favorites-badge">
                  <svg viewBox="0 0 24 24" fill="currentColor" width="16" height="16">
                    <path
                      d="M12 17.27L18.18 21l-1.64-7.03L22 9.24l-7.19-.61L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21z"
                    />
                  </svg>
                </span>
              {/if}
            </div>
            <div class="card-content">
              <h3 class="card-title">{collection.name}</h3>
              {#if collection.description}
                <p class="card-description">{collection.description}</p>
              {/if}
              <div class="card-meta">
                <span class="item-count">{collection.item_count} items</span>
              </div>
            </div>
          </a>
          <div class="card-actions">
            <button
              class="action-btn"
              title="Export collection"
              onclick={() => handleExport(collection)}
            >
              <svg viewBox="0 0 24 24" fill="currentColor" width="18" height="18">
                <path d="M19 9h-4V3H9v6H5l7 7 7-7zM5 18v2h14v-2H5z" />
              </svg>
            </button>
            {#if collection.name !== 'Favorites'}
              <button
                class="action-btn danger"
                title="Delete collection"
                onclick={() => (deleteConfirmId = collection.id)}
              >
                <svg viewBox="0 0 24 24" fill="currentColor" width="18" height="18">
                  <path
                    d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"
                  />
                </svg>
              </button>
            {/if}
          </div>
        </div>
      {/each}
    </div>
  {/if}
</div>

<!-- Create Modal -->
{#if showCreateModal}
  <div class="modal-overlay" onclick={() => (showCreateModal = false)} role="presentation">
    <div
      class="modal"
      onclick={(e) => e.stopPropagation()}
      role="dialog"
      aria-labelledby="create-modal-title"
    >
      <header class="modal-header">
        <h2 id="create-modal-title">Create Collection</h2>
        <button class="close-btn" onclick={() => (showCreateModal = false)}>
          <svg viewBox="0 0 24 24" fill="currentColor" width="24" height="24">
            <path
              d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"
            />
          </svg>
        </button>
      </header>
      <div class="modal-body">
        <div class="form-group">
          <label for="collection-name">Name</label>
          <input
            id="collection-name"
            type="text"
            class="input"
            placeholder="My Collection"
            bind:value={newCollectionName}
            onkeydown={(e) => e.key === 'Enter' && handleCreate()}
          />
        </div>
        <div class="form-group">
          <label for="collection-description">Description (optional)</label>
          <textarea
            id="collection-description"
            class="input textarea"
            placeholder="A brief description..."
            bind:value={newCollectionDescription}
            rows="3"
          ></textarea>
        </div>
      </div>
      <footer class="modal-footer">
        <button class="btn btn-secondary" onclick={() => (showCreateModal = false)}>Cancel</button>
        <button
          class="btn btn-primary"
          onclick={handleCreate}
          disabled={!newCollectionName.trim() || creating}
        >
          {creating ? 'Creating...' : 'Create'}
        </button>
      </footer>
    </div>
  </div>
{/if}

<!-- Delete Confirmation Modal -->
{#if deleteConfirmId !== null}
  {@const collectionToDelete = $collections.find((c) => c.id === deleteConfirmId)}
  <div class="modal-overlay" onclick={() => (deleteConfirmId = null)} role="presentation">
    <div
      class="modal modal-sm"
      onclick={(e) => e.stopPropagation()}
      role="dialog"
      aria-labelledby="delete-modal-title"
    >
      <header class="modal-header">
        <h2 id="delete-modal-title">Delete Collection</h2>
      </header>
      <div class="modal-body">
        <p>
          Are you sure you want to delete <strong>{collectionToDelete?.name}</strong>? This will
          remove all items in the collection.
        </p>
      </div>
      <footer class="modal-footer">
        <button class="btn btn-secondary" onclick={() => (deleteConfirmId = null)}>Cancel</button>
        <button
          class="btn btn-danger"
          onclick={() => deleteConfirmId && handleDelete(deleteConfirmId)}
          disabled={deleting}
        >
          {deleting ? 'Deleting...' : 'Delete'}
        </button>
      </footer>
    </div>
  </div>
{/if}

<style>
  .collections-page {
    max-width: 1200px;
    margin: 0 auto;
  }

  .page-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: var(--spacing-xl);
    flex-wrap: wrap;
    gap: var(--spacing-md);
  }

  .header-content h1 {
    font-size: 2rem;
    margin-bottom: var(--spacing-xs);
  }

  .subtitle {
    color: var(--color-text-secondary);
  }

  .page-header .btn {
    display: flex;
    align-items: center;
    gap: var(--spacing-xs);
  }

  .error-message {
    background: #fef2f2;
    color: var(--color-error);
    padding: var(--spacing-md);
    border-radius: var(--radius-md);
    margin-bottom: var(--spacing-lg);
  }

  .loading-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: var(--spacing-xl) * 2;
    color: var(--color-text-secondary);
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

  .empty-state {
    text-align: center;
    padding: var(--spacing-xl) * 2;
  }

  .empty-icon {
    color: var(--color-text-secondary);
    opacity: 0.5;
    margin-bottom: var(--spacing-lg);
  }

  .empty-state h2 {
    margin-bottom: var(--spacing-sm);
  }

  .empty-state p {
    color: var(--color-text-secondary);
    margin-bottom: var(--spacing-sm);
  }

  .empty-state .hint {
    font-size: 0.9rem;
    margin-bottom: var(--spacing-lg);
  }

  .collections-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: var(--spacing-lg);
  }

  .collection-card {
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-lg);
    overflow: hidden;
    transition: transform 0.2s, box-shadow 0.2s;
    position: relative;
  }

  .collection-card:hover {
    transform: translateY(-2px);
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  }

  .card-link {
    display: block;
    text-decoration: none;
    color: inherit;
  }

  .card-thumbnail {
    aspect-ratio: 16/10;
    background: var(--color-bg);
    display: flex;
    align-items: center;
    justify-content: center;
    position: relative;
  }

  .card-thumbnail img {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }

  .no-cover {
    color: var(--color-text-secondary);
    opacity: 0.3;
  }

  .favorites-badge {
    position: absolute;
    top: 8px;
    right: 8px;
    background: #fbbf24;
    color: white;
    padding: 4px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .card-content {
    padding: var(--spacing-md);
  }

  .card-title {
    font-size: 1.1rem;
    font-weight: 600;
    margin-bottom: var(--spacing-xs);
  }

  .card-description {
    font-size: 0.85rem;
    color: var(--color-text-secondary);
    margin-bottom: var(--spacing-sm);
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }

  .card-meta {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    font-size: 0.8rem;
    color: var(--color-text-secondary);
  }

  .card-actions {
    position: absolute;
    top: 8px;
    left: 8px;
    display: flex;
    gap: var(--spacing-xs);
    opacity: 0;
    transition: opacity 0.2s;
  }

  .collection-card:hover .card-actions {
    opacity: 1;
  }

  .action-btn {
    background: rgba(0, 0, 0, 0.6);
    border: none;
    border-radius: var(--radius-sm);
    padding: 6px;
    cursor: pointer;
    color: white;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: background 0.2s;
  }

  .action-btn:hover {
    background: rgba(0, 0, 0, 0.8);
  }

  .action-btn.danger:hover {
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
    .page-header {
      flex-direction: column;
      align-items: stretch;
    }

    .header-content h1 {
      font-size: 1.5rem;
    }

    .collections-grid {
      grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
      gap: var(--spacing-md);
    }

    .modal {
      margin: var(--spacing-sm);
    }
  }
</style>
