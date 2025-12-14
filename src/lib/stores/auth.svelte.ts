/**
 * Authentication Store
 * Manages user authentication state using Svelte 5 runes
 */

export interface User {
  id: number;
  username: string;
  display_name: string;
  avatar_color: string;
  has_pin: boolean;
}

export type AuthMode = 'open' | 'protected';

const TOKEN_KEY = 'session_token';

/**
 * Auth state using Svelte 5 runes
 */
function createAuthStore() {
  let user = $state<User | null>(null);
  let authMode = $state<AuthMode>('open');
  let isLoading = $state(true);
  let isInitialized = $state(false);

  /**
   * Initialize auth state on app load
   */
  async function init(): Promise<void> {
    if (isInitialized) return;

    isLoading = true;
    try {
      // Check if we have a stored token
      const token = localStorage.getItem(TOKEN_KEY);

      // Get auth mode and validate session in parallel
      const [modeResponse, meResponse] = await Promise.all([
        fetch('/api/auth/mode'),
        token ? fetch('/api/auth/me', {
          headers: { 'Authorization': `Bearer ${token}` }
        }) : Promise.resolve(null),
      ]);

      if (modeResponse.ok) {
        const modeData = await modeResponse.json();
        authMode = modeData.mode;
      }

      if (meResponse && meResponse.ok) {
        const meData = await meResponse.json();
        if (meData.authenticated && meData.user) {
          user = meData.user;
        } else {
          // Session invalid, clear token
          localStorage.removeItem(TOKEN_KEY);
        }
      }
    } catch (error) {
      console.error('Auth init error:', error);
    } finally {
      isLoading = false;
      isInitialized = true;
    }
  }

  /**
   * Login with username and optional PIN
   */
  async function login(username: string, pin?: string, deviceName?: string): Promise<{ success: boolean; message?: string }> {
    try {
      const response = await fetch('/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, pin, device_name: deviceName }),
      });

      const data = await response.json();

      if (data.success && data.token && data.user) {
        localStorage.setItem(TOKEN_KEY, data.token);
        user = data.user;
        return { success: true };
      }

      return { success: false, message: data.message || 'Login failed' };
    } catch (error) {
      console.error('Login error:', error);
      return { success: false, message: 'Network error' };
    }
  }

  /**
   * Logout current session
   */
  async function logout(): Promise<void> {
    try {
      const token = localStorage.getItem(TOKEN_KEY);
      if (token) {
        await fetch('/api/auth/logout', {
          method: 'POST',
          headers: { 'Authorization': `Bearer ${token}` },
        });
      }
    } catch {
      // Ignore logout errors
    } finally {
      localStorage.removeItem(TOKEN_KEY);
      user = null;
    }
  }

  /**
   * Refresh user data from server
   */
  async function refreshUser(): Promise<void> {
    const token = localStorage.getItem(TOKEN_KEY);
    if (!token) {
      user = null;
      return;
    }

    try {
      const response = await fetch('/api/auth/me', {
        headers: { 'Authorization': `Bearer ${token}` },
      });

      if (response.ok) {
        const data = await response.json();
        if (data.authenticated && data.user) {
          user = data.user;
          return;
        }
      }

      // Session invalid
      localStorage.removeItem(TOKEN_KEY);
      user = null;
    } catch {
      // Network error, keep current state
    }
  }

  /**
   * Get current auth token
   */
  function getToken(): string | null {
    return localStorage.getItem(TOKEN_KEY);
  }

  /**
   * Check if user needs to login
   */
  function needsLogin(): boolean {
    return authMode === 'protected' && !user;
  }

  return {
    // State (using getters for reactivity)
    get user() { return user; },
    get authMode() { return authMode; },
    get isLoading() { return isLoading; },
    get isInitialized() { return isInitialized; },
    get isAuthenticated() { return user !== null; },

    // Methods
    init,
    login,
    logout,
    refreshUser,
    getToken,
    needsLogin,
  };
}

// Singleton instance
export const auth = createAuthStore();

/**
 * Get authorization headers for API requests
 */
export function getAuthHeaders(): Record<string, string> {
  const token = localStorage.getItem(TOKEN_KEY);
  if (token) {
    return { 'Authorization': `Bearer ${token}` };
  }
  return {};
}
