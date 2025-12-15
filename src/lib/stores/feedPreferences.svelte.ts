/**
 * Feed Preferences Store
 * Manages feed display preferences (mode, view, filter)
 * Persists to localStorage
 */

import type { FeedMode } from '$lib/api/client';

export type ViewMode = 'chronological' | 'by_channel';
export type FilterStatus = 'all' | 'unwatched' | 'watched';
export type PlatformFilter = string; // 'all' or platform id

interface FeedPreferences {
  mode: FeedMode | null;
  viewMode: ViewMode;
  filterStatus: FilterStatus;
  platformFilter: PlatformFilter;
}

const STORAGE_KEY = 'websearch-feed-preferences';

/**
 * Get initial preferences from localStorage or defaults
 */
function getInitialPreferences(): FeedPreferences {
  const defaults: FeedPreferences = {
    mode: null,
    viewMode: 'chronological',
    filterStatus: 'unwatched',
    platformFilter: 'all',
  };

  if (typeof window === 'undefined') return defaults;

  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      const parsed = JSON.parse(stored);
      return { ...defaults, ...parsed };
    }
  } catch (e) {
    console.warn('Failed to load feed preferences:', e);
  }

  return defaults;
}

/**
 * Save preferences to localStorage
 */
function savePreferences(prefs: FeedPreferences) {
  if (typeof window === 'undefined') return;
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs));
  } catch (e) {
    console.warn('Failed to save feed preferences:', e);
  }
}

/**
 * Feed Preferences store using Svelte 5 runes
 */
function createFeedPreferencesStore() {
  let preferences = $state<FeedPreferences>(getInitialPreferences());

  return {
    /**
     * Get current mode
     */
    get mode() {
      return preferences.mode;
    },

    /**
     * Get current view mode
     */
    get viewMode() {
      return preferences.viewMode;
    },

    /**
     * Get current filter status
     */
    get filterStatus() {
      return preferences.filterStatus;
    },

    /**
     * Get current platform filter
     */
    get platformFilter() {
      return preferences.platformFilter;
    },

    /**
     * Get all preferences
     */
    get all() {
      return preferences;
    },

    /**
     * Set feed mode
     */
    setMode(mode: FeedMode | null) {
      preferences = { ...preferences, mode };
      savePreferences(preferences);
    },

    /**
     * Set view mode
     */
    setViewMode(viewMode: ViewMode) {
      preferences = { ...preferences, viewMode };
      savePreferences(preferences);
    },

    /**
     * Set filter status
     */
    setFilterStatus(filterStatus: FilterStatus) {
      preferences = { ...preferences, filterStatus };
      savePreferences(preferences);
    },

    /**
     * Set platform filter
     */
    setPlatformFilter(platformFilter: PlatformFilter) {
      preferences = { ...preferences, platformFilter };
      savePreferences(preferences);
    },

    /**
     * Reset to defaults
     */
    reset() {
      preferences = {
        mode: null,
        viewMode: 'chronological',
        filterStatus: 'unwatched',
        platformFilter: 'all',
      };
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
export const feedPreferences = createFeedPreferencesStore();
