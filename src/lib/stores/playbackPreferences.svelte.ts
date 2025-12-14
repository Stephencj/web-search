/**
 * Playback Preferences Store
 * Manages video playback settings like background playback
 * Persists to localStorage
 */

export interface PlaybackPreferences {
  backgroundPlayback: boolean;
}

const STORAGE_KEY = 'websearch-playback-preferences';

const defaults: PlaybackPreferences = {
  backgroundPlayback: false,
};

/**
 * Get initial preferences from localStorage or defaults
 */
function getInitialPreferences(): PlaybackPreferences {
  if (typeof window === 'undefined') return defaults;

  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      const parsed = JSON.parse(stored);
      return { ...defaults, ...parsed };
    }
  } catch (e) {
    console.warn('Failed to load playback preferences:', e);
  }

  return defaults;
}

/**
 * Save preferences to localStorage
 */
function savePreferences(prefs: PlaybackPreferences) {
  if (typeof window === 'undefined') return;
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs));
  } catch (e) {
    console.warn('Failed to save playback preferences:', e);
  }
}

/**
 * Playback Preferences store using Svelte 5 runes
 */
function createPlaybackPreferencesStore() {
  let preferences = $state<PlaybackPreferences>(getInitialPreferences());

  return {
    /**
     * Get whether background playback is enabled
     */
    get backgroundPlayback() {
      return preferences.backgroundPlayback;
    },

    /**
     * Get all preferences
     */
    get all() {
      return preferences;
    },

    /**
     * Set background playback preference
     */
    setBackgroundPlayback(enabled: boolean) {
      preferences = { ...preferences, backgroundPlayback: enabled };
      savePreferences(preferences);
    },

    /**
     * Toggle background playback
     */
    toggleBackgroundPlayback() {
      this.setBackgroundPlayback(!preferences.backgroundPlayback);
    },

    /**
     * Reset to defaults
     */
    reset() {
      preferences = { ...defaults };
      savePreferences(preferences);
    },

    /**
     * Initialize on client-side mount
     */
    init() {
      if (typeof window === 'undefined') return;
      preferences = getInitialPreferences();
    },
  };
}

// Global singleton store
export const playbackPreferences = createPlaybackPreferencesStore();
