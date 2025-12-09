<script lang="ts">
  import { page } from '$app/stores';

  interface NavItem {
    href: string;
    label: string;
    icon: string;
  }

  const navItems: NavItem[] = [
    { href: '/', label: 'Search', icon: '🔍' },
    { href: '/indexes', label: 'Indexes', icon: '📚' },
    { href: '/crawl', label: 'Crawl Status', icon: '🔄' },
    { href: '/settings', label: 'Settings', icon: '⚙️' },
  ];

  function isActive(href: string, currentPath: string): boolean {
    if (href === '/') return currentPath === '/';
    return currentPath.startsWith(href);
  }
</script>

<aside class="sidebar">
  <div class="sidebar-header">
    <h1 class="logo">WebSearch</h1>
    <span class="version">v0.1.0</span>
  </div>

  <nav class="nav">
    {#each navItems as item}
      <a
        href={item.href}
        class="nav-item"
        class:active={isActive(item.href, $page.url.pathname)}
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
  }

  .sidebar-header {
    padding: var(--spacing-lg);
    border-bottom: 1px solid var(--color-border);
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

  .nav {
    flex: 1;
    padding: var(--spacing-md);
    display: flex;
    flex-direction: column;
    gap: var(--spacing-xs);
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
    font-size: 1.1rem;
  }

  .nav-label {
    font-weight: 500;
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
</style>
