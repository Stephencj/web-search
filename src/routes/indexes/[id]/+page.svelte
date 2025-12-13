<script lang="ts">
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { api, type Index, type Source } from '$lib/api/client';

  let index = $state<Index | null>(null);
  let sources = $state<Source[]>([]);
  let loading = $state(true);
  let error = $state<string | null>(null);

  // Add source modal
  let showAddSource = $state(false);
  let newSourceUrl = $state('');
  let newSourceName = $state('');
  let newSourceDepth = $state(2);
  let newSourceFrequency = $state<'hourly' | 'daily' | 'weekly' | 'monthly'>('daily');
  let newSourceCrawlMode = $state<'text_only' | 'images_only' | 'videos_only' | 'text_images' | 'text_videos' | 'images_videos' | 'all'>('all');
  let newSourceMaxPages = $state(1000);
  let addingSource = $state(false);

  // Edit index modal
  let showEditIndex = $state(false);
  let editName = $state('');
  let editDescription = $state('');
  let savingIndex = $state(false);

  // Edit source modal
  let showEditSource = $state(false);
  let editingSource = $state<Source | null>(null);
  let editSourceName = $state('');
  let editSourceDepth = $state(2);
  let editSourceFrequency = $state<'hourly' | 'daily' | 'weekly' | 'monthly'>('daily');
  let editSourceCrawlMode = $state<'text_only' | 'images_only' | 'videos_only' | 'text_images' | 'text_videos' | 'images_videos' | 'all'>('all');
  let editSourceMaxPages = $state(1000);
  let editSourceActive = $state(true);
  let savingSource = $state(false);

  $effect(() => {
    const id = $page.params.id;
    if (id) {
      loadIndex(parseInt(id));
    }
  });

  async function loadIndex(id: number) {
    loading = true;
    error = null;
    try {
      const [indexData, sourcesData] = await Promise.all([
        api.getIndex(id),
        api.listSources(id)
      ]);
      index = indexData;
      sources = sourcesData;
      editName = indexData.name;
      editDescription = indexData.description || '';
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to load index';
    } finally {
      loading = false;
    }
  }

  async function addSource() {
    if (!newSourceUrl.trim() || !index) return;

    addingSource = true;
    try {
      const source = await api.createSource(index.id, {
        url: newSourceUrl.trim(),
        name: newSourceName.trim() || undefined,
        crawl_depth: newSourceDepth,
        crawl_frequency: newSourceFrequency,
        crawl_mode: newSourceCrawlMode,
        max_pages: newSourceMaxPages,
      });
      sources = [...sources, source];
      showAddSource = false;
      resetSourceForm();
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to add source';
    } finally {
      addingSource = false;
    }
  }

  function resetSourceForm() {
    newSourceUrl = '';
    newSourceName = '';
    newSourceDepth = 2;
    newSourceFrequency = 'daily';
    newSourceCrawlMode = 'all';
    newSourceMaxPages = 1000;
  }

  function formatCrawlMode(mode: string): string {
    const modeLabels: Record<string, string> = {
      'all': 'All content',
      'text_only': 'Text only',
      'images_only': 'Images only',
      'videos_only': 'Videos only',
      'text_images': 'Text + Images',
      'text_videos': 'Text + Videos',
      'images_videos': 'Images + Videos',
    };
    return modeLabels[mode] || mode;
  }

  async function deleteSource(sourceId: number) {
    if (!confirm('Delete this source? This will remove all crawled pages from this source.')) {
      return;
    }

    try {
      await api.deleteSource(sourceId);
      sources = sources.filter(s => s.id !== sourceId);
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to delete source';
    }
  }

  async function saveIndex() {
    if (!index || !editName.trim()) return;

    savingIndex = true;
    try {
      const updated = await api.updateIndex(index.id, {
        name: editName.trim(),
        description: editDescription.trim() || undefined,
      });
      index = updated;
      showEditIndex = false;
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to update index';
    } finally {
      savingIndex = false;
    }
  }

  async function startCrawl(sourceIds: number[]) {
    try {
      const result = await api.startCrawl(sourceIds);
      alert(`Crawl started: ${result.message}`);
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to start crawl';
    }
  }

  function openEditSource(source: Source) {
    editingSource = source;
    editSourceName = source.name || '';
    editSourceDepth = source.crawl_depth;
    editSourceFrequency = source.crawl_frequency;
    editSourceCrawlMode = source.crawl_mode;
    editSourceMaxPages = source.max_pages;
    editSourceActive = source.is_active;
    showEditSource = true;
  }

  async function saveSource() {
    if (!editingSource) return;

    savingSource = true;
    try {
      const updated = await api.updateSource(editingSource.id, {
        name: editSourceName.trim() || undefined,
        crawl_depth: editSourceDepth,
        crawl_frequency: editSourceFrequency,
        crawl_mode: editSourceCrawlMode,
        max_pages: editSourceMaxPages,
        is_active: editSourceActive,
      });
      sources = sources.map(s => s.id === updated.id ? updated : s);
      showEditSource = false;
      editingSource = null;
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to update source';
    } finally {
      savingSource = false;
    }
  }

  function formatDate(dateStr: string | null): string {
    if (!dateStr) return 'Never';
    return new Date(dateStr).toLocaleDateString();
  }
