/**
 * Media Viewer Store - manages state for in-app image/video viewing
 *
 * Supports three view modes:
 * - lightbox: Modal overlay (default)
 * - sidepanel: Slide-in panel from right
 * - fullpage: Full-page view (URL-based)
 */

import { browser } from '$app/environment';

export type ViewMode = 'lightbox' | 'sidepanel' | 'fullpage';

export type MediaType = 'image' | 'video';

export interface MediaItem {
  type: MediaType;
  url: string;           // Image URL or video URL
  thumbnailUrl?: string; // Video thumbnail
  title?: string;
  alt?: string;          // Image alt text
  pageUrl?: string;      // Source page URL
  pageTitle?: string;
  domain?: string;
  // Video-specific
  embedType?: 'direct' | 'youtube' | 'vimeo' | 'page_link';
  videoId?: string;
}

// Storage key for persisting view mode preference
const VIEW_MODE_KEY = 'mediaViewer.viewMode';

// Load saved preference from localStorage
function loadViewModePreference(): ViewMode {
  if (!browser) return 'lightbox';
  const saved = localStorage.getItem(VIEW_MODE_KEY);
  if (saved === 'lightbox' || saved === 'sidepanel' || saved === 'fullpage') {
    return saved;
  }
  return 'lightbox';
}

// Save preference to localStorage
function saveViewModePreference(mode: ViewMode): void {
  if (browser) {
    localStorage.setItem(VIEW_MODE_KEY, mode);
  }
}

// Create the media viewer store
function createMediaViewerStore() {
  // State using Svelte 5 runes pattern (but exported as regular object for cross-component use)
  let isOpen = $state(false);
  let items = $state<MediaItem[]>([]);
  let currentIndex = $state(0);
  let viewMode = $state<ViewMode>(loadViewModePreference());

  // Derived state
  const currentItem = $derived(items[currentIndex] ?? null);
  const hasNext = $derived(currentIndex < items.length - 1);
  const hasPrevious = $derived(currentIndex > 0);
  const totalItems = $derived(items.length);

  return {
    // Getters
    get isOpen() { return isOpen; },
    get items() { return items; },
    get currentIndex() { return currentIndex; },
    get viewMode() { return viewMode; },
    get currentItem() { return currentItem; },
    get hasNext() { return hasNext; },
    get hasPrevious() { return hasPrevious; },
    get totalItems() { return totalItems; },

    /**
     * Open the media viewer with a set of items
     * @param mediaItems - Array of media items to view
     * @param startIndex - Index to start at (default 0)
     * @param mode - Optional view mode override
     */
    open(mediaItems: MediaItem[], startIndex = 0, mode?: ViewMode) {
      if (mediaItems.length === 0) return;

      items = mediaItems;
      currentIndex = Math.max(0, Math.min(startIndex, mediaItems.length - 1));
      if (mode) {
        viewMode = mode;
        saveViewModePreference(mode);
      }
      isOpen = true;

      // Prevent body scroll when open
      if (browser && viewMode !== 'fullpage') {
        document.body.style.overflow = 'hidden';
      }
    },

    /**
     * Open a single media item
     */
    openSingle(item: MediaItem, mode?: ViewMode) {
      this.open([item], 0, mode);
    },

    /**
     * Close the media viewer
     */
    close() {
      isOpen = false;

      // Restore body scroll
      if (browser) {
        document.body.style.overflow = '';
      }
    },

    /**
     * Go to next item
     */
    next() {
      if (currentIndex < items.length - 1) {
        currentIndex++;
      }
    },

    /**
     * Go to previous item
     */
    previous() {
      if (currentIndex > 0) {
        currentIndex--;
      }
    },

    /**
     * Go to specific index
     */
    goTo(index: number) {
      if (index >= 0 && index < items.length) {
        currentIndex = index;
      }
    },

    /**
     * Change view mode
     */
    setViewMode(mode: ViewMode) {
      viewMode = mode;
      saveViewModePreference(mode);

      // Update body scroll based on new mode
      if (browser && isOpen) {
        if (mode === 'fullpage') {
          document.body.style.overflow = '';
        } else {
          document.body.style.overflow = 'hidden';
        }
      }
    },

    /**
     * Toggle between lightbox and sidepanel modes
     */
    toggleSidePanel() {
      const newMode = viewMode === 'sidepanel' ? 'lightbox' : 'sidepanel';
      this.setViewMode(newMode);
    },
  };
}

// Export singleton store instance
export const mediaViewer = createMediaViewerStore();
