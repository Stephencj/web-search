<script lang="ts">
  import { onMount } from 'svelte';
  import { page } from '$app/stores';
  import { api, type AppSettings, type CrawlerSettings, type ApiKey, type CrawlerSettingsUpdate } from '$lib/api/client';
  import { themeStore, type Theme } from '$lib/stores/theme.svelte';
  import { playbackPreferences } from '$lib/stores/playbackPreferences.svelte';
  import { ApiKeyModal, PlatformAccountCard } from '$lib/components/Settings';

  // Platform account types
  interface PlatformAccount {
    id: number;
    platform: string;
    account_email: string;
    account_name: string;
    is_active: boolean;
    is_premium: boolean;
    token_expires_at?: string;
    last_used_at?: string;
    last_error?: string;
    created_at: string;
  }

  interface OAuthConfigStatus {
    youtube: boolean;
  }

  // Page state
  let settings = $state<AppSettings | null>(null);
  let apiKeys = $state<ApiKey[]>([]);
  let platformAccounts = $state<PlatformAccount[]>([]);
  let oauthConfig = $state<OAuthConfigStatus>({ youtube: false });
  let loading = $state(true);
  let error = $state<string | null>(null);
  let saveMessage = $state<{ type: 'success' | 'error'; text: string } | null>(null);

  // Form state for crawler settings
  let editingCrawler = $state(false);
  let crawlerForm = $state<CrawlerSettingsUpdate>({});
  let savingCrawler = $state(false);

  // API Key Modal state
  let apiKeyModalOpen = $state(false);
  let editingApiKey = $state<ApiKey | null>(null);

  // Red Bar Radio auth state
  let redbarStatus = $state<{ logged_in: boolean; username?: string; is_premium?: boolean } | null>(null);
  let redbarLoading = $state(false);
  let redbarUsername = $state('');
  let redbarPassword = $state('');
  let redbarError = $state<string | null>(null);

  // Maintenance state
  let fixingMetadata = $state(false);
  let metadataFixMessage = $state<string | null>(null);

  // Theme options
  const themeOptions: { value: Theme; label: string; icon: string }[] = [
    { value: 'light', label: 'Light', icon: '☀️' },
    { value: 'dark', label: 'Dark', icon: '🌙' },
    { value: 'auto', label: 'Auto', icon: '🖥️' },
  ];

  // Provider info for display
  const providerInfo: Record<string, { name: string; description: string; requiresKey: boolean }> = {
    google: { name: 'Google Custom Search', description: 'Search the web using Google\'s Custom Search API', requiresKey: true },
    bing: { name: 'Bing Search', description: 'Search using Microsoft\'s Bing Search API', requiresKey: true },
    brave: { name: 'Brave Search', description: 'Independent search engine with privacy focus', requiresKey: true },
    duckduckgo: { name: 'DuckDuckGo', description: 'Privacy-focused search (uses instant answers API)', requiresKey: false },
  };

  onMount(async () => {
    await loadData();

    // Check for OAuth callback params
    const urlParams = new URLSearchParams(window.location.search);
    if (urlParams.has('oauth_success')) {
      const platform = urlParams.get('platform');
      const email = urlParams.get('email');
      saveMessage = { type: 'success', text: `Successfully linked ${platform} account: ${email}` };
      // Clean URL
      window.history.replaceState({}, '', '/settings');
      // Reload accounts
      await loadPlatformAccounts();
      setTimeout(() => saveMessage = null, 5000);
    } else if (urlParams.has('oauth_error')) {
      const errorMsg = urlParams.get('oauth_error');
      const platform = urlParams.get('platform');
      saveMessage = { type: 'error', text: `Failed to link ${platform} account: ${errorMsg}` };
      window.history.replaceState({}, '', '/settings');
      setTimeout(() => saveMessage = null, 5000);
    }
  });

  async function loadData() {
    loading = true;
    error = null;
    try {
      const [settingsData, keysData] = await Promise.all([
        api.getSettings(),
        api.listApiKeys(),
        loadPlatformAccounts(),
        loadOAuthConfig(),
        loadRedbarStatus(),
      ]);
      settings = settingsData;
      apiKeys = keysData;
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to load settings';
    } finally {
      loading = false;
    }
  }

  async function loadPlatformAccounts() {
    try {
      const response = await fetch('/api/accounts');
      if (response.ok) {
        platformAccounts = await response.json();
      }
    } catch {
      // Silently fail - accounts feature may not be configured
    }
  }

  async function loadOAuthConfig() {
    try {
      const response = await fetch('/api/accounts/config-status');
      if (response.ok) {
        oauthConfig = await response.json();
      }
    } catch {
      // Silently fail
    }
  }

  async function loadRedbarStatus() {
    try {
      redbarStatus = await api.getRedbarStatus();
    } catch {
      redbarStatus = { logged_in: false };
    }
  }

  async function handleRedbarLogin() {
    if (!redbarUsername || !redbarPassword) {
      redbarError = 'Please enter username and password';
      return;
    }

    redbarLoading = true;
    redbarError = null;

    try {
      const result = await api.redbarLogin(redbarUsername, redbarPassword);
      if (result.success) {
        saveMessage = { type: 'success', text: 'Successfully logged in to Red Bar Radio' };
        redbarUsername = '';
        redbarPassword = '';
        await loadRedbarStatus();
      } else {
        redbarError = result.message;
      }
    } catch (e) {
      redbarError = e instanceof Error ? e.message : 'Login failed';
    } finally {
      redbarLoading = false;
      setTimeout(() => saveMessage = null, 5000);
    }
  }

  async function handleRedbarLogout() {
    redbarLoading = true;
    try {
      await api.redbarLogout();
      redbarStatus = { logged_in: false };
      saveMessage = { type: 'success', text: 'Logged out of Red Bar Radio' };
    } catch (e) {
      redbarError = e instanceof Error ? e.message : 'Logout failed';
    } finally {
      redbarLoading = false;
      setTimeout(() => saveMessage = null, 5000);
    }
  }

  async function handleFixMetadata() {
    fixingMetadata = true;
    metadataFixMessage = 'Starting metadata fix...';
    try {
      const result = await api.fixFeedMetadata(200);
      metadataFixMessage = result.message + ' (running in background)';
      setTimeout(() => metadataFixMessage = null, 15000);
    } catch (e) {
      metadataFixMessage = 'Error: ' + (e instanceof Error ? e.message : 'Failed to fix metadata');
      setTimeout(() => metadataFixMessage = null, 8000);
    } finally {
      fixingMetadata = false;
    }
  }

  function getAccountForPlatform(platform: string): PlatformAccount | null {
    return platformAccounts.find(a => a.platform === platform) || null;
  }

  function startEditingCrawler() {
    if (!settings) return;
    // Initialize form with current values
    crawlerForm = {
      user_agent: settings.crawler.user_agent.value,
      concurrent_requests: settings.crawler.concurrent_requests.value,
      request_delay_ms: settings.crawler.request_delay_ms.value,
      timeout_seconds: settings.crawler.timeout_seconds.value,
      max_retries: settings.crawler.max_retries.value,
      respect_robots_txt: settings.crawler.respect_robots_txt.value,
      max_pages_per_source: settings.crawler.max_pages_per_source.value,
    };
    editingCrawler = true;
  }

  function cancelEditingCrawler() {
    editingCrawler = false;
    crawlerForm = {};
  }

  async function saveCrawlerSettings() {
    savingCrawler = true;
    saveMessage = null;

    try {
      // Only include changed values
      const updates: CrawlerSettingsUpdate = {};
      if (settings) {
        if (crawlerForm.user_agent !== settings.crawler.user_agent.value) {
          updates.user_agent = crawlerForm.user_agent;
        }
        if (crawlerForm.concurrent_requests !== settings.crawler.concurrent_requests.value) {
          updates.concurrent_requests = crawlerForm.concurrent_requests;
        }
        if (crawlerForm.request_delay_ms !== settings.crawler.request_delay_ms.value) {
          updates.request_delay_ms = crawlerForm.request_delay_ms;
        }
        if (crawlerForm.timeout_seconds !== settings.crawler.timeout_seconds.value) {
          updates.timeout_seconds = crawlerForm.timeout_seconds;
        }
        if (crawlerForm.max_retries !== settings.crawler.max_retries.value) {
          updates.max_retries = crawlerForm.max_retries;
        }
        if (crawlerForm.respect_robots_txt !== settings.crawler.respect_robots_txt.value) {
          updates.respect_robots_txt = crawlerForm.respect_robots_txt;
        }
        if (crawlerForm.max_pages_per_source !== settings.crawler.max_pages_per_source.value) {
          updates.max_pages_per_source = crawlerForm.max_pages_per_source;
        }
      }

      if (Object.keys(updates).length === 0) {
        saveMessage = { type: 'success', text: 'No changes to save' };
        editingCrawler = false;
        return;
      }

      const result = await api.updateCrawlerSettings(updates);
      if (settings) {
        settings = { ...settings, crawler: result.settings };
      }
      saveMessage = { type: 'success', text: result.message };
      editingCrawler = false;
    } catch (e) {
      saveMessage = { type: 'error', text: e instanceof Error ? e.message : 'Failed to save settings' };
    } finally {
      savingCrawler = false;
      // Clear message after 3 seconds
      setTimeout(() => saveMessage = null, 3000);
    }
  }

  async function resetCrawlerSetting(key: string) {
    try {
      const result = await api.resetCrawlerSetting(key);
      if (settings) {
        settings = { ...settings, crawler: result.settings };
      }
      saveMessage = { type: 'success', text: `Reset ${key} to default` };
    } catch (e) {
      saveMessage = { type: 'error', text: e instanceof Error ? e.message : 'Failed to reset setting' };
    }
    setTimeout(() => saveMessage = null, 3000);
  }

  function openApiKeyModal(key?: ApiKey) {
    editingApiKey = key || null;
    apiKeyModalOpen = true;
  }

  async function handleApiKeySaved() {
    apiKeys = await api.listApiKeys();
  }

  async function deleteApiKey(provider: string) {
    if (!confirm(`Delete API key for ${providerInfo[provider]?.name || provider}?`)) {
      return;
    }

    try {
      await api.deleteApiKey(provider);
      apiKeys = apiKeys.filter(k => k.provider !== provider);
      saveMessage = { type: 'success', text: 'API key deleted' };
    } catch (e) {
      saveMessage = { type: 'error', text: e instanceof Error ? e.message : 'Failed to delete API key' };
    }
    setTimeout(() => saveMessage = null, 3000);
  }

  function getSourceBadgeClass(source: 'env' | 'db' | 'default'): string {
    switch (source) {
      case 'env': return 'source-env';
      case 'db': return 'source-db';
      default: return 'source-default';
    }
  }

  function getSourceLabel(source: 'env' | 'db' | 'default'): string {
    switch (source) {
      case 'env': return 'ENV';
      case 'db': return 'Custom';
      default: return 'Default';
    }
  }

  function getApiKeyForProvider(provider: string): ApiKey | undefined {
    return apiKeys.find(k => k.provider === provider);
  }
