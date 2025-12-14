<script lang="ts">
  import { onMount } from 'svelte';
  import { goto } from '$app/navigation';
  import { auth, type User } from '$lib/stores/auth.svelte';

  interface UserPublic {
    id: number;
    username: string;
    display_name: string;
    avatar_color: string;
    has_pin: boolean;
  }

  let users = $state<UserPublic[]>([]);
  let loading = $state(true);
  let error = $state<string | null>(null);
  let authMode = $state<'open' | 'protected'>('open');

  // Login state
  let selectedUser = $state<UserPublic | null>(null);
  let pinInput = $state('');
  let loginError = $state<string | null>(null);
  let loggingIn = $state(false);

  onMount(async () => {
    await loadUsers();

    // If already authenticated in protected mode, redirect
    if (auth.isAuthenticated) {
      goto('/');
    }
  });

  async function loadUsers() {
    loading = true;
    error = null;
    try {
      const response = await fetch('/api/auth/users');
      if (response.ok) {
        const data = await response.json();
        users = data.users;
        authMode = data.auth_mode;
      } else {
        error = 'Failed to load users';
      }
    } catch (e) {
      error = 'Network error';
    } finally {
      loading = false;
    }
  }

  function selectUser(user: UserPublic) {
    selectedUser = user;
    pinInput = '';
    loginError = null;
  }

  function clearSelection() {
    selectedUser = null;
    pinInput = '';
    loginError = null;
  }

  async function handleLogin() {
    if (!selectedUser) return;

    loggingIn = true;
    loginError = null;

    const result = await auth.login(
      selectedUser.username,
      selectedUser.has_pin ? pinInput : undefined
    );

    if (result.success) {
      goto('/');
    } else {
      loginError = result.message || 'Login failed';
      pinInput = '';
    }

    loggingIn = false;
  }

  async function continueAsGuest() {
    // In open mode without users, just proceed
    goto('/');
  }

  function handlePinInput(e: KeyboardEvent) {
    if (e.key === 'Enter') {
      handleLogin();
    }
  }

  function getInitials(name: string): string {
    const parts = name.split(' ');
    if (parts.length >= 2) {
      return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
    }
    return name.slice(0, 2).toUpperCase();
  }
</script>

