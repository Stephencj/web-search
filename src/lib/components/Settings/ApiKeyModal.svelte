<script lang="ts">
  import { api, type ApiKey, type ApiKeyCreate } from '$lib/api/client';

  interface Props {
    isOpen: boolean;
    editingKey?: ApiKey | null;
    onClose: () => void;
    onSaved: () => void;
  }

  let { isOpen, editingKey = null, onClose, onSaved }: Props = $props();

  // Form state
  let provider = $state('');
  let apiKey = $state('');
  let extraConfig = $state('');
  let dailyLimit = $state<number | undefined>(undefined);
  let showApiKey = $state(false);
  let saving = $state(false);
  let error = $state<string | null>(null);

  // Provider options with descriptions
  const providers = [
    { id: 'google', name: 'Google Custom Search', hasExtraConfig: true, extraConfigLabel: 'Search Engine ID (cx)', extraConfigHelp: 'Your Custom Search Engine ID' },
    { id: 'bing', name: 'Bing Web Search', hasExtraConfig: false },
    { id: 'brave', name: 'Brave Search', hasExtraConfig: false },
    { id: 'duckduckgo', name: 'DuckDuckGo', hasExtraConfig: false },
  ];

  const isEditing = $derived(editingKey !== null);
  const selectedProvider = $derived(providers.find(p => p.id === provider));
  const modalTitle = $derived(isEditing ? `Edit ${selectedProvider?.name || 'API Key'}` : 'Add API Key');

  // Reset form when modal opens/closes
  $effect(() => {
    if (isOpen) {
      if (editingKey) {
        provider = editingKey.provider;
        apiKey = ''; // Don't prefill API key for security
        extraConfig = '';
        dailyLimit = editingKey.daily_limit ?? undefined;
      } else {
        provider = providers[0].id;
        apiKey = '';
        extraConfig = '';
        dailyLimit = undefined;
      }
      showApiKey = false;
      error = null;
    }
  });

  async function handleSubmit(e: Event) {
    e.preventDefault();

    if (!provider || !apiKey) {
      error = 'Provider and API Key are required';
      return;
    }

    saving = true;
    error = null;

    try {
      const data: ApiKeyCreate = {
        provider,
        api_key: apiKey,
        extra_config: extraConfig || null,
        daily_limit: dailyLimit || null,
      };

      await api.createApiKey(data);
      onSaved();
      onClose();
    } catch (err) {
      error = err instanceof Error ? err.message : 'Failed to save API key';
    } finally {
      saving = false;
    }
  }

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === 'Escape') {
      onClose();
    }
  }
</script>

<svelte:window onkeydown={handleKeydown} />

