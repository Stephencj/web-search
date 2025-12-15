<script lang="ts">
  import { onMount } from 'svelte';
  import { api, type Channel, type ImportResult, type ChannelSearchResult, type PlatformAccount, type ImportSubscriptionsResult } from '$lib/api/client';

  let channels = $state<Channel[]>([]);
  let loading = $state(true);
  let error = $state<string | null>(null);
  let syncing = $state(false);
  let syncingChannelId = $state<number | null>(null);

  // Add channel modal
  let showAddModal = $state(false);
  let newChannelUrl = $state('');
  let adding = $state(false);
  let addError = $state<string | null>(null);

  // Channel search
  let searchQuery = $state('');
  let searchPlatform = $state<'youtube' | 'rumble' | 'podcast'>('youtube');
  let searchResults = $state<ChannelSearchResult[]>([]);
  let searching = $state(false);
  let searchError = $state<string | null>(null);
  let addMode = $state<'search' | 'url'>('search');
  let searchTimeout: ReturnType<typeof setTimeout> | null = null;

  // Import modal
  let showImportModal = $state(false);
  let importUrls = $state('');
  let importFile: FileList | null = $state(null);
  let importing = $state(false);
  let importResult = $state<ImportResult | null>(null);

  // Delete confirmation
  let deleteConfirmId = $state<number | null>(null);
  let deleting = $state(false);

  // Filters
  let platformFilter = $state<'all' | 'youtube' | 'rumble' | 'podcast'>('all');

  // YouTube account import
  let youtubeAccounts = $state<PlatformAccount[]>([]);
  let loadingAccounts = $state(false);
  let importingFromAccount = $state(false);
  let accountImportResult = $state<ImportSubscriptionsResult | null>(null);

  onMount(() => {
    loadChannels();
  });

  async function loadChannels() {
    loading = true;
    error = null;
    try {
      const params = platformFilter !== 'all' ? { platform: platformFilter } : undefined;
      const response = await api.listChannels(params);
      channels = response.items;
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to load channels';
    } finally {
      loading = false;
    }
  }

  async function handleAddChannel() {
    if (!newChannelUrl.trim() || adding) return;

    adding = true;
    addError = null;
    try {
      const channel = await api.addChannel(newChannelUrl.trim());
      channels = [channel, ...channels];
      closeAddModal();
    } catch (e) {
      addError = e instanceof Error ? e.message : 'Failed to add channel';
    } finally {
      adding = false;
    }
  }

  async function handleAddFromSearch(result: ChannelSearchResult) {
    adding = true;
    addError = null;
    try {
      const channel = await api.addChannel(result.channel_url);
      channels = [channel, ...channels];
      closeAddModal();
    } catch (e) {
      addError = e instanceof Error ? e.message : 'Failed to add channel';
    } finally {
      adding = false;
    }
  }

  async function searchChannels() {
    if (!searchQuery.trim() || searching) return;

    searching = true;
    searchError = null;
    try {
      const response = await api.searchChannels({
        query: searchQuery.trim(),
        platform: searchPlatform,
        limit: 10,
      });
      searchResults = response.results;
    } catch (e) {
      searchError = e instanceof Error ? e.message : 'Search failed';
      searchResults = [];
    } finally {
      searching = false;
    }
  }

  function handleSearchInput() {
    if (searchTimeout) clearTimeout(searchTimeout);
    if (searchQuery.trim().length >= 2) {
      searchTimeout = setTimeout(() => {
        searchChannels();
      }, 500);
    } else {
      searchResults = [];
    }
  }

  function closeAddModal() {
    showAddModal = false;
    newChannelUrl = '';
    searchQuery = '';
    searchResults = [];
    searchError = null;
    addError = null;
    addMode = 'search';
  }

  function formatSubscriberCount(count: number | null): string {
    if (!count) return '';
    if (count >= 1000000) return `${(count / 1000000).toFixed(1)}M`;
    if (count >= 1000) return `${(count / 1000).toFixed(1)}K`;
    return count.toString();
  }

  async function handleImportUrls() {
    if (!importUrls.trim() || importing) return;

    importing = true;
    importResult = null;
    try {
      const urls = importUrls
        .split('\n')
        .map((u) => u.trim())
        .filter((u) => u);
      const result = await api.importChannelsFromUrls(urls);
      importResult = result;
      if (result.imported > 0) {
        await loadChannels();
      }
    } catch (e) {
      importResult = {
        imported: 0,
        skipped: 0,
        failed: 1,
        channels: [],
        errors: [e instanceof Error ? e.message : 'Import failed'],
      };
    } finally {
      importing = false;
    }
  }

  async function handleImportTakeout() {
    if (!importFile || !importFile[0] || importing) return;

    importing = true;
    importResult = null;
    try {
      const file = importFile[0];
      const text = await file.text();
      const data = JSON.parse(text);
      const result = await api.importChannelsFromTakeout(data);
      importResult = result;
      if (result.imported > 0) {
        await loadChannels();
      }
    } catch (e) {
      importResult = {
        imported: 0,
        skipped: 0,
        failed: 1,
        channels: [],
        errors: [e instanceof Error ? e.message : 'Failed to parse takeout file'],
      };
    } finally {
      importing = false;
    }
  }

  async function loadYoutubeAccounts() {
    loadingAccounts = true;
    try {
      const accounts = await api.listAccounts();
      youtubeAccounts = accounts.filter((a) => a.platform === 'youtube' && a.is_active);
    } catch (e) {
      console.error('Failed to load accounts:', e);
      youtubeAccounts = [];
    } finally {
      loadingAccounts = false;
    }
  }

  async function handleImportFromAccount(accountId: number) {
    if (importingFromAccount) return;

    importingFromAccount = true;
    accountImportResult = null;
    try {
      const result = await api.importSubscriptionsFromAccount(accountId);
      accountImportResult = result;
      if (result.imported > 0) {
        await loadChannels();
      }
    } catch (e) {
      accountImportResult = {
        imported: 0,
        skipped: 0,
        failed: 1,
        total_found: 0,
      };
    } finally {
      importingFromAccount = false;
    }
  }

  // Load accounts when import modal opens
  $effect(() => {
    if (showImportModal) {
      loadYoutubeAccounts();
      accountImportResult = null;
    }
  });

  async function handleSyncChannel(id: number) {
    syncingChannelId = id;
    try {
      await api.syncChannel(id);
      await loadChannels();
    } catch (e) {
      console.error('Sync failed:', e);
    } finally {
      syncingChannelId = null;
    }
  }

  async function handleSyncAll() {
    syncing = true;
    try {
      await api.syncAllFeeds();
      // Sync now runs in background on the server - show brief feedback
      setTimeout(() => {
        syncing = false;
      }, 1500);
    } catch (e) {
      console.error('Sync all failed:', e);
      syncing = false;
    }
  }

  async function handleDelete(id: number) {
    if (deleting) return;

    deleting = true;
    try {
      await api.deleteChannel(id);
      channels = channels.filter((c) => c.id !== id);
      deleteConfirmId = null;
    } catch (e) {
      console.error('Delete failed:', e);
    } finally {
      deleting = false;
    }
  }

  async function handleToggleActive(channel: Channel) {
    try {
      const updated = await api.updateChannel(channel.id, { is_active: !channel.is_active });
      channels = channels.map((c) => (c.id === channel.id ? updated : c));
    } catch (e) {
      console.error('Toggle failed:', e);
    }
  }

  function formatDate(dateStr: string | null): string {
    if (!dateStr) return 'Never';
    return new Date(dateStr).toLocaleDateString();
  }

  function getPlatformIcon(platform: string): string {
    if (platform === 'youtube') return 'YT';
    if (platform === 'rumble') return 'R';
    if (platform === 'podcast') return '🎙️';
    return '?';
  }

  function getPlatformColor(platform: string): string {
    if (platform === 'youtube') return '#ff0000';
    if (platform === 'rumble') return '#85c742';
    if (platform === 'podcast') return '#8B5CF6';
    return '#666666';
  }

  $effect(() => {
    if (platformFilter) {
      loadChannels();
    }
  });
