/**
 * Quality Preferences Store
 * Manages video quality settings (auto, 1080p, 720p, etc.)
 * Persists to localStorage
 */

export type QualityLevel = 'auto' | 'best' | '2160p' | '1080p' | '720p' | '480p' | '360p' | 'worst';

export interface QualityPreferences {
  preferredQuality: QualityLevel;
  perPlatformQuality: Record<string, QualityLevel>; // platform -> quality
}

const STORAGE_KEY = 'websearch-quality-preferences';

const defaults: QualityPreferences = {
  preferredQuality: 'auto',
  perPlatformQuality: {},
};

/**
 * Get initial preferences from localStorage or defaults
 */
function getInitialPreferences(): QualityPreferences {
  if (typeof window === 'undefined') return defaults;

  try {
    const stored = localStorage.getItem(STORAGE_KEY);
    if (stored) {
      const parsed = JSON.parse(stored);
      return { ...defaults, ...parsed };
    }
  } catch (e) {
    console.warn('Failed to load quality preferences:', e);
  }

  return defaults;
}

/**
 * Save preferences to localStorage
 */
function savePreferences(prefs: QualityPreferences) {
  if (typeof window === 'undefined') return;
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(prefs));
  } catch (e) {
    console.warn('Failed to save quality preferences:', e);
  }
}

/**
 * Quality Preferences store using Svelte 5 runes
 */
function createQualityPreferencesStore() {
  let preferences = $state<QualityPreferences>(getInitialPreferences());

  return {
    /**
     * Get the global preferred quality
     */
    get preferredQuality() {
      return preferences.preferredQuality;
    },

    /**
     * Get platform-specific quality preferences
     */
    get perPlatformQuality() {
      return preferences.perPlatformQuality;
    },

    /**
     * Get all preferences
     */
    get all() {
      return preferences;
    },

    /**
     * Get effective quality for a platform (platform-specific or global fallback)
     */
    getEffectiveQuality(platform: string): QualityLevel {
      return preferences.perPlatformQuality[platform] || preferences.preferredQuality;
    },

    /**
     * Set global preferred quality
     */
    setPreferredQuality(quality: QualityLevel) {
      preferences = { ...preferences, preferredQuality: quality };
      savePreferences(preferences);
    },

    /**
     * Set quality preference for a specific platform
     */
    setPlatformQuality(platform: string, quality: QualityLevel) {
      preferences = {
        ...preferences,
        perPlatformQuality: {
          ...preferences.perPlatformQuality,
          [platform]: quality,
        },
      };
      savePreferences(preferences);
    },

    /**
     * Clear platform-specific quality (use global instead)
     */
    clearPlatformQuality(platform: string) {
      const { [platform]: _, ...rest } = preferences.perPlatformQuality;
      preferences = {
        ...preferences,
        perPlatformQuality: rest,
      };
      savePreferences(preferences);
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
export const qualityPreferences = createQualityPreferencesStore();