</script>

<div class="index-detail">
  {#if loading}
    <div class="loading">Loading index...</div>
  {:else if error}
    <div class="error-message">{error}</div>
  {:else if index}
    <header class="page-header">
      <div class="header-info">
        <div class="breadcrumb">
          <a href="/indexes">Indexes</a> / {index.name}
        </div>
        <h1>{index.name}</h1>
        {#if index.description}
          <p class="description">{index.description}</p>
        {/if}
        <div class="index-meta">
          <span class="slug">{index.slug}</span>
          <span class="stat">{sources.length} sources</span>
          <span class="stat">{index.document_count} documents</span>
        </div>
      </div>
      <div class="header-actions">
        <button class="btn btn-secondary" onclick={() => showEditIndex = true}>
          Edit Index
        </button>
        <button class="btn btn-primary" onclick={() => showAddSource = true}>
          + Add Source
        </button>
      </div>
    </header>

    <!-- Sources List -->
    <section class="sources-section">
      <div class="section-header">
        <h2>Sources</h2>
        {#if sources.length > 0}
          <button
            class="btn btn-secondary"
            onclick={() => startCrawl(sources.map(s => s.id))}
          >
            Crawl All Sources
          </button>
        {/if}
      </div>

      {#if sources.length === 0}
        <div class="empty-state card">
          <div class="empty-icon">🌐</div>
          <h3>No Sources Yet</h3>
          <p>Add websites or domains to crawl and index</p>
          <button class="btn btn-primary" onclick={() => showAddSource = true}>
            Add Your First Source
          </button>
        </div>
      {:else}
        <div class="sources-list">
          {#each sources as source}
            <article class="source-card card">
              <div class="source-header">
                <div class="source-info">
                  <h3 class="source-name">{source.display_name}</h3>
                  <a href={source.url} target="_blank" class="source-url">{source.url}</a>
                </div>
                <span
                  class="source-status"
                  class:active={source.is_active}
                  class:inactive={!source.is_active}
                >
                  {source.is_active ? 'Active' : 'Inactive'}
                </span>
              </div>

              <div class="source-config">
                <div class="config-item">
                  <span class="config-label">Content Mode</span>
                  <span class="config-value">{formatCrawlMode(source.crawl_mode || 'all')}</span>
                </div>
                <div class="config-item">
                  <span class="config-label">Depth</span>
                  <span class="config-value">{source.crawl_depth} levels</span>
                </div>
                <div class="config-item">
                  <span class="config-label">Frequency</span>
                  <span class="config-value">{source.crawl_frequency}</span>
                </div>
                <div class="config-item">
                  <span class="config-label">Max Pages</span>
                  <span class="config-value">{source.max_pages.toLocaleString()}</span>
                </div>
                <div class="config-item">
                  <span class="config-label">Pages Indexed</span>
                  <span class="config-value">{source.page_count.toLocaleString()}</span>
                </div>
              </div>

              <div class="source-footer">
                <span class="last-crawl">
                  Last crawl: {formatDate(source.last_crawl_at)}
                </span>
                <div class="source-actions">
                  <button
                    class="btn btn-secondary btn-sm"
                    onclick={() => openEditSource(source)}
                  >
                    Edit
                  </button>
                  <button
                    class="btn btn-secondary btn-sm"
                    onclick={() => startCrawl([source.id])}
                  >
                    Crawl Now
                  </button>
                  <button
                    class="btn btn-secondary btn-sm btn-danger"
                    onclick={() => deleteSource(source.id)}
                  >
                    Delete
                  </button>
                </div>
              </div>

              {#if source.last_error}
                <div class="source-error">
                  Last error: {source.last_error}
                </div>
              {/if}
            </article>
          {/each}
        </div>
      {/if}
    </section>
  {/if}
</div>

<!-- Add Source Modal -->
{#if showAddSource}
  <div class="modal-overlay">
    <div class="modal card">
      <h2>Add Source</h2>
      <p class="modal-description">Add a website or domain to crawl</p>

      <form onsubmit={(e) => { e.preventDefault(); addSource(); }}>
        <div class="form-group">
          <label for="url">URL *</label>
          <input
            id="url"
            type="url"
            class="input"
            placeholder="https://example.com"
            bind:value={newSourceUrl}
            required
          />
          <span class="form-hint">Starting URL for the crawl</span>
        </div>

        <div class="form-group">
          <label for="name">Display Name (optional)</label>
          <input
            id="name"
            type="text"
            class="input"
            placeholder="e.g., Example Blog"
            bind:value={newSourceName}
          />
        </div>

        <div class="form-group">
          <label for="crawlMode">Content to Index</label>
          <select id="crawlMode" class="input" bind:value={newSourceCrawlMode}>
            <option value="all">All (text, images, and videos)</option>
            <option value="text_only">Text only</option>
            <option value="images_only">Images only</option>
            <option value="videos_only">Videos only</option>
            <option value="text_images">Text + Images</option>
            <option value="text_videos">Text + Videos</option>
            <option value="images_videos">Images + Videos</option>
          </select>
          <span class="form-hint">What content to extract and index from pages</span>
        </div>

        <div class="form-row">
          <div class="form-group">
            <label for="depth">Crawl Depth</label>
            <select id="depth" class="input" bind:value={newSourceDepth}>
              <option value={1}>1 level</option>
              <option value={2}>2 levels</option>
              <option value={3}>3 levels</option>
              <option value={4}>4 levels</option>
              <option value={5}>5 levels</option>
            </select>
            <span class="form-hint">How many links deep to follow</span>
          </div>

          <div class="form-group">
            <label for="frequency">Crawl Frequency</label>
            <select id="frequency" class="input" bind:value={newSourceFrequency}>
              <option value="hourly">Hourly</option>
              <option value="daily">Daily</option>
              <option value="weekly">Weekly</option>
              <option value="monthly">Monthly</option>
            </select>
          </div>
        </div>

        <div class="form-group">
          <label for="maxPages">Max Pages</label>
          <input
            id="maxPages"
            type="number"
            class="input"
            min="1"
            max="100000"
            bind:value={newSourceMaxPages}
          />
          <span class="form-hint">Maximum pages to crawl from this source</span>
        </div>

        <div class="modal-actions">
          <button type="button" class="btn btn-secondary" onclick={() => showAddSource = false}>
            Cancel
          </button>
          <button type="submit" class="btn btn-primary" disabled={addingSource || !newSourceUrl.trim()}>
            {addingSource ? 'Adding...' : 'Add Source'}
          </button>
        </div>
      </form>
    </div>
  </div>
{/if}

<!-- Edit Index Modal -->
{#if showEditIndex}
  <div class="modal-overlay">
    <div class="modal card">
      <h2>Edit Index</h2>

      <form onsubmit={(e) => { e.preventDefault(); saveIndex(); }}>
        <div class="form-group">
          <label for="editName">Name</label>
          <input
            id="editName"
            type="text"
            class="input"
            bind:value={editName}
            required
          />
        </div>

        <div class="form-group">
          <label for="editDescription">Description</label>
          <textarea
            id="editDescription"
            class="input"
            bind:value={editDescription}
            rows="3"
          ></textarea>
        </div>

        <div class="modal-actions">
          <button type="button" class="btn btn-secondary" onclick={() => showEditIndex = false}>
            Cancel
          </button>
          <button type="submit" class="btn btn-primary" disabled={savingIndex || !editName.trim()}>
            {savingIndex ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </form>
    </div>
  </div>
{/if}

<!-- Edit Source Modal -->
{#if showEditSource && editingSource}
  <div class="modal-overlay">
    <div class="modal card">
      <h2>Edit Source</h2>
      <p class="modal-description">Update source settings for {editingSource.display_name}</p>

      <form onsubmit={(e) => { e.preventDefault(); saveSource(); }}>
        <div class="form-group">
          <label for="editSourceName">Display Name (optional)</label>
          <input
            id="editSourceName"
            type="text"
            class="input"
            placeholder="e.g., Example Blog"
            bind:value={editSourceName}
          />
        </div>

        <div class="form-group">
          <label for="editCrawlMode">Content to Index</label>
          <select id="editCrawlMode" class="input" bind:value={editSourceCrawlMode}>
            <option value="all">All (text, images, and videos)</option>
            <option value="text_only">Text only</option>
            <option value="images_only">Images only</option>
            <option value="videos_only">Videos only</option>
            <option value="text_images">Text + Images</option>
            <option value="text_videos">Text + Videos</option>
            <option value="images_videos">Images + Videos</option>
          </select>
        </div>

        <div class="form-row">
          <div class="form-group">
            <label for="editDepth">Crawl Depth</label>
            <select id="editDepth" class="input" bind:value={editSourceDepth}>
              <option value={1}>1 level</option>
              <option value={2}>2 levels</option>
              <option value={3}>3 levels</option>
              <option value={4}>4 levels</option>
              <option value={5}>5 levels</option>
            </select>
          </div>

          <div class="form-group">
            <label for="editFrequency">Crawl Frequency</label>
            <select id="editFrequency" class="input" bind:value={editSourceFrequency}>
              <option value="hourly">Hourly</option>
              <option value="daily">Daily</option>
              <option value="weekly">Weekly</option>
              <option value="monthly">Monthly</option>
            </select>
          </div>
        </div>

        <div class="form-group">
          <label for="editMaxPages">Max Pages</label>
          <input
            id="editMaxPages"
            type="number"
            class="input"
            min="1"
            max="100000"
            bind:value={editSourceMaxPages}
          />
        </div>

        <div class="form-group">
          <label class="checkbox-label">
            <input type="checkbox" bind:checked={editSourceActive} />
            <span>Active (source will be crawled on schedule)</span>
          </label>
        </div>

        <div class="modal-actions">
          <button type="button" class="btn btn-secondary" onclick={() => { showEditSource = false; editingSource = null; }}>
            Cancel
          </button>
          <button type="submit" class="btn btn-primary" disabled={savingSource}>
            {savingSource ? 'Saving...' : 'Save Changes'}
          </button>
        </div>
      </form>
    </div>
  </div>
{/if}

<style>
  .index-detail {
    max-width: 900px;
  }

  .loading {
    text-align: center;
    padding: var(--spacing-xl);
    color: var(--color-text-secondary);
  }

  .error-message {
    background: #fef2f2;
    color: var(--color-error);
    padding: var(--spacing-md);
    border-radius: var(--radius-md);
    margin-bottom: var(--spacing-lg);
  }

  .page-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: var(--spacing-xl);
    gap: var(--spacing-lg);
  }

  .breadcrumb {
    font-size: 0.85rem;
    color: var(--color-text-secondary);
    margin-bottom: var(--spacing-xs);
  }

  .breadcrumb a {
    color: var(--color-primary);
  }

  .page-header h1 {
    margin-bottom: var(--spacing-xs);
  }

  .description {
    color: var(--color-text-secondary);
    margin-bottom: var(--spacing-sm);
  }

  .index-meta {
    display: flex;
    gap: var(--spacing-md);
    font-size: 0.85rem;
  }

  .slug {
    font-family: var(--font-mono);
    background: var(--color-bg);
    padding: var(--spacing-xs) var(--spacing-sm);
    border-radius: var(--radius-sm);
  }

  .stat {
    color: var(--color-text-secondary);
  }

  .header-actions {
    display: flex;
    gap: var(--spacing-sm);
    flex-shrink: 0;
  }

  .sources-section {
    margin-top: var(--spacing-xl);
  }

  .section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: var(--spacing-md);
  }

  .section-header h2 {
    font-size: 1.1rem;
  }

  .empty-state {
    text-align: center;
    padding: var(--spacing-xl) * 2;
  }

  .empty-icon {
    font-size: 3rem;
    margin-bottom: var(--spacing-md);
  }

  .empty-state h3 {
    margin-bottom: var(--spacing-sm);
  }

  .empty-state p {
    color: var(--color-text-secondary);
    margin-bottom: var(--spacing-lg);
  }

  .sources-list {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-md);
  }

  .source-card {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-md);
  }

  .source-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
  }

  .source-name {
    font-size: 1rem;
    margin: 0 0 var(--spacing-xs) 0;
  }

  .source-url {
    font-size: 0.85rem;
    color: var(--color-text-secondary);
    word-break: break-all;
  }

  .source-status {
    font-size: 0.75rem;
    padding: var(--spacing-xs) var(--spacing-sm);
    border-radius: var(--radius-sm);
    font-weight: 500;
  }

  .source-status.active {
    background: #ecfdf5;
    color: var(--color-success);
  }

  .source-status.inactive {
    background: #f3f4f6;
    color: var(--color-text-secondary);
  }

  .source-config {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
    gap: var(--spacing-md);
  }

  .config-item {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .config-label {
    font-size: 0.75rem;
    color: var(--color-text-secondary);
  }

  .config-value {
    font-weight: 500;
  }

  .source-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding-top: var(--spacing-md);
    border-top: 1px solid var(--color-border);
  }

  .last-crawl {
    font-size: 0.8rem;
    color: var(--color-text-secondary);
  }

  .source-actions {
    display: flex;
    gap: var(--spacing-sm);
  }

  .btn-sm {
    padding: var(--spacing-xs) var(--spacing-sm);
    font-size: 0.85rem;
  }

  .btn-danger {
    color: var(--color-error);
  }

  .btn-danger:hover {
    background: #fef2f2;
  }

  .source-error {
    background: #fef2f2;
    color: var(--color-error);
    padding: var(--spacing-sm);
    border-radius: var(--radius-sm);
    font-size: 0.85rem;
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
    margin-bottom: var(--spacing-xs);
  }

  .modal-description {
    color: var(--color-text-secondary);
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

  .form-hint {
    display: block;
    font-size: 0.8rem;
    color: var(--color-text-secondary);
    margin-top: var(--spacing-xs);
  }

  .form-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: var(--spacing-md);
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

  .checkbox-label {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    cursor: pointer;
  }

  .checkbox-label input[type="checkbox"] {
    width: 18px;
    height: 18px;
    cursor: pointer;
  }
</style>