</script>

<div class="subscriptions-page">
  <header class="page-header">
    <div class="header-content">
      <h1>Subscriptions</h1>
      <p class="subtitle">Manage your video channel subscriptions</p>
    </div>
    <div class="header-actions">
      <button class="btn btn-secondary" onclick={handleSyncAll} disabled={syncing}>
        {syncing ? 'Syncing...' : 'Sync All'}
      </button>
      <button class="btn btn-secondary" onclick={() => (showImportModal = true)}>Import</button>
      <button class="btn btn-primary" onclick={() => (showAddModal = true)}>Add Channel</button>
    </div>
  </header>

  <!-- Filters -->
  <div class="filters">
    <div class="filter-group">
      <label>Platform:</label>
      <select bind:value={platformFilter} class="select">
        <option value="all">All</option>
        <option value="youtube">YouTube</option>
        <option value="rumble">Rumble</option>
        <option value="podcast">Podcast</option>
      </select>
    </div>
    <div class="channel-count">
      {channels.length} channel{channels.length !== 1 ? 's' : ''}
    </div>
  </div>

  {#if error}
    <div class="error-message">{error}</div>
  {/if}

  {#if loading}
    <div class="loading-state">
      <div class="spinner"></div>
      <p>Loading channels...</p>
    </div>
  {:else if channels.length === 0}
    <div class="empty-state">
      <div class="empty-icon">
        <svg viewBox="0 0 24 24" fill="currentColor" width="64" height="64">
          <path
            d="M18 3v2h-2V3H8v2H6V3H4v18h2v-2h2v2h8v-2h2v2h2V3h-2zM8 17H6v-2h2v2zm0-4H6v-2h2v2zm0-4H6V7h2v2zm10 8h-2v-2h2v2zm0-4h-2v-2h2v2zm0-4h-2V7h2v2z"
          />
        </svg>
      </div>
      <h2>No Subscriptions Yet</h2>
      <p>Add channels to start building your personal video feed.</p>
      <div class="empty-actions">
        <button class="btn btn-primary" onclick={() => (showAddModal = true)}>
          Add Your First Channel
        </button>
        <button class="btn btn-secondary" onclick={() => (showImportModal = true)}>
          Import from YouTube
        </button>
      </div>
    </div>
  {:else}
    <div class="channels-list">
      {#each channels as channel}
        <div class="channel-card" class:inactive={!channel.is_active}>
          <div class="channel-avatar">
            {#if channel.avatar_url}
              <img src={channel.avatar_url} alt={channel.name} />
            {:else}
              <div
                class="avatar-placeholder"
                style="background-color: {getPlatformColor(channel.platform)}"
              >
                {getPlatformIcon(channel.platform)}
              </div>
            {/if}
          </div>

          <div class="channel-info">
            <div class="channel-header">
              <h3 class="channel-name">{channel.display_name}</h3>
              <span class="platform-badge" class:youtube={channel.platform === 'youtube'} class:podcast={channel.platform === 'podcast'}>
                {channel.platform}
              </span>
            </div>
            <div class="channel-meta">
              <span>{channel.video_count} {channel.platform === 'podcast' ? 'episodes' : 'videos'}</span>
              <span class="separator">|</span>
              <span>{channel.unwatched_count} unwatched</span>
              {#if channel.subscriber_count}
                <span class="separator">|</span>
                <span>{channel.subscriber_count.toLocaleString()} subscribers</span>
              {/if}
            </div>
            <div class="channel-sync">
              {#if channel.last_sync_error}
                <span class="sync-error" title={channel.last_sync_error}>Sync error</span>
              {:else}
                <span class="sync-time">Last synced: {formatDate(channel.last_synced_at)}</span>
              {/if}
            </div>
          </div>

          <div class="channel-actions">
            <button
              class="action-btn"
              title="Sync channel"
              onclick={() => handleSyncChannel(channel.id)}
              disabled={syncingChannelId === channel.id}
            >
              <svg
                viewBox="0 0 24 24"
                fill="currentColor"
                width="20"
                height="20"
                class:spinning={syncingChannelId === channel.id}
              >
                <path
                  d="M12 4V1L8 5l4 4V6c3.31 0 6 2.69 6 6 0 1.01-.25 1.97-.7 2.8l1.46 1.46C19.54 15.03 20 13.57 20 12c0-4.42-3.58-8-8-8zm0 14c-3.31 0-6-2.69-6-6 0-1.01.25-1.97.7-2.8L5.24 7.74C4.46 8.97 4 10.43 4 12c0 4.42 3.58 8 8 8v3l4-4-4-4v3z"
                />
              </svg>
            </button>
            <a href="/feed?channel_id={channel.id}" class="action-btn" title="View videos">
              <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
                <path d="M4 6h16v2H4V6zm0 5h16v2H4v-2zm0 5h16v2H4v-2z" />
              </svg>
            </a>
            <button
              class="action-btn"
              title={channel.is_active ? 'Pause syncing' : 'Resume syncing'}
              onclick={() => handleToggleActive(channel)}
            >
              {#if channel.is_active}
                <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
                  <path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z" />
                </svg>
              {:else}
                <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
                  <path d="M8 5v14l11-7z" />
                </svg>
              {/if}
            </button>
            <button
              class="action-btn danger"
              title="Unsubscribe"
              onclick={() => (deleteConfirmId = channel.id)}
            >
              <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
                <path
                  d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"
                />
              </svg>
            </button>
          </div>
        </div>
      {/each}
    </div>
  {/if}
</div>

<!-- Add Channel Modal -->
{#if showAddModal}
  <div class="modal-overlay" onclick={closeAddModal} role="presentation">
    <div
      class="modal modal-lg"
      onclick={(e) => e.stopPropagation()}
      role="dialog"
      aria-labelledby="add-modal-title"
    >
      <header class="modal-header">
        <h2 id="add-modal-title">Add Channel</h2>
        <button class="close-btn" onclick={closeAddModal}>
          <svg viewBox="0 0 24 24" fill="currentColor" width="24" height="24">
            <path
              d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"
            />
          </svg>
        </button>
      </header>
      <div class="modal-body">
        <!-- Mode Tabs -->
        <div class="mode-tabs">
          <button
            class="mode-tab"
            class:active={addMode === 'search'}
            onclick={() => (addMode = 'search')}
          >
            Search
          </button>
          <button
            class="mode-tab"
            class:active={addMode === 'url'}
            onclick={() => (addMode = 'url')}
          >
            Paste URL
          </button>
        </div>

        {#if addMode === 'search'}
          <!-- Search Mode -->
          <div class="search-section">
            <div class="search-row">
              <select class="select platform-select" bind:value={searchPlatform} onchange={() => { searchResults = []; if (searchQuery.trim()) searchChannels(); }}>
                <option value="youtube">YouTube</option>
                <option value="rumble">Rumble</option>
                <option value="podcast">Podcast</option>
              </select>
              <div class="search-input-wrapper">
                <input
                  type="text"
                  class="input"
                  placeholder="Search for a channel..."
                  bind:value={searchQuery}
                  oninput={handleSearchInput}
                  onkeydown={(e) => e.key === 'Enter' && searchChannels()}
                />
                {#if searching}
                  <div class="search-spinner"></div>
                {/if}
              </div>
              <button class="btn btn-primary" onclick={searchChannels} disabled={!searchQuery.trim() || searching}>
                Search
              </button>
            </div>

            {#if searchError}
              <div class="error-inline">{searchError}</div>
            {/if}

            {#if searchResults.length > 0}
              <div class="search-results">
                {#each searchResults as result}
                  <div class="search-result-item">
                    <div class="result-avatar">
                      {#if result.avatar_url}
                        <img src={result.avatar_url} alt={result.name} />
                      {:else}
                        <div class="avatar-placeholder" style="background-color: {getPlatformColor(result.platform)}">
                          {getPlatformIcon(result.platform)}
                        </div>
                      {/if}
                    </div>
                    <div class="result-info">
                      <div class="result-name">{result.name}</div>
                      <div class="result-meta">
                        {#if result.subscriber_count}
                          <span>{formatSubscriberCount(result.subscriber_count)} subscribers</span>
                        {/if}
                        {#if result.video_count}
                          <span>{result.video_count} {result.platform === 'podcast' ? 'episodes' : 'videos'}</span>
                        {/if}
                      </div>
                    </div>
                    <button
                      class="btn btn-primary btn-sm"
                      onclick={() => handleAddFromSearch(result)}
                      disabled={adding}
                    >
                      {adding ? '...' : 'Add'}
                    </button>
                  </div>
                {/each}
              </div>
            {:else if searchQuery.trim() && !searching}
              <div class="no-results">
                <p>No channels found for "{searchQuery}"</p>
                <p class="hint">Try a different search term or switch platforms</p>
              </div>
            {/if}
          </div>
        {:else}
          <!-- URL Mode -->
          <div class="form-group">
            <label for="channel-url">Channel or Feed URL</label>
            <input
              id="channel-url"
              type="url"
              class="input"
              placeholder="YouTube, Rumble channel URL or Podcast RSS feed"
              bind:value={newChannelUrl}
              onkeydown={(e) => e.key === 'Enter' && handleAddChannel()}
            />
            <p class="form-hint">Supports YouTube, Rumble, and Podcast RSS feed URLs</p>
          </div>
        {/if}

        {#if addError}
          <div class="error-inline">{addError}</div>
        {/if}
      </div>
      <footer class="modal-footer">
        <button class="btn btn-secondary" onclick={closeAddModal}>Cancel</button>
        {#if addMode === 'url'}
          <button
            class="btn btn-primary"
            onclick={handleAddChannel}
            disabled={!newChannelUrl.trim() || adding}
          >
            {adding ? 'Adding...' : 'Add Channel'}
          </button>
        {/if}
      </footer>
    </div>
  </div>
{/if}

<!-- Import Modal -->
{#if showImportModal}
  <div class="modal-overlay" onclick={() => (showImportModal = false)} role="presentation">
    <div
      class="modal modal-lg"
      onclick={(e) => e.stopPropagation()}
      role="dialog"
      aria-labelledby="import-modal-title"
    >
      <header class="modal-header">
        <h2 id="import-modal-title">Import Channels</h2>
        <button class="close-btn" onclick={() => (showImportModal = false)}>
          <svg viewBox="0 0 24 24" fill="currentColor" width="24" height="24">
            <path
              d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"
            />
          </svg>
        </button>
      </header>
      <div class="modal-body">
        <div class="import-tabs">
          <!-- Import from Connected YouTube Account -->
          {#if loadingAccounts}
            <div class="import-section">
              <h3>From YouTube Account</h3>
              <p class="form-hint">Loading connected accounts...</p>
            </div>
          {:else if youtubeAccounts.length > 0}
            <div class="import-section">
              <h3>From YouTube Account</h3>
              <p class="form-hint">Import all subscriptions from your connected YouTube account</p>
              {#each youtubeAccounts as account}
                <div class="account-import-row">
                  <div class="account-info">
                    <span class="account-email">{account.account_email}</span>
                  </div>
                  <button
                    class="btn btn-primary"
                    onclick={() => handleImportFromAccount(account.id)}
                    disabled={importingFromAccount}
                  >
                    {importingFromAccount ? 'Importing...' : 'Import Subscriptions'}
                  </button>
                </div>
              {/each}
              {#if accountImportResult}
                <div class="import-result" class:success={accountImportResult.imported > 0}>
                  <p>
                    <strong>Import complete:</strong>
                    Found {accountImportResult.total_found} subscriptions.
                    {accountImportResult.imported} imported, {accountImportResult.skipped} already existed, {accountImportResult.failed} failed
                  </p>
                </div>
              {/if}
            </div>

            <div class="import-divider">
              <span>OR</span>
            </div>
          {:else}
            <div class="import-section">
              <h3>From YouTube Account</h3>
              <p class="form-hint">
                <a href="/settings">Link your YouTube account</a> to import subscriptions directly
              </p>
            </div>

            <div class="import-divider">
              <span>OR</span>
            </div>
          {/if}

          <div class="import-section">
            <h3>Paste Channel URLs</h3>
            <p class="form-hint">One URL per line (YouTube or Rumble channels)</p>
            <textarea
              class="input textarea"
              placeholder="https://www.youtube.com/@channel1&#10;https://rumble.com/c/channel2"
              bind:value={importUrls}
              rows="6"
            ></textarea>
            <button
              class="btn btn-primary"
              onclick={handleImportUrls}
              disabled={!importUrls.trim() || importing}
            >
              {importing ? 'Importing...' : 'Import URLs'}
            </button>
          </div>

          <div class="import-divider">
            <span>OR</span>
          </div>

          <div class="import-section">
            <h3>Google Takeout</h3>
            <p class="form-hint">
              Upload your YouTube subscriptions.json from <a
                href="https://takeout.google.com"
                target="_blank">Google Takeout</a
              >
            </p>
            <input
              type="file"
              accept=".json"
              class="file-input"
              onchange={(e) => (importFile = e.currentTarget.files)}
            />
            <button
              class="btn btn-primary"
              onclick={handleImportTakeout}
              disabled={!importFile?.length || importing}
            >
              {importing ? 'Importing...' : 'Import Takeout'}
            </button>
          </div>
        </div>

        {#if importResult}
          <div class="import-result" class:success={importResult.imported > 0}>
            <p>
              <strong>Import complete:</strong>
              {importResult.imported} imported, {importResult.skipped} skipped, {importResult.failed}
              failed
            </p>
            {#if importResult.errors.length > 0}
              <ul class="error-list">
                {#each importResult.errors as err}
                  <li>{err}</li>
                {/each}
              </ul>
            {/if}
          </div>
        {/if}
      </div>
      <footer class="modal-footer">
        <button class="btn btn-secondary" onclick={() => (showImportModal = false)}>Close</button>
      </footer>
    </div>
  </div>
{/if}

<!-- Delete Confirmation Modal -->
{#if deleteConfirmId !== null}
  {@const channelToDelete = channels.find((c) => c.id === deleteConfirmId)}
  <div class="modal-overlay" onclick={() => (deleteConfirmId = null)} role="presentation">
    <div
      class="modal modal-sm"
      onclick={(e) => e.stopPropagation()}
      role="dialog"
      aria-labelledby="delete-modal-title"
    >
      <header class="modal-header">
        <h2 id="delete-modal-title">Unsubscribe</h2>
      </header>
      <div class="modal-body">
        <p>
          Are you sure you want to unsubscribe from <strong>{channelToDelete?.name}</strong>? This
          will remove all synced videos from this channel.
        </p>
      </div>
      <footer class="modal-footer">
        <button class="btn btn-secondary" onclick={() => (deleteConfirmId = null)}>Cancel</button>
        <button
          class="btn btn-danger"
          onclick={() => deleteConfirmId && handleDelete(deleteConfirmId)}
          disabled={deleting}
        >
          {deleting ? 'Removing...' : 'Unsubscribe'}
        </button>
      </footer>
    </div>
  </div>
{/if}

<style>
  .subscriptions-page {
    max-width: 1000px;
    margin: 0 auto;
  }

  .page-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: var(--spacing-lg);
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

  .header-actions {
    display: flex;
    gap: var(--spacing-sm);
    flex-wrap: wrap;
  }

  .filters {
    display: flex;
    align-items: center;
    gap: var(--spacing-lg);
    margin-bottom: var(--spacing-lg);
    padding: var(--spacing-md);
    background: var(--color-surface);
    border-radius: var(--radius-md);
  }

  .filter-group {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
  }

  .filter-group label {
    font-weight: 500;
    color: var(--color-text-secondary);
  }

  .select {
    padding: var(--spacing-xs) var(--spacing-sm);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    background: var(--color-bg);
    color: var(--color-text);
  }

  .channel-count {
    margin-left: auto;
    color: var(--color-text-secondary);
    font-size: 0.9rem;
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
    padding: calc(var(--spacing-xl) * 2);
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

  .spinning {
    animation: spin 0.8s linear infinite;
  }

  .empty-state {
    text-align: center;
    padding: calc(var(--spacing-xl) * 2);
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
    margin-bottom: var(--spacing-lg);
  }

  .empty-actions {
    display: flex;
    gap: var(--spacing-md);
    justify-content: center;
    flex-wrap: wrap;
  }

  .channels-list {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-md);
  }

  .channel-card {
    display: flex;
    align-items: center;
    gap: var(--spacing-md);
    padding: var(--spacing-md);
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-lg);
    transition: box-shadow 0.2s;
  }

  .channel-card:hover {
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
  }

  .channel-card.inactive {
    opacity: 0.6;
  }

  .channel-avatar {
    width: 56px;
    height: 56px;
    border-radius: 50%;
    overflow: hidden;
    flex-shrink: 0;
  }

  .channel-avatar img {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }

  .avatar-placeholder {
    width: 100%;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    color: white;
    font-weight: bold;
    font-size: 1.25rem;
  }

  .channel-info {
    flex: 1;
    min-width: 0;
  }

  .channel-header {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    margin-bottom: var(--spacing-xs);
  }

  .channel-name {
    font-size: 1.1rem;
    font-weight: 600;
    margin: 0;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .platform-badge {
    font-size: 0.7rem;
    padding: 2px 6px;
    border-radius: var(--radius-sm);
    background: #85c742;
    color: white;
    text-transform: uppercase;
    font-weight: 600;
  }

  .platform-badge.youtube {
    background: #ff0000;
  }

  .platform-badge.podcast {
    background: #8B5CF6;
  }

  .channel-meta {
    font-size: 0.85rem;
    color: var(--color-text-secondary);
    margin-bottom: var(--spacing-xs);
  }

  .separator {
    margin: 0 var(--spacing-xs);
    opacity: 0.5;
  }

  .channel-sync {
    font-size: 0.8rem;
  }

  .sync-time {
    color: var(--color-text-secondary);
  }

  .sync-error {
    color: var(--color-error);
  }

  .channel-actions {
    display: flex;
    gap: var(--spacing-xs);
    flex-shrink: 0;
  }

  .action-btn {
    background: var(--color-bg);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    padding: var(--spacing-sm);
    cursor: pointer;
    color: var(--color-text-secondary);
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.2s;
    text-decoration: none;
  }

  .action-btn:hover {
    background: var(--color-surface);
    color: var(--color-text);
    border-color: var(--color-text-secondary);
  }

  .action-btn.danger:hover {
    background: var(--color-error);
    color: white;
    border-color: var(--color-error);
  }

  .action-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
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

  .modal-lg {
    max-width: 600px;
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
  }

  .form-hint {
    font-size: 0.85rem;
    color: var(--color-text-secondary);
    margin-top: var(--spacing-xs);
  }

  .form-hint a {
    color: var(--color-primary);
  }

  .input {
    width: 100%;
    padding: var(--spacing-sm) var(--spacing-md);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    background: var(--color-bg);
    color: var(--color-text);
    font-size: 1rem;
  }

  .input:focus {
    outline: none;
    border-color: var(--color-primary);
  }

  .textarea {
    resize: vertical;
    font-family: inherit;
  }

  .error-inline {
    background: #fef2f2;
    color: var(--color-error);
    padding: var(--spacing-sm);
    border-radius: var(--radius-sm);
    font-size: 0.9rem;
    margin-top: var(--spacing-sm);
  }

  .btn {
    padding: var(--spacing-sm) var(--spacing-md);
    border-radius: var(--radius-md);
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s;
  }

  .btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .btn-primary {
    background: var(--color-primary);
    color: white;
    border: none;
  }

  .btn-primary:hover:not(:disabled) {
    opacity: 0.9;
  }

  .btn-secondary {
    background: var(--color-bg);
    color: var(--color-text);
    border: 1px solid var(--color-border);
  }

  .btn-secondary:hover:not(:disabled) {
    background: var(--color-surface);
  }

  .btn-danger {
    background: var(--color-error);
    color: white;
    border: none;
  }

  .btn-danger:hover:not(:disabled) {
    opacity: 0.9;
  }

  /* Import modal specific styles */
  .import-tabs {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-lg);
  }

  .import-section {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-sm);
  }

  .import-section h3 {
    font-size: 1rem;
    margin: 0;
  }

  .import-divider {
    display: flex;
    align-items: center;
    gap: var(--spacing-md);
    color: var(--color-text-secondary);
  }

  .import-divider::before,
  .import-divider::after {
    content: '';
    flex: 1;
    border-top: 1px solid var(--color-border);
  }

  .file-input {
    padding: var(--spacing-sm);
    border: 1px dashed var(--color-border);
    border-radius: var(--radius-md);
    background: var(--color-bg);
  }

  .import-result {
    margin-top: var(--spacing-lg);
    padding: var(--spacing-md);
    background: #fef2f2;
    border-radius: var(--radius-md);
    color: var(--color-error);
  }

  .import-result.success {
    background: #f0fdf4;
    color: var(--color-success);
  }

  .error-list {
    margin: var(--spacing-sm) 0 0 var(--spacing-md);
    padding: 0;
    font-size: 0.85rem;
  }

  /* Channel Search Styles */
  .mode-tabs {
    display: flex;
    gap: var(--spacing-xs);
    margin-bottom: var(--spacing-lg);
    border-bottom: 1px solid var(--color-border);
  }

  .mode-tab {
    padding: var(--spacing-sm) var(--spacing-md);
    background: none;
    border: none;
    border-bottom: 2px solid transparent;
    cursor: pointer;
    font-weight: 500;
    color: var(--color-text-secondary);
    transition: all 0.2s;
  }

  .mode-tab:hover {
    color: var(--color-text);
  }

  .mode-tab.active {
    color: var(--color-primary);
    border-bottom-color: var(--color-primary);
  }

  .search-section {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-md);
  }

  .search-row {
    display: flex;
    gap: var(--spacing-sm);
    align-items: stretch;
  }

  .platform-select {
    width: 120px;
    flex-shrink: 0;
  }

  .search-input-wrapper {
    flex: 1;
    position: relative;
  }

  .search-input-wrapper .input {
    padding-right: 40px;
  }

  .search-spinner {
    position: absolute;
    right: 12px;
    top: 50%;
    transform: translateY(-50%);
    width: 20px;
    height: 20px;
    border: 2px solid var(--color-border);
    border-top-color: var(--color-primary);
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }

  .search-results {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-sm);
    max-height: 300px;
    overflow-y: auto;
  }

  .search-result-item {
    display: flex;
    align-items: center;
    gap: var(--spacing-md);
    padding: var(--spacing-sm);
    background: var(--color-bg);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    transition: border-color 0.2s;
  }

  .search-result-item:hover {
    border-color: var(--color-primary);
  }

  .result-avatar {
    width: 40px;
    height: 40px;
    border-radius: 50%;
    overflow: hidden;
    flex-shrink: 0;
  }

  .result-avatar img {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }

  .result-info {
    flex: 1;
    min-width: 0;
  }

  .result-name {
    font-weight: 500;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .result-meta {
    font-size: 0.8rem;
    color: var(--color-text-secondary);
    display: flex;
    gap: var(--spacing-sm);
  }

  .btn-sm {
    padding: var(--spacing-xs) var(--spacing-sm);
    font-size: 0.85rem;
  }

  .no-results {
    text-align: center;
    padding: var(--spacing-lg);
    color: var(--color-text-secondary);
  }

  .no-results p {
    margin: 0;
  }

  .no-results .hint {
    font-size: 0.85rem;
    margin-top: var(--spacing-xs);
  }

  /* Account Import Styles */
  .account-import-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--spacing-md);
    padding: var(--spacing-sm);
    background: var(--color-bg);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
  }

  .account-info {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
  }

  .account-email {
    font-weight: 500;
  }

  /* Mobile Styles */
  @media (max-width: 768px) {
    .page-header {
      display: none;
    }

    .filters {
      flex-wrap: wrap;
      gap: var(--spacing-sm);
    }

    .channel-count {
      width: 100%;
      text-align: right;
    }

    .channel-card {
      flex-direction: column;
      align-items: flex-start;
      gap: var(--spacing-sm);
    }

    .channel-avatar {
      width: 48px;
      height: 48px;
    }

    .channel-info {
      width: 100%;
    }

    .channel-actions {
      width: 100%;
      justify-content: flex-end;
      padding-top: var(--spacing-sm);
      border-top: 1px solid var(--color-border);
    }

    .action-btn {
      min-width: var(--touch-target-min);
      min-height: var(--touch-target-min);
    }

    .modal-overlay {
      padding: var(--spacing-sm);
      align-items: flex-end;
    }

    .modal {
      margin: 0;
      max-height: 85vh;
      border-radius: var(--radius-lg) var(--radius-lg) 0 0;
    }

    .input {
      min-height: var(--touch-target-min);
      font-size: 16px;
    }

    .modal-footer .btn {
      flex: 1;
      min-height: var(--touch-target-min);
    }

    .header-actions {
      width: 100%;
    }

    .header-actions .btn {
      flex: 1;
    }
  }
</style>
