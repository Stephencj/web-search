<script lang="ts">
  import { api } from '$lib/api/client';

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

  interface Props {
    platform: 'youtube' | 'rumble';
    account?: PlatformAccount | null;
    isConfigured: boolean;
    onAccountChange: () => void;
  }

  let { platform, account = null, isConfigured, onAccountChange }: Props = $props();

  let linking = $state(false);
  let unlinking = $state(false);
  let error = $state<string | null>(null);

  // Platform display info
  const platformInfo = {
    youtube: {
      name: 'YouTube',
      icon: `<svg viewBox="0 0 24 24" width="24" height="24" fill="#FF0000"><path d="M21.543 6.498C22 8.28 22 12 22 12s0 3.72-.457 5.502c-.254.985-.997 1.76-1.938 2.022C17.896 20 12 20 12 20s-5.893 0-7.605-.476c-.945-.266-1.687-1.04-1.938-2.022C2 15.72 2 12 2 12s0-3.72.457-5.502c.254-.985.997-1.76 1.938-2.022C6.107 4 12 4 12 4s5.896 0 7.605.476c.945.266 1.687 1.04 1.938 2.022zM10 15.5l6-3.5-6-3.5v7z"/></svg>`,
      color: '#FF0000',
      benefits: ['Ad-free playback', 'Background play', 'Higher quality streams', 'Members-only content'],
    },
    rumble: {
      name: 'Rumble',
      icon: `<svg viewBox="0 0 24 24" width="24" height="24" fill="#85c742"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 14.5v-9l6 4.5-6 4.5z"/></svg>`,
      color: '#85c742',
      benefits: ['Premium content access', 'Higher quality streams'],
    },
  };

  const info = $derived(platformInfo[platform]);
  const isLinked = $derived(!!account && account.is_active);

  async function handleLink() {
    if (!isConfigured) {
      error = `OAuth not configured for ${info.name}. Please set the environment variables.`;
      return;
    }

    linking = true;
    error = null;

    try {
      const response = await fetch(`/api/accounts/auth/${platform}`);
      const data = await response.json();

      if (!response.ok) {
        throw new Error(data.detail || 'Failed to get authorization URL');
      }

      // Open OAuth popup
      const width = 600;
      const height = 700;
      const left = window.screenX + (window.outerWidth - width) / 2;
      const top = window.screenY + (window.outerHeight - height) / 2;

      const popup = window.open(
        data.url,
        'oauth_popup',
        `width=${width},height=${height},left=${left},top=${top},scrollbars=yes`
      );

      // Poll for popup close and URL changes
      const checkPopup = setInterval(() => {
        try {
          if (popup?.closed) {
            clearInterval(checkPopup);
            linking = false;
            // Check if account was linked
            onAccountChange();
          }
        } catch {
          // Cross-origin access denied - popup still open
        }
      }, 500);

    } catch (err) {
      error = err instanceof Error ? err.message : 'Failed to start OAuth flow';
      linking = false;
    }
  }

  async function handleUnlink() {
    if (!account) return;

    if (!confirm(`Are you sure you want to unlink your ${info.name} account (${account.account_email})?`)) {
      return;
    }

    unlinking = true;
    error = null;

    try {
      const response = await fetch(`/api/accounts/${account.id}`, {
        method: 'DELETE',
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Failed to unlink account');
      }

      onAccountChange();
    } catch (err) {
      error = err instanceof Error ? err.message : 'Failed to unlink account';
    } finally {
      unlinking = false;
    }
  }

  function formatDate(dateStr: string): string {
    return new Date(dateStr).toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  }
</script>

<div class="account-card" class:linked={isLinked}>
  <div class="card-header">
    <div class="platform-info">
      <span class="platform-icon">{@html info.icon}</span>
      <span class="platform-name">{info.name}</span>
      {#if isLinked && account?.is_premium}
        <span class="premium-badge">Premium</span>
      {/if}
    </div>
    <div class="status-indicator" class:active={isLinked} class:inactive={!isLinked}>
      {isLinked ? 'Linked' : 'Not Linked'}
    </div>
  </div>

  {#if isLinked && account}
    <div class="account-info">
      <div class="account-details">
        <span class="account-name">{account.account_name}</span>
        <span class="account-email">{account.account_email}</span>
      </div>
      <div class="account-meta">
        <span>Linked {formatDate(account.created_at)}</span>
        {#if account.last_error}
          <span class="error-indicator" title={account.last_error}>
            <svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor">
              <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/>
            </svg>
            Error
          </span>
        {/if}
      </div>
    </div>

    <div class="card-actions">
      <button class="btn btn-danger" onclick={handleUnlink} disabled={unlinking}>
        {unlinking ? 'Unlinking...' : 'Unlink Account'}
      </button>
    </div>
  {:else}
    <div class="benefits">
      <p class="benefits-title">Link your account to unlock:</p>
      <ul>
        {#each info.benefits as benefit}
          <li>
            <svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor">
              <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/>
            </svg>
            {benefit}
          </li>
        {/each}
      </ul>
    </div>

    {#if !isConfigured}
      <div class="config-warning">
        <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
          <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/>
        </svg>
        <span>OAuth not configured. Set environment variables to enable.</span>
      </div>
    {/if}

    <div class="card-actions">
      <button class="btn btn-primary" onclick={handleLink} disabled={linking || !isConfigured}>
        {#if linking}
          <span class="spinner"></span>
          Linking...
        {:else}
          <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
            <path d="M10 6L8.59 7.41 13.17 12l-4.58 4.59L10 18l6-6z"/>
          </svg>
          Link {info.name} Account
        {/if}
      </button>
    </div>
  {/if}

  {#if error}
    <div class="error-message">{error}</div>
  {/if}
</div>

<style>
  .account-card {
    background: var(--color-bg-secondary);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-lg);
    padding: var(--spacing-lg);
    transition: border-color 0.2s ease;
  }

  .account-card.linked {
    border-color: var(--color-success);
  }

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: var(--spacing-md);
  }

  .platform-info {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
  }

  .platform-icon {
    display: flex;
    align-items: center;
    justify-content: center;
  }

  .platform-name {
    font-weight: 600;
    font-size: 1.1rem;
  }

  .premium-badge {
    background: linear-gradient(135deg, #ffd700, #ffb700);
    color: #000;
    font-size: 0.7rem;
    font-weight: 600;
    padding: 2px 8px;
    border-radius: 12px;
    text-transform: uppercase;
  }

  .status-indicator {
    font-size: 0.85rem;
    font-weight: 500;
    padding: 4px 12px;
    border-radius: var(--radius-full);
  }

  .status-indicator.active {
    background: rgba(34, 197, 94, 0.1);
    color: var(--color-success);
  }

  .status-indicator.inactive {
    background: var(--color-bg);
    color: var(--color-text-secondary);
  }

  .account-info {
    background: var(--color-bg);
    border-radius: var(--radius-md);
    padding: var(--spacing-md);
    margin-bottom: var(--spacing-md);
  }

  .account-details {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  .account-name {
    font-weight: 500;
    color: var(--color-text);
  }

  .account-email {
    font-size: 0.9rem;
    color: var(--color-text-secondary);
  }

  .account-meta {
    display: flex;
    align-items: center;
    gap: var(--spacing-md);
    margin-top: var(--spacing-sm);
    font-size: 0.8rem;
    color: var(--color-text-tertiary);
  }

  .error-indicator {
    display: flex;
    align-items: center;
    gap: 4px;
    color: var(--color-error);
  }

  .benefits {
    margin-bottom: var(--spacing-md);
  }

  .benefits-title {
    font-size: 0.9rem;
    color: var(--color-text-secondary);
    margin-bottom: var(--spacing-sm);
  }

  .benefits ul {
    list-style: none;
    padding: 0;
    margin: 0;
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    gap: var(--spacing-xs);
  }

  .benefits li {
    display: flex;
    align-items: center;
    gap: var(--spacing-xs);
    font-size: 0.9rem;
    color: var(--color-text);
  }

  .benefits li svg {
    color: var(--color-success);
    flex-shrink: 0;
  }

  .config-warning {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    background: rgba(234, 179, 8, 0.1);
    border: 1px solid rgba(234, 179, 8, 0.3);
    color: #eab308;
    padding: var(--spacing-sm) var(--spacing-md);
    border-radius: var(--radius-md);
    font-size: 0.85rem;
    margin-bottom: var(--spacing-md);
  }

  .card-actions {
    display: flex;
    justify-content: flex-end;
    gap: var(--spacing-sm);
  }

  .btn {
    display: flex;
    align-items: center;
    gap: var(--spacing-xs);
    padding: var(--spacing-sm) var(--spacing-lg);
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

  .btn-primary {
    background: var(--color-primary);
    color: white;
  }

  .btn-primary:hover:not(:disabled) {
    background: var(--color-primary-hover);
  }

  .btn-danger {
    background: rgba(239, 68, 68, 0.1);
    color: var(--color-error);
    border: 1px solid var(--color-error);
  }

  .btn-danger:hover:not(:disabled) {
    background: var(--color-error);
    color: white;
  }

  .spinner {
    width: 16px;
    height: 16px;
    border: 2px solid rgba(255, 255, 255, 0.3);
    border-top-color: white;
    border-radius: 50%;
    animation: spin 0.8s linear infinite;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  .error-message {
    margin-top: var(--spacing-md);
    background: rgba(239, 68, 68, 0.1);
    border: 1px solid var(--color-error);
    color: var(--color-error);
    padding: var(--spacing-sm) var(--spacing-md);
    border-radius: var(--radius-md);
    font-size: 0.9rem;
  }
</style>