{#if isOpen}
  <div class="modal-overlay" onclick={onClose} role="button" tabindex="-1" aria-label="Close modal">
    <div
      class="modal"
      onclick={(e) => e.stopPropagation()}
      role="dialog"
      aria-modal="true"
      aria-labelledby="modal-title"
    >
      <div class="modal-header">
        <h2 id="modal-title">{modalTitle}</h2>
        <button class="close-btn" onclick={onClose} aria-label="Close">
          <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor">
            <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
          </svg>
        </button>
      </div>

      <form onsubmit={handleSubmit}>
        <div class="form-group">
          <label for="provider">Provider</label>
          <select
            id="provider"
            bind:value={provider}
            disabled={isEditing}
            class="input"
          >
            {#each providers as p}
              <option value={p.id}>{p.name}</option>
            {/each}
          </select>
        </div>

        <div class="form-group">
          <label for="api-key">API Key</label>
          <div class="input-with-toggle">
            {#if showApiKey}
              <input
                type="text"
                id="api-key"
                bind:value={apiKey}
                class="input"
                placeholder={isEditing ? 'Enter new API key to update' : 'Enter your API key'}
                autocomplete="off"
              />
            {:else}
              <input
                type="password"
                id="api-key"
                bind:value={apiKey}
                class="input"
                placeholder={isEditing ? 'Enter new API key to update' : 'Enter your API key'}
                autocomplete="off"
              />
            {/if}
            <button
              type="button"
              class="toggle-visibility"
              onclick={() => showApiKey = !showApiKey}
              aria-label={showApiKey ? 'Hide API key' : 'Show API key'}
            >
              {#if showApiKey}
                <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
                  <path d="M12 7c2.76 0 5 2.24 5 5 0 .65-.13 1.26-.36 1.83l2.92 2.92c1.51-1.26 2.7-2.89 3.43-4.75-1.73-4.39-6-7.5-11-7.5-1.4 0-2.74.25-3.98.7l2.16 2.16C10.74 7.13 11.35 7 12 7zM2 4.27l2.28 2.28.46.46C3.08 8.3 1.78 10.02 1 12c1.73 4.39 6 7.5 11 7.5 1.55 0 3.03-.3 4.38-.84l.42.42L19.73 22 21 20.73 3.27 3 2 4.27zM7.53 9.8l1.55 1.55c-.05.21-.08.43-.08.65 0 1.66 1.34 3 3 3 .22 0 .44-.03.65-.08l1.55 1.55c-.67.33-1.41.53-2.2.53-2.76 0-5-2.24-5-5 0-.79.2-1.53.53-2.2zm4.31-.78l3.15 3.15.02-.16c0-1.66-1.34-3-3-3l-.17.01z"/>
                </svg>
              {:else}
                <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
                  <path d="M12 4.5C7 4.5 2.73 7.61 1 12c1.73 4.39 6 7.5 11 7.5s9.27-3.11 11-7.5c-1.73-4.39-6-7.5-11-7.5zM12 17c-2.76 0-5-2.24-5-5s2.24-5 5-5 5 2.24 5 5-2.24 5-5 5zm0-8c-1.66 0-3 1.34-3 3s1.34 3 3 3 3-1.34 3-3-1.34-3-3-3z"/>
                </svg>
              {/if}
            </button>
          </div>
        </div>

        {#if selectedProvider?.hasExtraConfig}
          <div class="form-group">
            <label for="extra-config">{selectedProvider.extraConfigLabel}</label>
            <input
              type="text"
              id="extra-config"
              bind:value={extraConfig}
              class="input"
              placeholder={selectedProvider.extraConfigHelp}
            />
          </div>
        {/if}

        <div class="form-group">
          <label for="daily-limit">Daily Limit (optional)</label>
          <input
            type="number"
            id="daily-limit"
            bind:value={dailyLimit}
            class="input"
            min="1"
            placeholder="Unlimited"
          />
          <p class="help-text">Maximum API calls per day. Leave empty for unlimited.</p>
        </div>

        {#if error}
          <div class="error-message">{error}</div>
        {/if}

        <div class="modal-actions">
          <button type="button" class="btn btn-secondary" onclick={onClose} disabled={saving}>
            Cancel
          </button>
          <button type="submit" class="btn btn-primary" disabled={saving || !apiKey}>
            {#if saving}
              Saving...
            {:else if isEditing}
              Update Key
            {:else}
              Add Key
            {/if}
          </button>
        </div>
      </form>
    </div>
  </div>
{/if}

<style>
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
    background: var(--color-bg-secondary);
    border-radius: var(--radius-lg);
    width: 100%;
    max-width: 480px;
    max-height: 90vh;
    overflow-y: auto;
    box-shadow: var(--shadow-lg);
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
    font-weight: 600;
    margin: 0;
  }

  .close-btn {
    background: none;
    border: none;
    color: var(--color-text-secondary);
    cursor: pointer;
    padding: var(--spacing-xs);
    border-radius: var(--radius-sm);
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .close-btn:hover {
    background: var(--color-bg);
    color: var(--color-text);
  }

  form {
    padding: var(--spacing-lg);
  }

  .form-group {
    margin-bottom: var(--spacing-lg);
  }

  .form-group label {
    display: block;
    font-weight: 500;
    margin-bottom: var(--spacing-xs);
    color: var(--color-text);
  }

  .input {
    width: 100%;
    padding: var(--spacing-sm) var(--spacing-md);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    background: var(--color-bg);
    color: var(--color-text);
    font-size: 0.95rem;
  }

  .input:focus {
    outline: none;
    border-color: var(--color-primary);
  }

  .input:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  select.input {
    appearance: none;
    background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 12 12'%3E%3Cpath fill='%236c757d' d='M6 8L1 3h10z'/%3E%3C/svg%3E");
    background-repeat: no-repeat;
    background-position: right 12px center;
    padding-right: 36px;
  }

  .input-with-toggle {
    position: relative;
    display: flex;
  }

  .input-with-toggle .input {
    padding-right: 44px;
  }

  .toggle-visibility {
    position: absolute;
    right: 8px;
    top: 50%;
    transform: translateY(-50%);
    background: none;
    border: none;
    color: var(--color-text-secondary);
    cursor: pointer;
    padding: var(--spacing-xs);
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .toggle-visibility:hover {
    color: var(--color-text);
  }

  .help-text {
    font-size: 0.85rem;
    color: var(--color-text-secondary);
    margin-top: var(--spacing-xs);
  }

  .error-message {
    background: rgba(239, 68, 68, 0.1);
    border: 1px solid var(--color-error);
    color: var(--color-error);
    padding: var(--spacing-sm) var(--spacing-md);
    border-radius: var(--radius-md);
    margin-bottom: var(--spacing-lg);
    font-size: 0.9rem;
  }

  .modal-actions {
    display: flex;
    justify-content: flex-end;
    gap: var(--spacing-sm);
    padding-top: var(--spacing-md);
    border-top: 1px solid var(--color-border);
  }

  .btn {
    padding: var(--spacing-sm) var(--spacing-lg);
    border-radius: var(--radius-md);
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s ease;
  }

  .btn:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .btn-primary {
    background: var(--color-primary);
    color: white;
    border: none;
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
</style>