</script>

<div class="settings-page">
  <header class="page-header">
    <h1>Settings</h1>
    <p class="subtitle">Configure your search engine preferences</p>
  </header>

  {#if saveMessage}
    <div class="save-message {saveMessage.type}">{saveMessage.text}</div>
  {/if}

  {#if error}
    <div class="error-message">{error}</div>
  {/if}

  {#if loading}
    <div class="loading">Loading settings...</div>
  {:else if settings}
    <div class="settings-sections">
      <!-- Appearance Settings -->
      <section class="settings-section card">
        <h2>Appearance</h2>
        <p class="section-description">Customize how WebSearch looks</p>

        <div class="setting-row">
          <div class="setting-info">
            <label>Theme</label>
            <p class="setting-help">Choose your preferred color scheme</p>
          </div>
          <div class="theme-toggle">
            {#each themeOptions as option}
              <button
                class="theme-btn"
                class:active={themeStore.current === option.value}
                onclick={() => themeStore.setTheme(option.value)}
              >
                <span class="theme-icon">{option.icon}</span>
                <span class="theme-label">{option.label}</span>
              </button>
            {/each}
          </div>
        </div>
      </section>

      <!-- Playback Settings -->
      <section class="settings-section card">
        <h2>Playback</h2>
        <p class="section-description">Configure video playback behavior</p>

        <div class="setting-row">
          <div class="setting-info">
            <label>Background Playback</label>
            <p class="setting-help">Continue playing videos when you switch tabs or turn off screen (uses native PiP for audio)</p>
          </div>
          <label class="toggle-switch">
            <input
              type="checkbox"
              checked={playbackPreferences.backgroundPlayback}
              onchange={() => playbackPreferences.toggleBackgroundPlayback()}
            />
            <span class="toggle-slider"></span>
          </label>
        </div>

        <div class="setting-row">
          <div class="setting-info">
            <label>Theater Mode</label>
            <p class="setting-help">Video fills the entire screen by default (press T to toggle)</p>
          </div>
          <label class="toggle-switch">
            <input
              type="checkbox"
              checked={playbackPreferences.theaterMode}
              onchange={() => playbackPreferences.toggleTheaterMode()}
            />
            <span class="toggle-slider"></span>
          </label>
        </div>
      </section>

      <!-- Linked Accounts -->
      <section class="settings-section card">
        <h2>Linked Accounts</h2>
        <p class="section-description">Connect your platform accounts for premium features</p>

        <div class="accounts-grid">
          <PlatformAccountCard
            platform="youtube"
            account={getAccountForPlatform('youtube')}
            isConfigured={oauthConfig.youtube}
            onAccountChange={loadPlatformAccounts}
          />
        </div>

        <!-- Red Bar Radio Login -->
        <div class="redbar-section">
          <div class="redbar-header">
            <div class="redbar-icon">
              <svg viewBox="0 0 24 24" fill="currentColor" width="24" height="24">
                <path d="M12 3v10.55c-.59-.34-1.27-.55-2-.55-2.21 0-4 1.79-4 4s1.79 4 4 4 4-1.79 4-4V7h4V3h-6z"/>
              </svg>
            </div>
            <div class="redbar-info">
              <h3>Red Bar Radio</h3>
              <p class="redbar-description">Access premium SCARS CLUB content</p>
            </div>
          </div>

          {#if redbarStatus?.logged_in}
            <div class="redbar-logged-in">
              <div class="redbar-user">
                <span class="redbar-username">{redbarStatus.username || 'Connected'}</span>
                {#if redbarStatus.is_premium}
                  <span class="premium-badge">SCARS CLUB</span>
                {/if}
              </div>
              <button
                class="btn btn-danger btn-sm"
                onclick={handleRedbarLogout}
                disabled={redbarLoading}
              >
                {redbarLoading ? 'Logging out...' : 'Logout'}
              </button>
            </div>
          {:else}
            <form class="redbar-login-form" onsubmit={(e) => { e.preventDefault(); handleRedbarLogin(); }}>
              <div class="form-row">
                <input
                  type="text"
                  class="input"
                  placeholder="Username"
                  bind:value={redbarUsername}
                  disabled={redbarLoading}
                />
                <input
                  type="password"
                  class="input"
                  placeholder="Password"
                  bind:value={redbarPassword}
                  disabled={redbarLoading}
                />
                <button
                  type="submit"
                  class="btn btn-primary"
                  disabled={redbarLoading || !redbarUsername || !redbarPassword}
                >
                  {redbarLoading ? 'Logging in...' : 'Login'}
                </button>
              </div>
              {#if redbarError}
                <p class="error-message">{redbarError}</p>
              {/if}
            </form>
          {/if}
        </div>
      </section>

      <!-- Crawler Settings -->
      <section class="settings-section card">
        <div class="section-header">
          <div>
            <h2>Crawler</h2>
            <p class="section-description">Configure how the crawler fetches web pages</p>
          </div>
          {#if !editingCrawler}
            <button class="btn btn-secondary" onclick={startEditingCrawler}>
              Edit
            </button>
          {/if}
        </div>

        <div class="settings-grid">
          <div class="setting-item">
            <div class="setting-label-row">
              <label for="user_agent">User Agent</label>
              <span class="source-badge {getSourceBadgeClass(settings.crawler.user_agent.source)}">
                {getSourceLabel(settings.crawler.user_agent.source)}
              </span>
            </div>
            {#if editingCrawler && settings.crawler.user_agent.editable}
              <input
                type="text"
                id="user_agent"
                class="input"
                bind:value={crawlerForm.user_agent}
              />
            {:else}
              <input
                type="text"
                class="input"
                value={settings.crawler.user_agent.value}
                disabled
              />
            {/if}
          </div>

          <div class="setting-item">
            <div class="setting-label-row">
              <label for="concurrent_requests">Concurrent Requests</label>
              <span class="source-badge {getSourceBadgeClass(settings.crawler.concurrent_requests.source)}">
                {getSourceLabel(settings.crawler.concurrent_requests.source)}
              </span>
            </div>
            {#if editingCrawler && settings.crawler.concurrent_requests.editable}
              <input
                type="number"
                id="concurrent_requests"
                class="input"
                bind:value={crawlerForm.concurrent_requests}
                min="1"
                max="50"
              />
            {:else}
              <input
                type="number"
                class="input"
                value={settings.crawler.concurrent_requests.value}
                disabled
              />
            {/if}
          </div>

          <div class="setting-item">
            <div class="setting-label-row">
              <label for="request_delay_ms">Request Delay (ms)</label>
              <span class="source-badge {getSourceBadgeClass(settings.crawler.request_delay_ms.source)}">
                {getSourceLabel(settings.crawler.request_delay_ms.source)}
              </span>
            </div>
            {#if editingCrawler && settings.crawler.request_delay_ms.editable}
              <input
                type="number"
                id="request_delay_ms"
                class="input"
                bind:value={crawlerForm.request_delay_ms}
                min="0"
                max="60000"
              />
            {:else}
              <input
                type="number"
                class="input"
                value={settings.crawler.request_delay_ms.value}
                disabled
              />
            {/if}
          </div>

          <div class="setting-item">
            <div class="setting-label-row">
              <label for="timeout_seconds">Timeout (seconds)</label>
              <span class="source-badge {getSourceBadgeClass(settings.crawler.timeout_seconds.source)}">
                {getSourceLabel(settings.crawler.timeout_seconds.source)}
              </span>
            </div>
            {#if editingCrawler && settings.crawler.timeout_seconds.editable}
              <input
                type="number"
                id="timeout_seconds"
                class="input"
                bind:value={crawlerForm.timeout_seconds}
                min="1"
                max="300"
              />
            {:else}
              <input
                type="number"
                class="input"
                value={settings.crawler.timeout_seconds.value}
                disabled
              />
            {/if}
          </div>

          <div class="setting-item">
            <div class="setting-label-row">
              <label for="max_retries">Max Retries</label>
              <span class="source-badge {getSourceBadgeClass(settings.crawler.max_retries.source)}">
                {getSourceLabel(settings.crawler.max_retries.source)}
              </span>
            </div>
            {#if editingCrawler && settings.crawler.max_retries.editable}
              <input
                type="number"
                id="max_retries"
                class="input"
                bind:value={crawlerForm.max_retries}
                min="0"
                max="10"
              />
            {:else}
              <input
                type="number"
                class="input"
                value={settings.crawler.max_retries.value}
                disabled
              />
            {/if}
          </div>

          <div class="setting-item">
            <div class="setting-label-row">
              <label for="max_pages_per_source">Max Pages per Source</label>
              <span class="source-badge {getSourceBadgeClass(settings.crawler.max_pages_per_source.source)}">
                {getSourceLabel(settings.crawler.max_pages_per_source.source)}
              </span>
            </div>
            {#if editingCrawler && settings.crawler.max_pages_per_source.editable}
              <input
                type="number"
                id="max_pages_per_source"
                class="input"
                bind:value={crawlerForm.max_pages_per_source}
                min="1"
                max="100000"
              />
            {:else}
              <input
                type="number"
                class="input"
                value={settings.crawler.max_pages_per_source.value}
                disabled
              />
            {/if}
          </div>

          <div class="setting-item">
            <div class="setting-label-row">
              <label>Respect robots.txt</label>
              <span class="source-badge {getSourceBadgeClass(settings.crawler.respect_robots_txt.source)}">
                {getSourceLabel(settings.crawler.respect_robots_txt.source)}
              </span>
            </div>
            {#if editingCrawler && settings.crawler.respect_robots_txt.editable}
              <label class="checkbox-label">
                <input
                  type="checkbox"
                  bind:checked={crawlerForm.respect_robots_txt}
                />
                <span>{crawlerForm.respect_robots_txt ? 'Yes' : 'No'}</span>
              </label>
            {:else}
              <span class="value-display">{settings.crawler.respect_robots_txt.value ? 'Yes' : 'No'}</span>
            {/if}
          </div>
        </div>

        {#if editingCrawler}
          <div class="edit-actions">
            <button class="btn btn-secondary" onclick={cancelEditingCrawler} disabled={savingCrawler}>
              Cancel
            </button>
            <button class="btn btn-primary" onclick={saveCrawlerSettings} disabled={savingCrawler}>
              {savingCrawler ? 'Saving...' : 'Save Changes'}
            </button>
          </div>
        {/if}
      </section>

      <!-- Meilisearch Settings -->
      <section class="settings-section card">
        <h2>Meilisearch</h2>
        <p class="section-description">Search engine connection settings (read-only)</p>

        <div class="settings-grid">
          <div class="setting-item">
            <label>Host</label>
            <input
              type="text"
              class="input"
              value={settings.meilisearch.host}
              disabled
            />
          </div>

          <div class="setting-item">
            <label>Index Prefix</label>
            <input
              type="text"
              class="input"
              value={settings.meilisearch.index_prefix}
              disabled
            />
          </div>
        </div>
      </section>

      <!-- API Keys -->
      <section class="settings-section card">
        <div class="section-header">
          <div>
            <h2>External API Keys</h2>
            <p class="section-description">Manage API keys for external search providers</p>
          </div>
          <button class="btn btn-primary" onclick={() => openApiKeyModal()}>
            Add API Key
          </button>
        </div>

        <div class="api-providers">
          {#each Object.entries(providerInfo) as [providerId, info]}
            {@const apiKey = getApiKeyForProvider(providerId)}
            <div class="provider-card">
              <div class="provider-header">
                <span class="provider-name">{info.name}</span>
                {#if !info.requiresKey}
                  <span class="provider-status available">No key required</span>
                {:else if apiKey}
                  <span class="provider-status configured">Configured</span>
                {:else}
                  <span class="provider-status unconfigured">Not configured</span>
                {/if}
              </div>
              <p class="provider-description">{info.description}</p>

              {#if apiKey}
                <div class="api-key-info">
                  <span class="masked-key">{apiKey.masked_key}</span>
                  {#if apiKey.daily_limit}
                    <span class="usage-info">
                      {apiKey.daily_usage} / {apiKey.daily_limit} today
                    </span>
                  {/if}
                </div>
                <div class="provider-actions">
                  <button class="btn btn-secondary btn-sm" onclick={() => openApiKeyModal(apiKey)}>
                    Update
                  </button>
                  <button class="btn btn-danger btn-sm" onclick={() => deleteApiKey(providerId)}>
                    Delete
                  </button>
                </div>
              {:else if info.requiresKey}
                <button class="btn btn-secondary" onclick={() => openApiKeyModal()}>
                  Add API Key
                </button>
              {/if}
            </div>
          {/each}
        </div>
      </section>

      <!-- Data Storage -->
      <section class="settings-section card">
        <h2>Data Storage</h2>
        <p class="section-description">Where your data is stored (read-only)</p>

        <div class="setting-item">
          <label>Data Directory</label>
          <input
            type="text"
            class="input"
            value={settings.data_dir}
            disabled
          />
        </div>
      </section>

      <!-- Maintenance -->
      <section class="settings-section card">
        <h2>Maintenance</h2>
        <p class="section-description">Tools to fix data issues</p>

        <div class="maintenance-item">
          <div class="maintenance-info">
            <h3>Fix Video Dates</h3>
            <p>Some videos may show incorrect upload dates (e.g., "Today" for old videos). This fetches accurate dates from YouTube.</p>
            {#if metadataFixMessage}
              <p class="metadata-fix-status">{metadataFixMessage}</p>
            {/if}
          </div>
          <button
            class="btn btn-secondary"
            onclick={handleFixMetadata}
            disabled={fixingMetadata}
          >
            {fixingMetadata ? 'Starting...' : 'Fix Dates'}
          </button>
        </div>
      </section>
    </div>
  {/if}
</div>

<!-- API Key Modal -->
<ApiKeyModal
  isOpen={apiKeyModalOpen}
  editingKey={editingApiKey}
  onClose={() => apiKeyModalOpen = false}
  onSaved={handleApiKeySaved}
/>

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

  .save-message {
    padding: var(--spacing-sm) var(--spacing-md);
    border-radius: var(--radius-md);
    margin-bottom: var(--spacing-lg);
    font-size: 0.9rem;
  }

  .save-message.success {
    background: rgba(16, 185, 129, 0.1);
    color: var(--color-success);
    border: 1px solid var(--color-success);
  }

  .save-message.error {
    background: rgba(239, 68, 68, 0.1);
    color: var(--color-error);
    border: 1px solid var(--color-error);
  }

  .error-message {
    background: rgba(239, 68, 68, 0.1);
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

  .section-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: var(--spacing-lg);
  }

  .settings-section h2 {
    font-size: 1.1rem;
    margin-bottom: var(--spacing-xs);
  }

  .section-description {
    color: var(--color-text-secondary);
    font-size: 0.9rem;
  }

  .section-header + .settings-grid,
  .section-header + .api-providers {
    margin-top: 0;
  }

  .settings-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: var(--spacing-md);
    margin-top: var(--spacing-lg);
  }

  .setting-item {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-xs);
  }

  .setting-label-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
  }

  .setting-item label {
    font-size: 0.85rem;
    font-weight: 500;
    color: var(--color-text-secondary);
  }

  .source-badge {
    font-size: 0.65rem;
    padding: 2px 6px;
    border-radius: var(--radius-sm);
    font-weight: 600;
    text-transform: uppercase;
  }

  .source-env {
    background: rgba(245, 158, 11, 0.15);
    color: var(--color-warning);
  }

  .source-db {
    background: rgba(67, 97, 238, 0.15);
    color: var(--color-primary);
  }

  .source-default {
    background: var(--color-bg);
    color: var(--color-text-secondary);
  }

  .value-display {
    padding: var(--spacing-sm) var(--spacing-md);
    background: var(--color-bg);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    color: var(--color-text);
  }

  .checkbox-label {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    cursor: pointer;
  }

  .checkbox-label input {
    width: 18px;
    height: 18px;
    cursor: pointer;
  }

  .edit-actions {
    display: flex;
    justify-content: flex-end;
    gap: var(--spacing-sm);
    margin-top: var(--spacing-lg);
    padding-top: var(--spacing-lg);
    border-top: 1px solid var(--color-border);
  }

  /* Theme Toggle */
  .setting-row {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: var(--spacing-lg);
  }

  .setting-info label {
    font-weight: 500;
    color: var(--color-text);
    display: block;
    margin-bottom: var(--spacing-xs);
  }

  .setting-help {
    font-size: 0.85rem;
    color: var(--color-text-secondary);
    margin: 0;
  }

  .theme-toggle {
    display: flex;
    gap: var(--spacing-xs);
    background: var(--color-bg);
    padding: var(--spacing-xs);
    border-radius: var(--radius-md);
    border: 1px solid var(--color-border);
  }

  .theme-btn {
    display: flex;
    align-items: center;
    gap: var(--spacing-xs);
    padding: var(--spacing-sm) var(--spacing-md);
    border: none;
    background: transparent;
    border-radius: var(--radius-sm);
    cursor: pointer;
    color: var(--color-text-secondary);
    transition: all 0.2s ease;
  }

  .theme-btn:hover {
    background: var(--color-bg-secondary);
    color: var(--color-text);
  }

  .theme-btn.active {
    background: var(--color-primary);
    color: white;
  }

  .theme-icon {
    font-size: 1rem;
  }

  .theme-label {
    font-size: 0.85rem;
    font-weight: 500;
  }

  /* Toggle Switch */
  .toggle-switch {
    position: relative;
    display: inline-block;
    width: 52px;
    height: 28px;
    flex-shrink: 0;
  }

  .toggle-switch input {
    opacity: 0;
    width: 0;
    height: 0;
  }

  .toggle-slider {
    position: absolute;
    cursor: pointer;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background-color: var(--color-border);
    transition: 0.3s;
    border-radius: 28px;
  }

  .toggle-slider::before {
    position: absolute;
    content: '';
    height: 20px;
    width: 20px;
    left: 4px;
    bottom: 4px;
    background-color: white;
    transition: 0.3s;
    border-radius: 50%;
  }

  .toggle-switch input:checked + .toggle-slider {
    background-color: var(--color-primary);
  }

  .toggle-switch input:checked + .toggle-slider::before {
    transform: translateX(24px);
  }

  .toggle-switch input:focus + .toggle-slider {
    box-shadow: 0 0 0 2px rgba(99, 102, 241, 0.3);
  }

  /* Linked Accounts */
  .accounts-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    gap: var(--spacing-md);
    margin-top: var(--spacing-lg);
  }

  /* Red Bar Radio Section */
  .redbar-section {
    margin-top: var(--spacing-lg);
    padding: var(--spacing-md);
    background: var(--color-bg);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
  }

  .redbar-header {
    display: flex;
    align-items: center;
    gap: var(--spacing-md);
    margin-bottom: var(--spacing-md);
  }

  .redbar-icon {
    width: 48px;
    height: 48px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: linear-gradient(135deg, #FF0000 0%, #CC0000 100%);
    border-radius: var(--radius-md);
    color: white;
  }

  .redbar-info h3 {
    margin: 0;
    font-size: 1rem;
    font-weight: 600;
  }

  .redbar-description {
    margin: 0;
    font-size: 0.875rem;
    color: var(--color-text-muted);
  }

  .redbar-logged-in {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: var(--spacing-sm) var(--spacing-md);
    background: rgba(34, 197, 94, 0.1);
    border: 1px solid rgba(34, 197, 94, 0.3);
    border-radius: var(--radius-md);
  }

  .redbar-user {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
  }

  .redbar-username {
    font-weight: 500;
    color: rgb(34, 197, 94);
  }

  .premium-badge {
    background: linear-gradient(135deg, #FFD700 0%, #FFA500 100%);
    color: black;
    padding: 2px 8px;
    border-radius: var(--radius-sm);
    font-size: 0.7rem;
    font-weight: 700;
  }

  .redbar-login-form {
    margin-top: var(--spacing-sm);
  }

  .redbar-login-form .form-row {
    display: flex;
    gap: var(--spacing-sm);
    flex-wrap: wrap;
  }

  .redbar-login-form .input {
    flex: 1;
    min-width: 120px;
  }

  .redbar-login-form .btn {
    white-space: nowrap;
  }

  .redbar-login-form .error-message {
    margin-top: var(--spacing-sm);
    color: var(--color-error);
    font-size: 0.875rem;
  }

  .btn-danger {
    background: var(--color-error);
    color: white;
    border: none;
  }

  .btn-danger:hover:not(:disabled) {
    background: #dc2626;
  }

  .btn-sm {
    padding: var(--spacing-xs) var(--spacing-sm);
    font-size: 0.875rem;
  }

  /* API Providers */
  .api-providers {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: var(--spacing-md);
    margin-top: var(--spacing-lg);
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
    font-weight: 500;
  }

  .provider-status.unconfigured {
    background: rgba(239, 68, 68, 0.1);
    color: var(--color-error);
  }

  .provider-status.configured {
    background: rgba(16, 185, 129, 0.1);
    color: var(--color-success);
  }

  .provider-status.available {
    background: rgba(67, 97, 238, 0.1);
    color: var(--color-primary);
  }

  .provider-description {
    font-size: 0.85rem;
    color: var(--color-text-secondary);
    margin-bottom: var(--spacing-sm);
  }

  .api-key-info {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: var(--spacing-sm);
    background: var(--color-bg-secondary);
    border-radius: var(--radius-sm);
    margin-bottom: var(--spacing-sm);
    font-size: 0.85rem;
  }

  .masked-key {
    font-family: var(--font-mono);
    color: var(--color-text-secondary);
  }

  .usage-info {
    color: var(--color-text-secondary);
  }

  .provider-actions {
    display: flex;
    gap: var(--spacing-sm);
  }

  .btn {
    padding: var(--spacing-sm) var(--spacing-md);
    border-radius: var(--radius-md);
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s ease;
    border: none;
  }

  .btn:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .btn-sm {
    padding: var(--spacing-xs) var(--spacing-sm);
    font-size: 0.85rem;
  }

  .btn-primary {
    background: var(--color-primary);
    color: white;
  }

  .btn-primary:hover:not(:disabled) {
    background: var(--color-primary-hover);
  }

  .btn-secondary {
    background: var(--color-bg);
    color: var(--color-text);
    border: 1px solid var(--color-border);
  }

  .btn-secondary:hover:not(:disabled) {
    background: var(--color-border);
  }

  .btn-danger {
    background: var(--color-error);
    color: white;
  }

  .btn-danger:hover:not(:disabled) {
    opacity: 0.9;
  }

  /* Maintenance */
  .maintenance-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    gap: var(--spacing-lg);
    padding: var(--spacing-md);
    background: var(--color-bg);
    border-radius: var(--radius-md);
  }

  .maintenance-info h3 {
    margin: 0 0 var(--spacing-xs) 0;
    font-size: 0.95rem;
    font-weight: 600;
  }

  .maintenance-info p {
    margin: 0;
    font-size: 0.85rem;
    color: var(--color-text-secondary);
  }

  .metadata-fix-status {
    margin-top: var(--spacing-sm) !important;
    padding: var(--spacing-xs) var(--spacing-sm);
    background: rgba(67, 97, 238, 0.1);
    border-radius: var(--radius-sm);
    color: var(--color-primary) !important;
    font-weight: 500;
  }

  /* Mobile */
  @media (max-width: 768px) {
    .settings-page {
      max-width: 100%;
    }

    .setting-row {
      flex-direction: column;
      align-items: flex-start;
    }

    .theme-toggle {
      width: 100%;
      justify-content: center;
    }

    .section-header {
      flex-direction: column;
      gap: var(--spacing-md);
    }

    .section-header .btn {
      align-self: flex-start;
    }

    .accounts-grid {
      grid-template-columns: 1fr;
    }

    .api-providers {
      grid-template-columns: 1fr;
    }

    .settings-grid {
      grid-template-columns: 1fr;
    }

    .redbar-section {
      padding: var(--spacing-sm);
    }

    .redbar-header {
      flex-direction: column;
      text-align: center;
    }

    .redbar-logged-in {
      flex-direction: column;
      gap: var(--spacing-sm);
      text-align: center;
    }

    .redbar-login-form .form-row {
      flex-direction: column;
    }

    .redbar-login-form .input {
      min-width: 100%;
    }

    .maintenance-item {
      flex-direction: column;
      text-align: center;
    }
  }
</style>
