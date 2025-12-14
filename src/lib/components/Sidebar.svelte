<script lang="ts">
  import { page } from '$app/stores';

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

  const navItems: NavItem[] = [
    { href: '/', label: 'Search', icon: '🔍' },
    { href: '/discover', label: 'Discover', icon: '🌐' },
    { href: '/saved', label: 'Saved', icon: '💾' },
    { href: '/feed', label: 'Feed', icon: '📺' },
    { href: '/history', label: 'History', icon: '⏱️' },
    { href: '/subscriptions', label: 'Subscriptions', icon: '🔔' },
    { href: '/collections', label: 'Collections', icon: '📁' },
    { href: '/indexes', label: 'Indexes', icon: '📚' },
    { href: '/crawl', label: 'Crawl Status', icon: '🔄' },
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
    <div class="status">
      <span class="status-dot"></span>
      <span class="status-text">Backend connected</span>
    </div>
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
