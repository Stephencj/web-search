<script lang="ts">
  import { onMount } from 'svelte';

  interface User {
    id: number;
    username: string;
    display_name: string;
    avatar_color: string;
    has_pin: boolean;
    is_admin: boolean;
    created_at: string;
    last_login_at: string | null;
  }

  // Color options for avatar
  const AVATAR_COLORS = [
    '#6366f1', // Indigo
    '#8b5cf6', // Violet
    '#d946ef', // Fuchsia
    '#ec4899', // Pink
    '#f43f5e', // Rose
    '#ef4444', // Red
    '#f97316', // Orange
    '#f59e0b', // Amber
    '#84cc16', // Lime
    '#22c55e', // Green
    '#14b8a6', // Teal
    '#06b6d4', // Cyan
    '#0ea5e9', // Sky
    '#3b82f6', // Blue
  ];

  let users = $state<User[]>([]);
  let loading = $state(true);
  let error = $state<string | null>(null);

  // Modal states
  let showCreateModal = $state(false);
  let showEditModal = $state(false);
  let showDeleteModal = $state(false);
  let showPinModal = $state(false);
  let selectedUser = $state<User | null>(null);

  // Form states
  let formUsername = $state('');
  let formDisplayName = $state('');
  let formAvatarColor = $state(AVATAR_COLORS[0]);
  let formIsAdmin = $state(false);
  let formPin = $state('');
  let formCurrentPin = $state('');
  let formNewPin = $state('');
  let formError = $state<string | null>(null);
  let formLoading = $state(false);

  onMount(() => {
    loadUsers();
  });

  async function loadUsers() {
    loading = true;
    error = null;
    try {
      const response = await fetch('/api/users');
      if (response.ok) {
        const data = await response.json();
        users = data.users;
      } else {
        error = 'Failed to load users';
      }
    } catch {
      error = 'Network error';
    } finally {
      loading = false;
    }
  }

  function openCreateModal() {
    formUsername = '';
    formDisplayName = '';
    formAvatarColor = AVATAR_COLORS[Math.floor(Math.random() * AVATAR_COLORS.length)];
    formIsAdmin = false;
    formPin = '';
    formError = null;
    showCreateModal = true;
  }

  function openEditModal(user: User) {
    selectedUser = user;
    formDisplayName = user.display_name;
    formAvatarColor = user.avatar_color;
    formIsAdmin = user.is_admin;
    formError = null;
    showEditModal = true;
  }

  function openDeleteModal(user: User) {
    selectedUser = user;
    showDeleteModal = true;
  }

  function openPinModal(user: User) {
    selectedUser = user;
    formCurrentPin = '';
    formNewPin = '';
    formError = null;
    showPinModal = true;
  }

  function closeModals() {
    showCreateModal = false;
    showEditModal = false;
    showDeleteModal = false;
    showPinModal = false;
    selectedUser = null;
    formError = null;
  }

  async function handleCreate() {
    formLoading = true;
    formError = null;

    try {
      const response = await fetch('/api/users', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          username: formUsername,
          display_name: formDisplayName,
          avatar_color: formAvatarColor,
          is_admin: formIsAdmin,
          pin: formPin || null,
        }),
      });

      if (response.ok) {
        await loadUsers();
        closeModals();
      } else {
        const data = await response.json();
        formError = data.detail || 'Failed to create user';
      }
    } catch {
      formError = 'Network error';
    } finally {
      formLoading = false;
    }
  }

  async function handleEdit() {
    if (!selectedUser) return;

    formLoading = true;
    formError = null;

    try {
      const response = await fetch(`/api/users/${selectedUser.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          display_name: formDisplayName,
          avatar_color: formAvatarColor,
          is_admin: formIsAdmin,
        }),
      });

      if (response.ok) {
        await loadUsers();
        closeModals();
      } else {
        const data = await response.json();
        formError = data.detail || 'Failed to update user';
      }
    } catch {
      formError = 'Network error';
    } finally {
      formLoading = false;
    }
  }

  async function handleDelete() {
    if (!selectedUser) return;

    formLoading = true;
    formError = null;

    try {
      const response = await fetch(`/api/users/${selectedUser.id}`, {
        method: 'DELETE',
      });

      if (response.ok) {
        await loadUsers();
        closeModals();
      } else {
        const data = await response.json();
        formError = data.detail || 'Failed to delete user';
      }
    } catch {
      formError = 'Network error';
    } finally {
      formLoading = false;
    }
  }

  async function handleSetPin() {
    if (!selectedUser) return;

    formLoading = true;
    formError = null;

    try {
      const response = await fetch(`/api/users/${selectedUser.id}/pin`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          current_pin: selectedUser.has_pin ? formCurrentPin : null,
          new_pin: formNewPin || null,
        }),
      });

      if (response.ok) {
        await loadUsers();
        closeModals();
      } else {
        const data = await response.json();
        formError = data.detail || 'Failed to update PIN';
      }
    } catch {
      formError = 'Network error';
    } finally {
      formLoading = false;
    }
  }

  function getInitials(name: string): string {
    const parts = name.split(' ');
    if (parts.length >= 2) {
      return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
    }
    return name.slice(0, 2).toUpperCase();
  }

  function formatDate(dateStr: string): string {
    return new Date(dateStr).toLocaleDateString();
  }
</script>

<div class="users-page">
  <header class="page-header">
    <div class="header-content">
      <a href="/settings" class="back-link">
        <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
          <path d="M20 11H7.83l5.59-5.59L12 4l-8 8 8 8 1.41-1.41L7.83 13H20v-2z"/>
        </svg>
        Settings
      </a>
      <h1>User Management</h1>
      <p class="subtitle">Create and manage user profiles</p>
    </div>
    <button class="add-btn" onclick={openCreateModal}>
      <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
        <path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/>
      </svg>
      Add User
    </button>
  </header>

  {#if loading}
    <div class="loading">
      <div class="spinner"></div>
      <span>Loading users...</span>
    </div>
  {:else if error}
    <div class="error-message">{error}</div>
  {:else}
    <div class="users-list">
      {#each users as user}
        <div class="user-card">
          <div class="user-avatar" style="background-color: {user.avatar_color}">
            {getInitials(user.display_name)}
          </div>
          <div class="user-info">
            <h3>{user.display_name}</h3>
            <p class="username">@{user.username}</p>
            <div class="user-badges">
              {#if user.is_admin}
                <span class="badge admin">Admin</span>
              {/if}
              {#if user.has_pin}
                <span class="badge pin">PIN Protected</span>
              {:else}
                <span class="badge no-pin">No PIN</span>
              {/if}
            </div>
            <p class="user-meta">
              Created {formatDate(user.created_at)}
              {#if user.last_login_at}
                | Last login {formatDate(user.last_login_at)}
              {/if}
            </p>
          </div>
          <div class="user-actions">
            <button class="action-btn" onclick={() => openPinModal(user)} title="Manage PIN">
              <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
                <path d="M18 8h-1V6c0-2.76-2.24-5-5-5S7 3.24 7 6v2H6c-1.1 0-2 .9-2 2v10c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V10c0-1.1-.9-2-2-2zm-6 9c-1.1 0-2-.9-2-2s.9-2 2-2 2 .9 2 2-.9 2-2 2zm3.1-9H8.9V6c0-1.71 1.39-3.1 3.1-3.1 1.71 0 3.1 1.39 3.1 3.1v2z"/>
              </svg>
            </button>
            <button class="action-btn" onclick={() => openEditModal(user)} title="Edit user">
              <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
                <path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04c.39-.39.39-1.02 0-1.41l-2.34-2.34c-.39-.39-1.02-.39-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z"/>
              </svg>
            </button>
            <button class="action-btn danger" onclick={() => openDeleteModal(user)} title="Delete user" disabled={users.length <= 1}>
              <svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
                <path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/>
              </svg>
            </button>
          </div>
        </div>
      {/each}

      {#if users.length === 0}
        <div class="empty-state">
          <p>No users yet. Create your first user to get started.</p>
        </div>
      {/if}
    </div>
  {/if}
</div>

<!-- Create User Modal -->
{#if showCreateModal}
  <div class="modal-overlay" onclick={closeModals}>
    <div class="modal" onclick={(e) => e.stopPropagation()}>
      <h2>Create User</h2>

      <div class="form-group">
        <label for="username">Username</label>
        <input id="username" type="text" bind:value={formUsername} placeholder="johndoe" />
      </div>

      <div class="form-group">
        <label for="displayName">Display Name</label>
        <input id="displayName" type="text" bind:value={formDisplayName} placeholder="John Doe" />
      </div>

      <div class="form-group">
        <label>Avatar Color</label>
        <div class="color-picker">
          {#each AVATAR_COLORS as color}
            <button
              class="color-option"
              class:selected={formAvatarColor === color}
              style="background-color: {color}"
              onclick={() => formAvatarColor = color}
            ></button>
          {/each}
        </div>
      </div>

      <div class="form-group">
        <label for="pin">PIN (optional)</label>
        <input id="pin" type="password" bind:value={formPin} placeholder="Leave empty for no PIN" />
      </div>

      <div class="form-group checkbox">
        <label>
          <input type="checkbox" bind:checked={formIsAdmin} />
          Admin user
        </label>
      </div>

      {#if formError}
        <p class="form-error">{formError}</p>
      {/if}

      <div class="modal-actions">
        <button class="btn secondary" onclick={closeModals} disabled={formLoading}>Cancel</button>
        <button class="btn primary" onclick={handleCreate} disabled={formLoading || !formUsername || !formDisplayName}>
          {formLoading ? 'Creating...' : 'Create User'}
        </button>
      </div>
    </div>
  </div>
{/if}

<!-- Edit User Modal -->
{#if showEditModal && selectedUser}
  <div class="modal-overlay" onclick={closeModals}>
    <div class="modal" onclick={(e) => e.stopPropagation()}>
      <h2>Edit User</h2>

      <div class="form-group">
        <label for="editDisplayName">Display Name</label>
        <input id="editDisplayName" type="text" bind:value={formDisplayName} />
      </div>

      <div class="form-group">
        <label>Avatar Color</label>
        <div class="color-picker">
          {#each AVATAR_COLORS as color}
            <button
              class="color-option"
              class:selected={formAvatarColor === color}
              style="background-color: {color}"
              onclick={() => formAvatarColor = color}
            ></button>
          {/each}
        </div>
      </div>

      <div class="form-group checkbox">
        <label>
          <input type="checkbox" bind:checked={formIsAdmin} />
          Admin user
        </label>
      </div>

      {#if formError}
        <p class="form-error">{formError}</p>
      {/if}

      <div class="modal-actions">
        <button class="btn secondary" onclick={closeModals} disabled={formLoading}>Cancel</button>
        <button class="btn primary" onclick={handleEdit} disabled={formLoading || !formDisplayName}>
          {formLoading ? 'Saving...' : 'Save Changes'}
        </button>
      </div>
    </div>
  </div>
{/if}

<!-- Delete User Modal -->
{#if showDeleteModal && selectedUser}
  <div class="modal-overlay" onclick={closeModals}>
    <div class="modal" onclick={(e) => e.stopPropagation()}>
      <h2>Delete User</h2>
      <p>Are you sure you want to delete <strong>{selectedUser.display_name}</strong>?</p>
      <p class="warning">This action cannot be undone.</p>

      {#if formError}
        <p class="form-error">{formError}</p>
      {/if}

      <div class="modal-actions">
        <button class="btn secondary" onclick={closeModals} disabled={formLoading}>Cancel</button>
        <button class="btn danger" onclick={handleDelete} disabled={formLoading}>
          {formLoading ? 'Deleting...' : 'Delete User'}
        </button>
      </div>
    </div>
  </div>
{/if}

<!-- PIN Modal -->
{#if showPinModal && selectedUser}
  <div class="modal-overlay" onclick={closeModals}>
    <div class="modal" onclick={(e) => e.stopPropagation()}>
      <h2>{selectedUser.has_pin ? 'Change PIN' : 'Set PIN'}</h2>

      {#if selectedUser.has_pin}
        <div class="form-group">
          <label for="currentPin">Current PIN</label>
          <input id="currentPin" type="password" bind:value={formCurrentPin} />
        </div>
      {/if}

      <div class="form-group">
        <label for="newPin">
          {selectedUser.has_pin ? 'New PIN (leave empty to remove)' : 'PIN'}
        </label>
        <input id="newPin" type="password" bind:value={formNewPin} placeholder="4+ characters" />
      </div>

      {#if formError}
        <p class="form-error">{formError}</p>
      {/if}

      <div class="modal-actions">
        <button class="btn secondary" onclick={closeModals} disabled={formLoading}>Cancel</button>
        <button class="btn primary" onclick={handleSetPin} disabled={formLoading}>
          {formLoading ? 'Saving...' : 'Save PIN'}
        </button>
      </div>
    </div>
  </div>
{/if}

<style>
  .users-page {
    max-width: 800px;
    margin: 0 auto;
  }

  .page-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: var(--spacing-xl);
    gap: var(--spacing-lg);
  }

  .back-link {
    display: flex;
    align-items: center;
    gap: var(--spacing-xs);
    color: var(--color-text-secondary);
    text-decoration: none;
    font-size: 0.9rem;
    margin-bottom: var(--spacing-sm);
  }

  .back-link:hover {
    color: var(--color-primary);
  }

  .page-header h1 {
    font-size: 1.75rem;
    margin: 0 0 var(--spacing-xs) 0;
  }

  .subtitle {
    color: var(--color-text-secondary);
    margin: 0;
    font-size: 0.9rem;
  }

  .add-btn {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    padding: var(--spacing-sm) var(--spacing-md);
    background: var(--color-primary);
    color: white;
    border: none;
    border-radius: var(--radius-md);
    font-weight: 500;
    cursor: pointer;
  }

  .add-btn:hover {
    opacity: 0.9;
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

  .users-list {
    display: flex;
    flex-direction: column;
    gap: var(--spacing-md);
  }

  .user-card {
    display: flex;
    align-items: center;
    gap: var(--spacing-md);
    padding: var(--spacing-lg);
    background: var(--color-bg-secondary);
    border-radius: var(--radius-lg);
  }

  .user-avatar {
    width: 60px;
    height: 60px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 1.4rem;
    font-weight: 600;
    color: white;
    flex-shrink: 0;
  }

  .user-info {
    flex: 1;
    min-width: 0;
  }

  .user-info h3 {
    margin: 0 0 var(--spacing-xs) 0;
    font-size: 1.1rem;
  }

  .username {
    color: var(--color-text-secondary);
    font-size: 0.85rem;
    margin: 0 0 var(--spacing-xs) 0;
  }

  .user-badges {
    display: flex;
    gap: var(--spacing-xs);
    margin-bottom: var(--spacing-xs);
  }

  .badge {
    font-size: 0.7rem;
    padding: 2px 6px;
    border-radius: var(--radius-sm);
    text-transform: uppercase;
    font-weight: 600;
  }

  .badge.admin {
    background: rgba(99, 102, 241, 0.2);
    color: #6366f1;
  }

  .badge.pin {
    background: rgba(34, 197, 94, 0.2);
    color: #22c55e;
  }

  .badge.no-pin {
    background: rgba(156, 163, 175, 0.2);
    color: var(--color-text-secondary);
  }

  .user-meta {
    color: var(--color-text-secondary);
    font-size: 0.75rem;
    margin: 0;
  }

  .user-actions {
    display: flex;
    gap: var(--spacing-xs);
  }

  .action-btn {
    padding: var(--spacing-sm);
    background: var(--color-bg);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    color: var(--color-text-secondary);
    cursor: pointer;
  }

  .action-btn:hover:not(:disabled) {
    color: var(--color-text);
    border-color: var(--color-text-secondary);
  }

  .action-btn.danger:hover:not(:disabled) {
    color: var(--color-error);
    border-color: var(--color-error);
  }

  .action-btn:disabled {
    opacity: 0.3;
    cursor: not-allowed;
  }

  .empty-state {
    text-align: center;
    padding: var(--spacing-xxl);
    color: var(--color-text-secondary);
  }

  /* Modal */
  .modal-overlay {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.7);
    display: flex;
    align-items: center;
    justify-content: center;
    padding: var(--spacing-lg);
    z-index: 1000;
  }

  .modal {
    background: var(--color-bg-secondary);
    border-radius: var(--radius-lg);
    padding: var(--spacing-xl);
    max-width: 400px;
    width: 100%;
  }

  .modal h2 {
    margin: 0 0 var(--spacing-lg) 0;
    font-size: 1.3rem;
  }

  .form-group {
    margin-bottom: var(--spacing-md);
  }

  .form-group label {
    display: block;
    margin-bottom: var(--spacing-xs);
    font-size: 0.9rem;
    color: var(--color-text-secondary);
  }

  .form-group input[type="text"],
  .form-group input[type="password"] {
    width: 100%;
    padding: var(--spacing-sm) var(--spacing-md);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    background: var(--color-bg);
    color: var(--color-text);
    font-size: 1rem;
  }

  .form-group input:focus {
    outline: none;
    border-color: var(--color-primary);
  }

  .form-group.checkbox label {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    cursor: pointer;
  }

  .color-picker {
    display: flex;
    flex-wrap: wrap;
    gap: var(--spacing-xs);
  }

  .color-option {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    border: 3px solid transparent;
    cursor: pointer;
    transition: transform 0.1s;
  }

  .color-option:hover {
    transform: scale(1.1);
  }

  .color-option.selected {
    border-color: white;
    box-shadow: 0 0 0 2px var(--color-primary);
  }

  .form-error {
    color: var(--color-error);
    font-size: 0.9rem;
    margin: var(--spacing-sm) 0;
  }

  .warning {
    color: var(--color-text-secondary);
    font-size: 0.9rem;
  }

  .modal-actions {
    display: flex;
    justify-content: flex-end;
    gap: var(--spacing-sm);
    margin-top: var(--spacing-lg);
  }

  .btn {
    padding: var(--spacing-sm) var(--spacing-lg);
    border-radius: var(--radius-md);
    font-weight: 500;
    cursor: pointer;
    border: none;
  }

  .btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .btn.primary {
    background: var(--color-primary);
    color: white;
  }

  .btn.secondary {
    background: var(--color-bg);
    color: var(--color-text);
    border: 1px solid var(--color-border);
  }

  .btn.danger {
    background: var(--color-error);
    color: white;
  }

  /* Mobile */
  @media (max-width: 600px) {
    .page-header {
      flex-direction: column;
    }

    .add-btn {
      width: 100%;
      justify-content: center;
    }

    .user-card {
      flex-wrap: wrap;
    }

    .user-actions {
      width: 100%;
      justify-content: flex-end;
      padding-top: var(--spacing-sm);
      border-top: 1px solid var(--color-border);
      margin-top: var(--spacing-sm);
    }
  }
</style>
