<script lang="ts">
  import '$lib/../app.css';
  import Sidebar from '$lib/components/Sidebar.svelte';
  import { VideoPlayerModal, PiPPlayer } from '$lib/components/VideoPlayer';
  import BackgroundPlaybackHandler from '$lib/components/VideoPlayer/BackgroundPlaybackHandler.svelte';
  import { page } from '$app/stores';
  import { goto } from '$app/navigation';
  import { themeStore } from '$lib/stores/theme.svelte';
  import { auth } from '$lib/stores/auth.svelte';
  import { videoPlayer } from '$lib/stores/videoPlayer.svelte';

  let { children } = $props();
  let sidebarOpen = $state(false);

  // Initialize theme on mount
  $effect(() => {
    const cleanup = themeStore.init();
    return cleanup;
  });

  // Initialize auth on mount
  $effect(() => {
    auth.init();
  });

  // Initialize media session for background playback controls
  $effect(() => {
    videoPlayer.initMediaSession();
  });

  // Auth guard - always redirect to login if not authenticated
  $effect(() => {
    if (auth.isInitialized && !auth.isLoading) {
      const currentPath = $page.url.pathname;
      const isLoginPage = currentPath === '/login';
      const isSettingsPage = currentPath.startsWith('/settings');

      // Always redirect to login if not authenticated
      // Allow settings pages for initial setup
      if (!auth.isAuthenticated && !isLoginPage && !isSettingsPage) {
        goto('/login');
      }
    }
  });

  // Check if we should show the full app layout (not on login page)
  const isLoginPage = $derived($page.url.pathname === '/login');

  function toggleSidebar() {
    sidebarOpen = !sidebarOpen;
  }

  function closeSidebar() {
    sidebarOpen = false;
  }

  // Get current page title for mobile header
  function getPageTitle(pathname: string): string {
    if (pathname === '/' || pathname.startsWith('/discover')) return 'Discover';
    if (pathname.startsWith('/feed')) return 'Feed';
    if (pathname.startsWith('/subscriptions')) return 'Subscriptions';
    if (pathname.startsWith('/saved')) return 'Saved';
    if (pathname.startsWith('/collections')) return 'Collections';
    if (pathname.startsWith('/history')) return 'History';
    if (pathname.startsWith('/crawler')) return 'Web Crawler';
    if (pathname.startsWith('/indexes')) return 'Indexes';
    if (pathname.startsWith('/settings')) return 'Settings';
    return 'WebSearch';
  }
</script>

{#if isLoginPage}
  <!-- Login page - full screen, no sidebar -->
  <main class="login-layout">
    {@render children()}
  </main>
{:else}
  <div class="app-layout">
    <!-- Mobile Header -->
    <header class="mobile-header hide-desktop">
      <button class="hamburger-btn" onclick={toggleSidebar} aria-label="Toggle menu">
        <span class="hamburger-icon">
          <span></span>
          <span></span>
          <span></span>
        </span>
      </button>
      <h1 class="mobile-title">{getPageTitle($page.url.pathname)}</h1>
    </header>

    <!-- Overlay for mobile sidebar -->
    <div
      class="mobile-overlay"
      class:active={sidebarOpen}
      onclick={closeSidebar}
      role="button"
      tabindex="-1"
      aria-label="Close sidebar"
    ></div>

    <Sidebar bind:isOpen={sidebarOpen} onClose={closeSidebar} />

    <main class="main-content">
      {@render children()}
    </main>

    <!-- Global Video Player Modal -->
    <VideoPlayerModal />

    <!-- Picture-in-Picture Player -->
    <PiPPlayer />

    <!-- Background Playback Handler (no UI) -->
    <BackgroundPlaybackHandler />
  </div>
{/if}

<style>
  .login-layout {
    min-height: 100vh;
    background: var(--color-bg);
  }

  .app-layout {
    display: flex;
    min-height: 100vh;
  }

  .main-content {
    flex: 1;
    margin-left: var(--sidebar-width);
    padding: var(--spacing-xl);
    overflow-y: auto;
  }

  /* Mobile Header */
  .mobile-header {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    height: var(--mobile-header-height);
    background: var(--color-bg-secondary);
    border-bottom: 1px solid var(--color-border);
    display: flex;
    align-items: center;
    padding: 0 var(--spacing-md);
    gap: var(--spacing-md);
    z-index: 100;
  }

  .hamburger-btn {
    background: none;
    border: none;
    padding: var(--spacing-sm);
    min-width: var(--touch-target-min);
    min-height: var(--touch-target-min);
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: var(--radius-md);
  }

  .hamburger-btn:hover {
    background: var(--color-bg);
  }

  .hamburger-icon {
    display: flex;
    flex-direction: column;
    gap: 5px;
    width: 24px;
  }

  .hamburger-icon span {
    display: block;
    height: 2px;
    background: var(--color-text);
    border-radius: 2px;
    transition: all 0.2s ease;
  }

  .mobile-title {
    font-size: 1.1rem;
    font-weight: 600;
    color: var(--color-text);
    margin: 0;
  }

  /* Mobile overlay */
  .mobile-overlay {
    display: none;
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.5);
    z-index: 998;
    opacity: 0;
    transition: opacity 0.3s ease;
  }

  .mobile-overlay.active {
    opacity: 1;
  }

  /* Mobile responsive */
  @media (max-width: 768px) {
    .main-content {
      margin-left: 0;
      padding: var(--spacing-md);
      padding-top: calc(var(--mobile-header-height) + var(--spacing-md));
    }

    .mobile-overlay {
      display: block;
      pointer-events: none;
    }

    .mobile-overlay.active {
      pointer-events: auto;
    }
  }

  /* Tablet adjustments */
  @media (min-width: 769px) and (max-width: 1024px) {
    .main-content {
      padding: var(--spacing-lg);
    }
  }
</style>
