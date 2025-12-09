<script lang="ts">
  import { onMount } from 'svelte';
  import { api, type Index } from '$lib/api/client';

  let indexes = $state<Index[]>([]);
  let loading = $state(true);
  let error = $state<string | null>(null);

  // Create modal
  let showCreateModal = $state(false);
  let newIndexName = $state('');
  let newIndexDescription = $state('');
  let creating = $state(false);

  onMount(async () => {
    await loadIndexes();
  });

  async function loadIndexes() {
    loading = true;
    error = null;
    try {
      const response = await api.listIndexes();
      indexes = response.items;
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to load indexes';
    } finally {
      loading = false;
    }
  }

  async function createIndex() {
    if (!newIndexName.trim()) return;

    creating = true;
    try {
      const newIndex = await api.createIndex({
        name: newIndexName.trim(),
        description: newIndexDescription.trim() || undefined,
      });
      indexes = [...indexes, newIndex];
      showCreateModal = false;
      newIndexName = '';
      newIndexDescription = '';
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to create index';
    } finally {
      creating = false;
    }
  }

  async function deleteIndex(id: number) {
    if (!confirm('Are you sure you want to delete this index? This will also delete all sources and indexed pages.')) {
      return;
    }

    try {
      await api.deleteIndex(id);
      indexes = indexes.filter(idx => idx.id !== id);
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to delete index';
    }
  }
</script>

<div class="indexes-page">
  <header class="page-header">
    <div>
      <h1>Indexes</h1>
      <p class="subtitle">Manage your search index collections</p>
    </div>
    <button class="btn btn-primary" onclick={() => showCreateModal = true}>
      + Create Index
    </button>
  </header>

  {#if error}
    <div class="error-message">{error}</div>
  {/if}

  {#if loading}
    <div class="loading">Loading indexes...</div>
  {:else if indexes.length === 0}
    <div class="empty-state card">
      <div class="empty-icon">📚</div>
      <h2>No Indexes Yet</h2>
      <p>Create your first index to start organizing your search sources</p>
      <button class="btn btn-primary" onclick={() => showCreateModal = true}>
        Create Your First Index
      </button>
    </div>
  {:else}
    <div class="indexes-grid">
      {#each indexes as index}
        <article class="index-card card">
          <div class="index-header">
            <h3 class="index-name">
              <a href="/indexes/{index.id}">{index.name}</a>
            </h3>
            <span class="index-slug">{index.slug}</span>
          </div>

          {#if index.description}
            <p class="index-description">{index.description}</p>
          {/if}

          <div class="index-stats">
            <div class="stat">
              <span class="stat-value">{index.source_count}</span>
              <span class="stat-label">Sources</span>
            </div>
            <div class="stat">
              <span class="stat-value">{index.document_count}</span>
              <span class="stat-label">Documents</span>
            </div>
          </div>

          <div class="index-actions">
            <a href="/indexes/{index.id}" class="btn btn-secondary">
              Manage
            </a>
            <button
              class="btn btn-secondary btn-danger"
              onclick={() => deleteIndex(index.id)}
            >
              Delete
            </button>
          </div>
        </article>
      {/each}
    </div>
  {/if}
</div>

<!-- Create Modal -->
{#if showCreateModal}
  <div class="modal-overlay">
    <div class="modal card">
      <h2>Create New Index</h2>

      <form onsubmit={(e) => { e.preventDefault(); createIndex(); }}>
        <div class="form-group">
          <label for="name">Name</label>
          <input
            id="name"
            type="text"
            class="input"
            placeholder="e.g., AI Research, Tech News"
            bind:value={newIndexName}
            required
          />
        </div>

        <div class="form-group">
          <label for="description">Description (optional)</label>
          <textarea
            id="description"
            class="input"
            placeholder="What topics does this index cover?"
            bind:value={newIndexDescription}
            rows="3"
          ></textarea>
        </div>

        <div class="modal-actions">
          <button type="button" class="btn btn-secondary" onclick={() => showCreateModal = false}>
            Cancel
          </button>
          <button type="submit" class="btn btn-primary" disabled={creating || !newIndexName.trim()}>
            {creating ? 'Creating...' : 'Create Index'}
          </button>
        </div>
      </form>
    </div>
  </div>
{/if}

<style>
  .indexes-page {
    max-width: 1000px;
  }

  .page-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: var(--spacing-xl);
  }

  .page-header h1 {
    margin-bottom: var(--spacing-xs);
  }

  .subtitle {
    color: var(--color-text-secondary);
  }

  .error-message {
    background: #fef2f2;
    color: var(--color-error);
    padding: var(--spacing-md);
    border-radius: var(--radius-md);
    margin-bottom: var(--spacing-lg);
  }

  .loading {
    text-align: center;
    padding: var(--spacing-xl);
    color: var(--color-text-secondary);
  }

  .empty-state {
    text-align: center;
    padding: var(--spacing-xl) * 2;
  }

  .empty-icon {
    font-size: 4rem;
    margin-bottom: var(--spacing-md);
  }

  .empty-state h2 {
    margin-bottom: var(--spacing-sm);
  }

  .empty-state p {
    color: var(--color-text-secondary);
    margin-bottom: var(--spacing-lg);
  }

  .indexes-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
    gap: var(--spacing-lg);
  }

  .index-card {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-md);
  }

  .index-header {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-xs);
  }

  .index-name {
    margin: 0;
  }

  .index-name a {
    color: var(--color-text);
    text-decoration: none;
  }

  .index-name a:hover {
    color: var(--color-primary);
  }

  .index-slug {
    font-family: var(--font-mono);
    font-size: 0.8rem;
    color: var(--color-text-secondary);
  }

  .index-description {
    color: var(--color-text-secondary);
    font-size: 0.9rem;
    flex: 1;
  }

  .index-stats {
    display: flex;
    gap: var(--spacing-lg);
  }

  .stat {
    display: flex;
    flex-direction: column;
  }

  .stat-value {
    font-size: 1.5rem;
    font-weight: 600;
    color: var(--color-primary);
  }

  .stat-label {
    font-size: 0.8rem;
    color: var(--color-text-secondary);
  }

  .index-actions {
    display: flex;
    gap: var(--spacing-sm);
    padding-top: var(--spacing-md);
    border-top: 1px solid var(--color-border);
  }

  .btn-danger {
    color: var(--color-error);
  }

  .btn-danger:hover {
    background: #fef2f2;
  }

  /* Modal */
  .modal-overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
  }

  .modal {
    width: 90%;
    max-width: 500px;
    max-height: 90vh;
    overflow-y: auto;
  }

  .modal h2 {
    margin-bottom: var(--spacing-lg);
  }

  .form-group {
    margin-bottom: var(--spacing-md);
  }

  .form-group label {
    display: block;
    margin-bottom: var(--spacing-xs);
    font-weight: 500;
  }

  textarea.input {
    resize: vertical;
    min-height: 80px;
  }

  .modal-actions {
    display: flex;
    justify-content: flex-end;
    gap: var(--spacing-sm);
    margin-top: var(--spacing-lg);
  }
</style>
