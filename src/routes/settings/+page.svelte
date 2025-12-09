<script lang="ts">
  import { onMount } from 'svelte';
  import { api } from '$lib/api/client';

  let settings = $state<Record<string, unknown> | null>(null);
  let loading = $state(true);
  let error = $state<string | null>(null);

  onMount(async () => {
    await loadSettings();
  });

  async function loadSettings() {
    loading = true;
    error = null;
    try {
      settings = await api.getSettings();
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to load settings';
    } finally {
      loading = false;
    }
  }
</script>

<div class="settings-page">
  <header class="page-header">
    <h1>Settings</h1>
    <p class="subtitle">Configure your search engine preferences</p>
  </header>

  {#if error}
    <div class="error-message">{error}</div>
  {/if}

  {#if loading}
    <div class="loading">Loading settings...</div>
  {:else if settings}
    <div class="settings-sections">
      <!-- Crawler Settings -->
      <section class="settings-section card">
        <h2>Crawler</h2>
        <p class="section-description">Configure how the crawler fetches web pages</p>

        <div class="settings-grid">
          <div class="setting-item">
            <label>User Agent</label>
            <input
              type="text"
              class="input"
              value={(settings.crawler as Record<string, unknown>)?.user_agent || ''}
              disabled
            />
          </div>

          <div class="setting-item">
            <label>Concurrent Requests</label>
            <input
              type="number"
              class="input"
              value={(settings.crawler as Record<string, unknown>)?.concurrent_requests || 5}
              disabled
            />
          </div>

          <div class="setting-item">
            <label>Request Delay (ms)</label>
            <input
              type="number"
              class="input"
              value={(settings.crawler as Record<string, unknown>)?.request_delay_ms || 1000}
              disabled
            />
          </div>

          <div class="setting-item">
            <label>Timeout (seconds)</label>
            <input
              type="number"
              class="input"
              value={(settings.crawler as Record<string, unknown>)?.timeout_seconds || 30}
              disabled
            />
          </div>
        </div>

        <p class="coming-soon">Settings editing coming soon</p>
      </section>

      <!-- Meilisearch Settings -->
      <section class="settings-section card">
        <h2>Meilisearch</h2>
        <p class="section-description">Search engine connection settings</p>

        <div class="settings-grid">
          <div class="setting-item">
            <label>Host</label>
            <input
              type="text"
              class="input"
              value={(settings.meilisearch as Record<string, unknown>)?.host || ''}
              disabled
            />
          </div>

          <div class="setting-item">
            <label>Index Prefix</label>
            <input
              type="text"
              class="input"
              value={(settings.meilisearch as Record<string, unknown>)?.index_prefix || ''}
              disabled
            />
          </div>
        </div>
      </section>

      <!-- API Keys -->
      <section class="settings-section card">
        <h2>External API Keys</h2>
        <p class="section-description">Manage API keys for external search providers</p>

        <div class="api-providers">
          <div class="provider-card">
            <div class="provider-header">
              <span class="provider-name">Google Custom Search</span>
              <span class="provider-status unconfigured">Not configured</span>
            </div>
            <p class="provider-description">
              Search the web using Google's Custom Search API
            </p>
            <button class="btn btn-secondary" disabled>Add API Key</button>
          </div>

          <div class="provider-card">
            <div class="provider-header">
              <span class="provider-name">Bing Search</span>
              <span class="provider-status unconfigured">Not configured</span>
            </div>
            <p class="provider-description">
              Search using Microsoft's Bing Search API
            </p>
            <button class="btn btn-secondary" disabled>Add API Key</button>
          </div>

          <div class="provider-card">
            <div class="provider-header">
              <span class="provider-name">DuckDuckGo</span>
              <span class="provider-status available">No key required</span>
            </div>
            <p class="provider-description">
              Privacy-focused search (uses instant answers API)
            </p>
          </div>

          <div class="provider-card">
            <div class="provider-header">
              <span class="provider-name">Brave Search</span>
              <span class="provider-status unconfigured">Not configured</span>
            </div>
            <p class="provider-description">
              Independent search engine with privacy focus
            </p>
            <button class="btn btn-secondary" disabled>Add API Key</button>
          </div>
        </div>

        <p class="coming-soon">API key management coming in Phase 5</p>
      </section>

      <!-- Data Storage -->
      <section class="settings-section card">
        <h2>Data Storage</h2>
        <p class="section-description">Where your data is stored</p>

        <div class="setting-item">
          <label>Data Directory</label>
          <input
            type="text"
            class="input"
            value={settings.data_dir || ''}
            disabled
          />
        </div>
      </section>
    </div>
  {/if}
</div>

<style>
  .settings-page {
    max-width: 800px;
  }

  .page-header {
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

  .settings-sections {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-lg);
  }

  .settings-section h2 {
    font-size: 1.1rem;
    margin-bottom: var(--spacing-xs);
  }

  .section-description {
    color: var(--color-text-secondary);
    font-size: 0.9rem;
    margin-bottom: var(--spacing-lg);
  }

  .settings-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: var(--spacing-md);
  }

  .setting-item {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-xs);
  }

  .setting-item label {
    font-size: 0.85rem;
    font-weight: 500;
    color: var(--color-text-secondary);
  }

  .coming-soon {
    margin-top: var(--spacing-md);
    font-size: 0.85rem;
    color: var(--color-text-secondary);
    font-style: italic;
  }

  .api-providers {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
    gap: var(--spacing-md);
  }

  .provider-card {
    background: var(--color-bg);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    padding: var(--spacing-md);
  }

  .provider-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: var(--spacing-sm);
  }

  .provider-name {
    font-weight: 500;
  }

  .provider-status {
    font-size: 0.75rem;
    padding: var(--spacing-xs) var(--spacing-sm);
    border-radius: var(--radius-sm);
  }

  .provider-status.unconfigured {
    background: #fef2f2;
    color: var(--color-error);
  }

  .provider-status.available {
    background: #ecfdf5;
    color: var(--color-success);
  }

  .provider-description {
    font-size: 0.85rem;
    color: var(--color-text-secondary);
    margin-bottom: var(--spacing-sm);
  }
</style>
