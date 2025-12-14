<script lang="ts">
  import { page } from '$app/stores';
  import { goto } from '$app/navigation';
  import { auth } from '$lib/stores/auth.svelte';

  interface NavItem {
    href: string;
    label: string;
    icon: string;
  }

  // Props for controlling sidebar state from parent
  interface Props {
    isOpen?: boolean;
    onClose?: () => void;
  }
  let { isOpen = $bindable(false), onClose = () => {} }: Props = $props();

  let showUserMenu = $state(false);

  const navItems: NavItem[] = [
    { href: '/discover', label: 'Discover', icon: '🌐' },
    { href: '/feed', label: 'Feed', icon: '📺' },
    { href: '/subscriptions', label: 'Subscriptions', icon: '🔔' },
    { href: '/saved', label: 'Saved', icon: '💾' },
    { href: '/collections', label: 'Collections', icon: '📁' },
    { href: '/history', label: 'History', icon: '⏱️' },
    { href: '/crawler', label: 'Web Crawler', icon: '🕷️' },
    { href: '/settings', label: 'Settings', icon: '⚙️' },
  ];

  function isActive(href: string, currentPath: string): boolean {
    if (href === '/') return currentPath === '/';
    return currentPath.startsWith(href);
  }

  function handleNavClick() {
    // Close sidebar on mobile when navigating
    if (window.innerWidth <= 768) {
      onClose();
    }
  }

  function getInitials(name: string): string {
    const parts = name.split(' ');
    if (parts.length >= 2) {
      return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
    }
    return name.slice(0, 2).toUpperCase();
  }

  async function handleLogout() {
    showUserMenu = false;
    await auth.logout();
    goto('/login');
  }

  async function handleSwitchUser() {
    showUserMenu = false;
    // Logout current user so they can select a different profile
    await auth.logout();
    goto('/login');
  }

  function toggleUserMenu() {
    showUserMenu = !showUserMenu;
  }
</script>