<div class="login-page">
  <div class="login-container">
    <header class="login-header">
      <h1>Welcome</h1>
      <p class="subtitle">Select your profile to continue</p>
    </header>

    {#if loading}
      <div class="loading">
        <div class="spinner"></div>
        <span>Loading...</span>
      </div>
    {:else if error}
      <div class="error-message">{error}</div>
    {:else if selectedUser}
      <!-- PIN Entry View -->
      <div class="pin-entry">
        <button class="back-btn" onclick={clearSelection}>
          <svg viewBox="0 0 24 24" fill="currentColor" width="24" height="24">
            <path d="M20 11H7.83l5.59-5.59L12 4l-8 8 8 8 1.41-1.41L7.83 13H20v-2z"/>
          </svg>
          Back
        </button>

        <div class="selected-avatar" style="background-color: {selectedUser.avatar_color}">
          {getInitials(selectedUser.display_name)}
        </div>
        <h2>{selectedUser.display_name}</h2>

        {#if selectedUser.has_pin}
          <div class="pin-form">
            <label for="pin-input">Enter PIN</label>
            <input
              id="pin-input"
              type="password"
              inputmode="numeric"
              maxlength="20"
              bind:value={pinInput}
              onkeydown={handlePinInput}
              placeholder="****"
              disabled={loggingIn}
              autofocus
            />
            {#if loginError}
              <p class="login-error">{loginError}</p>
            {/if}
            <button
              class="login-btn"
              onclick={handleLogin}
              disabled={loggingIn || !pinInput}
            >
              {loggingIn ? 'Logging in...' : 'Continue'}
            </button>
          </div>
        {:else}
          <button
            class="login-btn"
            onclick={handleLogin}
            disabled={loggingIn}
          >
            {loggingIn ? 'Logging in...' : 'Continue'}
          </button>
          {#if loginError}
            <p class="login-error">{loginError}</p>
          {/if}
        {/if}
      </div>
    {:else}
      <!-- User Selection Grid -->
      <div class="users-grid">
        {#each users as user}
          <button class="user-card" onclick={() => selectUser(user)}>
            <div class="user-avatar" style="background-color: {user.avatar_color}">
              {getInitials(user.display_name)}
            </div>
            <span class="user-name">{user.display_name}</span>
            {#if user.has_pin}
              <span class="pin-indicator">
                <svg viewBox="0 0 24 24" fill="currentColor" width="14" height="14">
                  <path d="M18 8h-1V6c0-2.76-2.24-5-5-5S7 3.24 7 6v2H6c-1.1 0-2 .9-2 2v10c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V10c0-1.1-.9-2-2-2zm-6 9c-1.1 0-2-.9-2-2s.9-2 2-2 2 .9 2 2-.9 2-2 2zm3.1-9H8.9V6c0-1.71 1.39-3.1 3.1-3.1 1.71 0 3.1 1.39 3.1 3.1v2z"/>
                </svg>
              </span>
            {/if}
          </button>
        {/each}

        {#if users.length === 0}
          <div class="no-users">
            <p>No users yet</p>
            <a href="/settings/users" class="create-user-link">Create a user</a>
          </div>
        {/if}
      </div>

      {#if authMode === 'open'}
        <div class="guest-option">
          <button class="guest-btn" onclick={continueAsGuest}>
            Continue without signing in
          </button>
        </div>
      {/if}
    {/if}
  </div>
</div>

<style>
  .login-page {
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: var(--spacing-xl);
    background: var(--color-bg);
  }

  .login-container {
    width: 100%;
    max-width: 600px;
    text-align: center;
  }

  .login-header {
    margin-bottom: var(--spacing-xxl);
  }

  .login-header h1 {
    font-size: 2.5rem;
    margin: 0 0 var(--spacing-sm) 0;
  }

  .subtitle {
    color: var(--color-text-secondary);
    margin: 0;
    font-size: 1.1rem;
  }

  .loading {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: var(--spacing-md);
    padding: var(--spacing-xxl);
    color: var(--color-text-secondary);
  }

  .spinner {
    width: 40px;
    height: 40px;
    border: 3px solid var(--color-border);
    border-top-color: var(--color-primary);
    border-radius: 50%;
    animation: spin 1s linear infinite;
  }

  @keyframes spin {
    to { transform: rotate(360deg); }
  }

  .error-message {
    padding: var(--spacing-lg);
    background: rgba(239, 68, 68, 0.1);
    color: var(--color-error);
    border-radius: var(--radius-md);
  }

  /* User Grid */
  .users-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
    gap: var(--spacing-lg);
    margin-bottom: var(--spacing-xl);
  }

  .user-card {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: var(--spacing-sm);
    padding: var(--spacing-lg);
    background: var(--color-bg-secondary);
    border: 2px solid transparent;
    border-radius: var(--radius-lg);
    cursor: pointer;
    transition: all 0.2s ease;
    position: relative;
  }

  .user-card:hover {
    border-color: var(--color-primary);
    transform: translateY(-2px);
  }

  .user-avatar {
    width: 80px;
    height: 80px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.8rem;
    font-weight: 600;
    color: white;
    text-transform: uppercase;
  }

  .user-name {
    font-weight: 500;
    color: var(--color-text);
    font-size: 1rem;
  }

  .pin-indicator {
    position: absolute;
    top: var(--spacing-sm);
    right: var(--spacing-sm);
    color: var(--color-text-secondary);
  }

  .no-users {
    grid-column: 1 / -1;
    padding: var(--spacing-xxl);
    color: var(--color-text-secondary);
  }

  .create-user-link {
    display: inline-block;
    margin-top: var(--spacing-md);
    color: var(--color-primary);
    text-decoration: none;
  }

  .create-user-link:hover {
    text-decoration: underline;
  }

  /* PIN Entry */
  .pin-entry {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: var(--spacing-lg);
  }

  .back-btn {
    display: flex;
    align-items: center;
    gap: var(--spacing-xs);
    background: none;
    border: none;
    color: var(--color-text-secondary);
    cursor: pointer;
    padding: var(--spacing-sm);
    font-size: 0.9rem;
    align-self: flex-start;
  }

  .back-btn:hover {
    color: var(--color-text);
  }

  .selected-avatar {
    width: 100px;
    height: 100px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 2.2rem;
    font-weight: 600;
    color: white;
    text-transform: uppercase;
  }

  .pin-entry h2 {
    margin: 0;
    font-size: 1.5rem;
  }

  .pin-form {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: var(--spacing-md);
    width: 100%;
    max-width: 280px;
  }

  .pin-form label {
    color: var(--color-text-secondary);
    font-size: 0.9rem;
  }

  .pin-form input {
    width: 100%;
    padding: var(--spacing-md);
    font-size: 1.5rem;
    text-align: center;
    letter-spacing: 0.5em;
    border: 2px solid var(--color-border);
    border-radius: var(--radius-md);
    background: var(--color-bg-secondary);
    color: var(--color-text);
  }

  .pin-form input:focus {
    outline: none;
    border-color: var(--color-primary);
  }

  .login-error {
    color: var(--color-error);
    font-size: 0.9rem;
    margin: 0;
  }

  .login-btn {
    padding: var(--spacing-md) var(--spacing-xl);
    font-size: 1rem;
    font-weight: 500;
    background: var(--color-primary);
    color: white;
    border: none;
    border-radius: var(--radius-md);
    cursor: pointer;
    transition: opacity 0.2s;
    min-width: 160px;
  }

  .login-btn:hover:not(:disabled) {
    opacity: 0.9;
  }

  .login-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  /* Guest Option */
  .guest-option {
    padding-top: var(--spacing-lg);
    border-top: 1px solid var(--color-border);
  }

  .guest-btn {
    background: none;
    border: none;
    color: var(--color-text-secondary);
    font-size: 0.95rem;
    cursor: pointer;
    padding: var(--spacing-sm);
  }

  .guest-btn:hover {
    color: var(--color-text);
    text-decoration: underline;
  }

  /* Mobile */
  @media (max-width: 480px) {
    .login-header h1 {
      font-size: 2rem;
    }

    .users-grid {
      grid-template-columns: repeat(2, 1fr);
    }

    .user-avatar {
      width: 60px;
      height: 60px;
      font-size: 1.4rem;
    }
  }
</style>
