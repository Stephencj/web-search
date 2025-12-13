/**
 * Theme Store
 * Manages application theme preference (light/dark/auto)
 * Persists to localStorage and applies via data-theme attribute
 */

export type Theme = 'light' | 'dark' | 'auto';

const STORAGE_KEY = 'websearch-theme';

/**
 * Get initial theme from localStorage or default to 'auto'
 */
function getInitialTheme(): Theme {
  if (typeof window === 'undefined') return 'auto';

  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored === 'light' || stored === 'dark' || stored === 'auto') {
    return stored;
  }
  return 'auto';
}

/**
 * Apply theme to document
 */
function applyTheme(theme: Theme) {
  if (typeof document === 'undefined') return;
  document.documentElement.dataset.theme = theme;
}

/**
 * Get the effective theme (resolves 'auto' to actual light/dark)
 */
function getEffectiveTheme(theme: Theme): 'light' | 'dark' {
  if (theme !== 'auto') return theme;

  if (typeof window === 'undefined') return 'light';
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

/**
 * Theme store using Svelte 5 runes
 */
function createThemeStore() {
  let theme = $state<Theme>(getInitialTheme());

  // Apply initial theme
  if (typeof window !== 'undefined') {
    applyTheme(theme);
  }

  return {
    get current() {
      return theme;
    },

    get effective() {
      return getEffectiveTheme(theme);
    },

    get isDark() {
      return getEffectiveTheme(theme) === 'dark';
    },

    get isLight() {
      return getEffectiveTheme(theme) === 'light';
    },

    get isAuto() {
      return theme === 'auto';
    },

    /**
     * Set theme preference
     */
    setTheme(value: Theme) {
      theme = value;
      localStorage.setItem(STORAGE_KEY, value);
      applyTheme(value);
    },

    /**
     * Toggle between light and dark (skips auto)
     */
    toggle() {
      const newTheme = getEffectiveTheme(theme) === 'dark' ? 'light' : 'dark';
      this.setTheme(newTheme);
    },

    /**
     * Cycle through: auto -> light -> dark -> auto
     */
    cycle() {
      const order: Theme[] = ['auto', 'light', 'dark'];
      const currentIndex = order.indexOf(theme);
      const nextIndex = (currentIndex + 1) % order.length;
      this.setTheme(order[nextIndex]);
    },

    /**
     * Initialize theme on client-side mount
     * Call this in +layout.svelte onMount
     */
    init() {
      if (typeof window === 'undefined') return;

      // Apply stored theme
      applyTheme(theme);

      // Listen for system theme changes when in auto mode
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
      const handleChange = () => {
        if (theme === 'auto') {
          // Force re-render by triggering reactivity
          applyTheme('auto');
        }
      };

      mediaQuery.addEventListener('change', handleChange);

      return () => {
        mediaQuery.removeEventListener('change', handleChange);
      };
    },
  };
}

// Global singleton store
export const themeStore = createThemeStore();
