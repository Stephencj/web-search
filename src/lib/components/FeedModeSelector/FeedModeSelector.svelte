<script lang="ts">
  import type { FeedMode } from '$lib/api/client';

  interface Props {
    currentMode: FeedMode | null;
    onModeChange: (mode: FeedMode | null) => void;
  }

  let { currentMode, onModeChange }: Props = $props();
  let showDropdown = $state(false);

  interface ModeOption {
    id: FeedMode;
    name: string;
    icon: string;
    desc?: string;
  }

  const modes: Record<string, ModeOption[]> = {
    standard: [
      { id: 'newest', name: 'Newest First', icon: '🕐' },
      { id: 'oldest', name: 'Oldest First', icon: '📅' },
      { id: 'most_viewed', name: 'Most Viewed', icon: '👁️' },
      { id: 'shortest', name: 'Shortest', icon: '⚡' },
      { id: 'longest', name: 'Longest', icon: '📺' },
      { id: 'random', name: 'Random Shuffle', icon: '🎲' },
    ],
    smart: [
      { id: 'catch_up', name: 'Catch Up', icon: '📚', desc: 'Oldest unwatched first' },
      { id: 'quick_watch', name: 'Quick Watch', icon: '⚡', desc: 'Under 10 min' },
      { id: 'deep_dive', name: 'Deep Dive', icon: '🏊', desc: 'Over 30 min' },
    ],
    mood: [
      { id: 'focus_learning', name: 'Focus on Learning', icon: '🎓' },
      { id: 'stay_positive', name: 'Stay Positive', icon: '😊' },
      { id: 'music_mode', name: 'Music Mode', icon: '🎵' },
      { id: 'news_politics', name: 'News & Politics', icon: '📰' },
      { id: 'gaming', name: 'Gaming', icon: '🎮' },
    ],
  };

  function getModeLabel(mode: FeedMode): string {
    for (const group of Object.values(modes)) {
      const found = group.find(m => m.id === mode);
      if (found) return `${found.icon} ${found.name}`;
    }
    return 'Feed Mode';
  }

  function selectMode(mode: FeedMode) {
    onModeChange(mode);
    showDropdown = false;
  }

  function clearMode() {
    onModeChange(null);
    showDropdown = false;
  }

  function handleClickOutside(event: MouseEvent) {
    const target = event.target as HTMLElement;
    if (!target.closest('.mode-selector')) {
      showDropdown = false;
    }
  }

  $effect(() => {
    if (showDropdown) {
      document.addEventListener('click', handleClickOutside);
      return () => document.removeEventListener('click', handleClickOutside);
    }
  });
</script>

<div class="mode-selector">
  <button class="mode-button" class:active={currentMode} onclick={() => showDropdown = !showDropdown}>
    <span class="label">{currentMode ? getModeLabel(currentMode) : 'Feed Mode'}</span>
    <svg class="chevron" class:open={showDropdown} width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
      <polyline points="6 9 12 15 18 9"></polyline>
    </svg>
  </button>

  {#if showDropdown}
    <div class="dropdown">
      <div class="group">
        <div class="group-label">Standard</div>
        {#each modes.standard as mode}
          <button
            class="mode-option"
            class:selected={currentMode === mode.id}
            onclick={() => selectMode(mode.id)}
          >
            <span class="icon">{mode.icon}</span>
            <span class="name">{mode.name}</span>
          </button>
        {/each}
      </div>

      <div class="group">
        <div class="group-label">Smart Modes</div>
        {#each modes.smart as mode}
          <button
            class="mode-option"
            class:selected={currentMode === mode.id}
            onclick={() => selectMode(mode.id)}
          >
            <span class="icon">{mode.icon}</span>
            <span class="name">{mode.name}</span>
            {#if mode.desc}
              <span class="desc">{mode.desc}</span>
            {/if}
          </button>
        {/each}
      </div>

      <div class="group">
        <div class="group-label">By Mood (YouTube Categories)</div>
        {#each modes.mood as mode}
          <button
            class="mode-option"
            class:selected={currentMode === mode.id}
            onclick={() => selectMode(mode.id)}
          >
            <span class="icon">{mode.icon}</span>
            <span class="name">{mode.name}</span>
          </button>
        {/each}
      </div>

      {#if currentMode}
        <div class="group">
          <button class="clear-btn" onclick={clearMode}>
            Clear Mode
          </button>
        </div>
      {/if}
    </div>
  {/if}
</div>

<style>
  .mode-selector {
    position: relative;
  }

  .mode-button {
    display: flex;
    align-items: center;
    gap: var(--spacing-xs);
    padding: var(--spacing-sm) var(--spacing-md);
    background: var(--color-bg-secondary);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    color: var(--color-text);
    cursor: pointer;
    font-size: 0.875rem;
    transition: all 0.2s ease;
  }

  .mode-button:hover {
    border-color: var(--color-primary);
  }

  .mode-button.active {
    background: var(--color-primary);
    color: white;
    border-color: var(--color-primary);
  }

  .chevron {
    transition: transform 0.2s ease;
  }

  .chevron.open {
    transform: rotate(180deg);
  }

  .dropdown {
    position: absolute;
    top: 100%;
    left: 0;
    margin-top: var(--spacing-xs);
    min-width: 240px;
    max-height: 400px;
    overflow-y: auto;
    background: var(--color-bg-secondary);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    box-shadow: var(--shadow-lg);
    z-index: 100;
  }

  .group {
    padding: var(--spacing-xs) 0;
    border-bottom: 1px solid var(--color-border);
  }

  .group:last-child {
    border-bottom: none;
  }

  .group-label {
    padding: var(--spacing-xs) var(--spacing-md);
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--color-text-secondary);
    text-transform: uppercase;
    letter-spacing: 0.05em;
  }

  .mode-option {
    display: flex;
    align-items: center;
    gap: var(--spacing-sm);
    width: 100%;
    padding: var(--spacing-sm) var(--spacing-md);
    background: none;
    border: none;
    color: var(--color-text);
    cursor: pointer;
    text-align: left;
    font-size: 0.875rem;
    transition: background 0.15s ease;
  }

  .mode-option:hover {
    background: var(--color-bg);
  }

  .mode-option.selected {
    background: var(--color-primary);
    color: white;
  }

  .mode-option .icon {
    flex-shrink: 0;
    width: 20px;
    text-align: center;
  }

  .mode-option .name {
    flex: 1;
  }

  .mode-option .desc {
    font-size: 0.75rem;
    color: var(--color-text-secondary);
  }

  .mode-option.selected .desc {
    color: rgba(255, 255, 255, 0.8);
  }

  .clear-btn {
    display: block;
    width: calc(100% - var(--spacing-md) * 2);
    margin: var(--spacing-xs) var(--spacing-md);
    padding: var(--spacing-sm);
    background: var(--color-error);
    border: none;
    border-radius: var(--radius-sm);
    color: white;
    cursor: pointer;
    font-size: 0.875rem;
    text-align: center;
    transition: opacity 0.15s ease;
  }

  .clear-btn:hover {
    opacity: 0.9;
  }

  @media (max-width: 768px) {
    .dropdown {
      position: fixed;
      left: var(--spacing-md);
      right: var(--spacing-md);
      bottom: var(--spacing-md);
      top: auto;
      max-height: 60vh;
      border-radius: var(--radius-lg);
    }
  }
</style>
