/**
 * Hidden Channels Store
 * Manages hidden channels state for Discover page filtering using Svelte 5 runes
 */

import { api, type HiddenChannel, type HiddenChannelCreate } from '$lib/api/client';

/**
 * Hidden Channels state using Svelte 5 runes
 */
function createHiddenChannelsStore() {
  let hiddenChannels = $state<HiddenChannel[]>([]);
  let hiddenKeys = $state<Set<string>>(new Set());
  let isLoading = $state(false);
  let isLoaded = $state(false);
  let error = $state<string | null>(null);

  /**
   * Create a unique key for a channel (platform:channel_id)
   */
  function makeKey(platform: string, channelId: string): string {
    return `${platform}:${channelId}`;
  }

  /**
   * Load hidden channels from API
   */
  async function load(): Promise<void> {
    if (isLoading) return;

    isLoading = true;
    error = null;

    try {
      const response = await api.listHiddenChannels();
      hiddenChannels = response.items;
      hiddenKeys = new Set(response.items.map(c => makeKey(c.platform, c.channel_id)));
      isLoaded = true;
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to load hidden channels';
      console.error('Failed to load hidden channels:', e);
    } finally {
      isLoading = false;
    }
  }

  /**
   * Hide a channel
   */
  async function hide(data: HiddenChannelCreate): Promise<boolean> {
    const key = makeKey(data.platform, data.channel_id);

    // Already hidden
    if (hiddenKeys.has(key)) {
      return true;
    }

    try {
      const hidden = await api.hideChannel(data);
      hiddenChannels = [...hiddenChannels, hidden];
      hiddenKeys = new Set([...hiddenKeys, key]);
      return true;
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to hide channel';
      console.error('Failed to hide channel:', e);
      return false;
    }
  }

  /**
   * Unhide a channel
   */
  async function unhide(platform: string, channelId: string): Promise<boolean> {
    const key = makeKey(platform, channelId);

    // Not hidden
    if (!hiddenKeys.has(key)) {
      return true;
    }

    try {
      await api.unhideChannel(platform, channelId);
      hiddenChannels = hiddenChannels.filter(c =>
        !(c.platform === platform && c.channel_id === channelId)
      );
      const newKeys = new Set(hiddenKeys);
      newKeys.delete(key);
      hiddenKeys = newKeys;
      return true;
    } catch (e) {
      error = e instanceof Error ? e.message : 'Failed to unhide channel';
      console.error('Failed to unhide channel:', e);
      return false;
    }
  }

  /**
   * Check if a channel is hidden
   */
  function isHidden(platform: string, channelId: string): boolean {
    return hiddenKeys.has(makeKey(platform, channelId));
  }

  /**
   * Clear error state
   */
  function clearError(): void {
    error = null;
  }

  return {
    // State (using getters for reactivity)
    get channels() { return hiddenChannels; },
    get count() { return hiddenChannels.length; },
    get isLoading() { return isLoading; },
    get isLoaded() { return isLoaded; },
    get error() { return error; },

    // Methods
    load,
    hide,
    unhide,
    isHidden,
    clearError,
  };
}

// Singleton instance
export const hiddenChannelsStore = createHiddenChannelsStore();