<aside class="sidebar" class:open={isOpen}>
  <div class="sidebar-header">
    <h1 class="logo">WebSearch</h1>
    <span class="version">v0.1.0</span>
    <button class="close-btn hide-desktop" onclick={onClose} aria-label="Close menu">
      ✕
    </button>
  </div>

  <nav class="nav">
    {#each navItems as item}
      <a
        href={item.href}
        class="nav-item"
        class:active={isActive(item.href, $page.url.pathname)}
        onclick={handleNavClick}
      >
        <span class="nav-icon">{item.icon}</span>
        <span class="nav-label">{item.label}</span>
      </a>
    {/each}
  </nav>

  <div class="sidebar-footer">
    {#if auth.user}
      <div class="user-section">
        <button class="user-profile" onclick={toggleUserMenu}>
          <div class="user-avatar" style="background-color: {auth.user.avatar_color}">
            {getInitials(auth.user.display_name)}
          </div>
          <div class="user-info">
            <span class="user-name">{auth.user.display_name}</span>
            <span class="user-username">@{auth.user.username}</span>
          </div>
          <svg class="dropdown-arrow" class:open={showUserMenu} viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
            <path d="M7 10l5 5 5-5z"/>
          </svg>
        </button>

        {#if showUserMenu}
          <div class="user-menu">
            <button class="user-menu-item" onclick={handleSwitchUser}>
              <svg viewBox="0 0 24 24" fill="currentColor" width="18" height="18">
                <path d="M16.67 13.13C18.04 14.06 19 15.32 19 17v3h4v-3c0-2.18-3.57-3.47-6.33-3.87z"/>
                <circle cx="9" cy="8" r="4"/>
                <path d="M15 12c2.21 0 4-1.79 4-4s-1.79-4-4-4c-.47 0-.91.1-1.33.24a5.98 5.98 0 010 7.52c.42.14.86.24 1.33.24z"/>
                <path d="M9 13c-2.67 0-8 1.34-8 4v3h16v-3c0-2.66-5.33-4-8-4z"/>
              </svg>
              Switch User
            </button>
            <button class="user-menu-item" onclick={handleLogout}>
              <svg viewBox="0 0 24 24" fill="currentColor" width="18" height="18">
                <path d="M17 7l-1.41 1.41L18.17 11H8v2h10.17l-2.58 2.58L17 17l5-5zM4 5h8V3H4c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h8v-2H4V5z"/>
              </svg>
              Logout
            </button>
          </div>
        {/if}
      </div>
    {:else}
      <div class="status">
        <span class="status-dot"></span>
        <span class="status-text">Backend connected</span>
      </div>
    {/if}
  </div>
</aside>

<style>
  .sidebar {
    width: var(--sidebar-width);
    height: 100vh;
    background: var(--color-bg-secondary);
    border-right: 1px solid var(--color-border);
    display: flex;
    flex-direction: column;
    position: fixed;
    left: 0;
    top: 0;
    z-index: 999;
    transition: transform 0.3s ease;
  }

  .sidebar-header {
    padding: var(--spacing-lg);
    border-bottom: 1px solid var(--color-border);
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    flex-wrap: wrap;
  }

  .logo {
    font-size: 1.25rem;
    font-weight: 600;
    color: var(--color-primary);
    margin: 0;
  }

  .version {
    font-size: 0.75rem;
    color: var(--color-text-secondary);
  }

  .close-btn {
    margin-left: auto;
    background: none;
    border: none;
    font-size: 1.25rem;
    color: var(--color-text-secondary);
    padding: var(--spacing-sm);
    min-width: var(--touch-target-min);
    min-height: var(--touch-target-min);
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: var(--radius-md);
  }

  .close-btn:hover {
    background: var(--color-bg);
    color: var(--color-text);
  }

  .nav {
    flex: 1;
    padding: var(--spacing-md);
    display: flex;
    flex-direction: column;
    gap: var(--spacing-xs);
    overflow-y: auto;
  }

  .nav-item {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    padding: var(--spacing-sm) var(--spacing-md);
    border-radius: var(--radius-md);
    color: var(--color-text);
    text-decoration: none;
    transition: all 0.2s ease;
    min-height: var(--touch-target-min);
  }

  .nav-item:hover {
    background: var(--color-bg);
    text-decoration: none;
  }

  .nav-item.active {
    background: var(--color-primary);
    color: white;
  }

  .nav-icon {
    font-size: 1.25rem;
  }

  .nav-label {
    font-weight: 500;
    font-size: 1rem;
  }

  .sidebar-footer {
    padding: var(--spacing-md) var(--spacing-lg);
    border-top: 1px solid var(--color-border);
  }

  .status {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
  }

  .status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--color-success);
  }

  .status-text {
    font-size: 0.75rem;
    color: var(--color-text-secondary);
  }

  /* User Section */
  .user-section {
    position: relative;
  }

  .user-profile {
    width: 100%;
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    padding: var(--spacing-sm);
    background: none;
    border: none;
    border-radius: var(--radius-md);
    cursor: pointer;
    text-align: left;
    transition: background 0.2s;
  }

  .user-profile:hover {
    background: var(--color-bg);
  }

  .user-avatar {
    width: 36px;
    height: 36px;
    border-radius: 50%;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 0.85rem;
    font-weight: 600;
    color: white;
    text-transform: uppercase;
    flex-shrink: 0;
  }

  .user-info {
    flex: 1;
    min-width: 0;
  }

  .user-name {
    display: block;
    font-weight: 500;
    font-size: 0.9rem;
    color: var(--color-text);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .user-username {
    display: block;
    font-size: 0.75rem;
    color: var(--color-text-secondary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .dropdown-arrow {
    color: var(--color-text-secondary);
    transition: transform 0.2s;
    flex-shrink: 0;
  }

  .dropdown-arrow.open {
    transform: rotate(180deg);
  }

  .user-menu {
    position: absolute;
    bottom: 100%;
    left: 0;
    right: 0;
    margin-bottom: var(--spacing-xs);
    background: var(--color-bg-secondary);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    box-shadow: var(--shadow-md);
    overflow: hidden;
  }

  .user-menu-item {
    width: 100%;
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    padding: var(--spacing-sm) var(--spacing-md);
    background: none;
    border: none;
    color: var(--color-text);
    font-size: 0.9rem;
    cursor: pointer;
    transition: background 0.2s;
    text-align: left;
  }

  .user-menu-item:hover {
    background: var(--color-bg);
  }

  .user-menu-item svg {
    color: var(--color-text-secondary);
  }

  /* Mobile styles */
  @media (max-width: 768px) {
    .sidebar {
      transform: translateX(-100%);
      width: 280px;
      box-shadow: var(--shadow-lg);
    }

    .sidebar.open {
      transform: translateX(0);
    }

    .nav-item {
      padding: var(--spacing-md);
      font-size: 1.1rem;
    }

    .nav-icon {
      font-size: 1.5rem;
    }
  }
</style>
