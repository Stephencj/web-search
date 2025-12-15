/**
 * Media Session API Integration
 *
 * Provides lock screen controls, notification controls, and background playback
 * support across browsers. Maintains persistent connection even when visual
 * player modes change.
 */

import type { VideoItem } from '$lib/stores/videoPlayer.svelte';

export interface MediaSessionHandlers {
  onPlay?: () => void;
  onPause?: () => void;
  onSeekBackward?: (seekOffset?: number) => void;
  onSeekForward?: (seekOffset?: number) => void;
  onSeekTo?: (seekTime: number) => void;
  onPreviousTrack?: () => void;
  onNextTrack?: () => void;
  onStop?: () => void;
}

// Track if handlers are registered
let handlersRegistered = false;
let currentHandlers: MediaSessionHandlers = {};

/**
 * Check if Media Session API is available
 */
export function isMediaSessionSupported(): boolean {
  return 'mediaSession' in navigator;
}

/**
 * Update the media session metadata (title, artist, artwork)
 */
export function updateMediaMetadata(video: VideoItem | null): void {
  if (!isMediaSessionSupported() || !video) {
    return;
  }

  try {
    const artwork: MediaImage[] = [];

    if (video.thumbnailUrl) {
      // Add multiple sizes for different contexts
      artwork.push(
        { src: video.thumbnailUrl, sizes: '96x96', type: 'image/jpeg' },
        { src: video.thumbnailUrl, sizes: '128x128', type: 'image/jpeg' },
        { src: video.thumbnailUrl, sizes: '192x192', type: 'image/jpeg' },
        { src: video.thumbnailUrl, sizes: '256x256', type: 'image/jpeg' },
        { src: video.thumbnailUrl, sizes: '384x384', type: 'image/jpeg' },
        { src: video.thumbnailUrl, sizes: '512x512', type: 'image/jpeg' }
      );
    }

    navigator.mediaSession.metadata = new MediaMetadata({
      title: video.title,
      artist: video.channelName || 'Unknown',
      album: video.platform.charAt(0).toUpperCase() + video.platform.slice(1),
      artwork
    });

    console.log('[MediaSession] Metadata updated:', video.title);
  } catch (e) {
    console.warn('[MediaSession] Failed to update metadata:', e);
  }
}

/**
 * Update the playback state (playing/paused/none)
 */
export function updatePlaybackState(state: 'playing' | 'paused' | 'none'): void {
  if (!isMediaSessionSupported()) {
    return;
  }

  try {
    navigator.mediaSession.playbackState = state;
    console.log('[MediaSession] Playback state:', state);
  } catch (e) {
    console.warn('[MediaSession] Failed to update playback state:', e);
  }
}

/**
 * Update position state for seek bar display
 */
export function updatePositionState(
  duration: number,
  position: number,
  playbackRate: number = 1
): void {
  if (!isMediaSessionSupported()) {
    return;
  }

  try {
    // Only update if we have valid values
    if (duration > 0 && position >= 0 && position <= duration) {
      navigator.mediaSession.setPositionState({
        duration,
        position,
        playbackRate
      });
    }
  } catch (e) {
    // Position state not supported in all browsers
  }
}

/**
 * Register media session action handlers
 * These handle lock screen/notification control interactions
 */
export function registerMediaSessionHandlers(handlers: MediaSessionHandlers): void {
  if (!isMediaSessionSupported()) {
    return;
  }

  currentHandlers = handlers;

  try {
    // Play action
    if (handlers.onPlay) {
      navigator.mediaSession.setActionHandler('play', () => {
        console.log('[MediaSession] Play action triggered');
        currentHandlers.onPlay?.();
      });
    }

    // Pause action
    if (handlers.onPause) {
      navigator.mediaSession.setActionHandler('pause', () => {
        console.log('[MediaSession] Pause action triggered');
        currentHandlers.onPause?.();
      });
    }

    // Seek backward (usually -10s)
    if (handlers.onSeekBackward) {
      navigator.mediaSession.setActionHandler('seekbackward', (details) => {
        console.log('[MediaSession] Seek backward:', details?.seekOffset);
        currentHandlers.onSeekBackward?.(details?.seekOffset ?? 10);
      });
    }

    // Seek forward (usually +10s)
    if (handlers.onSeekForward) {
      navigator.mediaSession.setActionHandler('seekforward', (details) => {
        console.log('[MediaSession] Seek forward:', details?.seekOffset);
        currentHandlers.onSeekForward?.(details?.seekOffset ?? 10);
      });
    }

    // Seek to specific position
    if (handlers.onSeekTo) {
      navigator.mediaSession.setActionHandler('seekto', (details) => {
        if (details?.seekTime !== undefined) {
          console.log('[MediaSession] Seek to:', details.seekTime);
          currentHandlers.onSeekTo?.(details.seekTime);
        }
      });
    }

    // Previous track (if queue exists)
    if (handlers.onPreviousTrack) {
      navigator.mediaSession.setActionHandler('previoustrack', () => {
        console.log('[MediaSession] Previous track');
        currentHandlers.onPreviousTrack?.();
      });
    }

    // Next track (if queue exists)
    if (handlers.onNextTrack) {
      navigator.mediaSession.setActionHandler('nexttrack', () => {
        console.log('[MediaSession] Next track');
        currentHandlers.onNextTrack?.();
      });
    }

    // Stop action
    if (handlers.onStop) {
      navigator.mediaSession.setActionHandler('stop', () => {
        console.log('[MediaSession] Stop action');
        currentHandlers.onStop?.();
      });
    }

    handlersRegistered = true;
    console.log('[MediaSession] Handlers registered');
  } catch (e) {
    console.warn('[MediaSession] Failed to register handlers:', e);
  }
}

/**
 * Unregister all media session handlers
 */
export function unregisterMediaSessionHandlers(): void {
  if (!isMediaSessionSupported()) {
    return;
  }

  try {
    const actions: MediaSessionAction[] = [
      'play', 'pause', 'seekbackward', 'seekforward',
      'seekto', 'previoustrack', 'nexttrack', 'stop'
    ];

    for (const action of actions) {
      try {
        navigator.mediaSession.setActionHandler(action, null);
      } catch {
        // Some actions may not be supported
      }
    }

    handlersRegistered = false;
    currentHandlers = {};
    console.log('[MediaSession] Handlers unregistered');
  } catch (e) {
    console.warn('[MediaSession] Failed to unregister handlers:', e);
  }
}

/**
 * Clear media session metadata and state
 */
export function clearMediaSession(): void {
  if (!isMediaSessionSupported()) {
    return;
  }

  try {
    navigator.mediaSession.metadata = null;
    navigator.mediaSession.playbackState = 'none';
    console.log('[MediaSession] Cleared');
  } catch (e) {
    console.warn('[MediaSession] Failed to clear:', e);
  }
}

/**
 * Update handlers without re-registering (for when callbacks change)
 */
export function updateHandlers(handlers: Partial<MediaSessionHandlers>): void {
  currentHandlers = { ...currentHandlers, ...handlers };
}
