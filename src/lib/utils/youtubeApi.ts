/**
 * YouTube IFrame Player API integration
 *
 * Standard YouTube embeds (iframe src=) can't fire events due to cross-origin restrictions.
 * The YouTube IFrame Player API allows us to receive state change events including video end.
 */

// YouTube Player State constants
export const YT_PLAYER_STATE = {
  UNSTARTED: -1,
  ENDED: 0,
  PLAYING: 1,
  PAUSED: 2,
  BUFFERING: 3,
  CUED: 5,
} as const;

// Extend Window interface for YouTube API
declare global {
  interface Window {
    YT?: {
      Player: new (elementId: string | HTMLElement, config: YouTubePlayerConfig) => YouTubePlayer;
      PlayerState: typeof YT_PLAYER_STATE;
    };
    onYouTubeIframeAPIReady?: () => void;
  }
}

interface YouTubePlayerConfig {
  videoId?: string;
  width?: number | string;
  height?: number | string;
  playerVars?: {
    autoplay?: 0 | 1;
    controls?: 0 | 1;
    modestbranding?: 0 | 1;
    rel?: 0 | 1;
    enablejsapi?: 0 | 1;
    origin?: string;
    playsinline?: 0 | 1;
  };
  events?: {
    onReady?: (event: { target: YouTubePlayer }) => void;
    onStateChange?: (event: { data: number; target: YouTubePlayer }) => void;
    onError?: (event: { data: number }) => void;
  };
}

export interface YouTubePlayer {
  playVideo(): void;
  pauseVideo(): void;
  stopVideo(): void;
  seekTo(seconds: number, allowSeekAhead?: boolean): void;
  getPlayerState(): number;
  getCurrentTime(): number;
  getDuration(): number;
  getVideoUrl(): string;
  destroy(): void;
}

// Track API loading state
let apiLoadPromise: Promise<void> | null = null;
let apiLoaded = false;

/**
 * Load the YouTube IFrame Player API script
 * Returns a promise that resolves when the API is ready
 */
export function loadYouTubeAPI(): Promise<void> {
  // Already loaded
  if (apiLoaded && window.YT?.Player) {
    return Promise.resolve();
  }

  // Already loading
  if (apiLoadPromise) {
    return apiLoadPromise;
  }

  apiLoadPromise = new Promise((resolve, reject) => {
    // Check if already loaded by another script
    if (window.YT?.Player) {
      apiLoaded = true;
      resolve();
      return;
    }

    // Set up callback for when API is ready
    const previousCallback = window.onYouTubeIframeAPIReady;
    window.onYouTubeIframeAPIReady = () => {
      apiLoaded = true;
      console.log('[YouTube API] Loaded');
      previousCallback?.();
      resolve();
    };

    // Create and append the script
    const script = document.createElement('script');
    script.src = 'https://www.youtube.com/iframe_api';
    script.async = true;
    script.onerror = () => {
      apiLoadPromise = null;
      reject(new Error('Failed to load YouTube IFrame API'));
    };
    document.head.appendChild(script);

    // Timeout after 10 seconds
    setTimeout(() => {
      if (!apiLoaded) {
        apiLoadPromise = null;
        reject(new Error('YouTube IFrame API load timeout'));
      }
    }, 10000);
  });

  return apiLoadPromise;
}

/**
 * Check if YouTube API is available
 */
export function isYouTubeAPIReady(): boolean {
  return apiLoaded && !!window.YT?.Player;
}

/**
 * Create a YouTube player instance
 */
export function createYouTubePlayer(
  elementId: string | HTMLElement,
  videoId: string,
  callbacks: {
    onReady?: () => void;
    onStateChange?: (state: number) => void;
    onEnded?: () => void;
    onError?: (error: number) => void;
  }
): YouTubePlayer | null {
  if (!window.YT?.Player) {
    console.warn('[YouTube API] API not loaded');
    return null;
  }

  try {
    const player = new window.YT.Player(elementId, {
      videoId,
      width: '100%',
      height: '100%',
      playerVars: {
        autoplay: 1,
        controls: 1,
        modestbranding: 1,
        rel: 0,
        enablejsapi: 1,
        playsinline: 1,
      },
      events: {
        onReady: (event) => {
          console.log('[YouTube API] Player ready');
          callbacks.onReady?.();
        },
        onStateChange: (event) => {
          console.log('[YouTube API] State change:', event.data);
          callbacks.onStateChange?.(event.data);
          if (event.data === YT_PLAYER_STATE.ENDED) {
            callbacks.onEnded?.();
          }
        },
        onError: (event) => {
          console.warn('[YouTube API] Player error:', event.data);
          callbacks.onError?.(event.data);
        },
      },
    });

    return player;
  } catch (error) {
    console.error('[YouTube API] Failed to create player:', error);
    return null;
  }
}

/**
 * Extract video ID from a YouTube URL
 */
export function extractYouTubeVideoId(url: string): string | null {
  const patterns = [
    /(?:youtube\.com\/watch\?v=|youtu\.be\/|youtube\.com\/embed\/)([^&?/]+)/,
    /youtube\.com\/shorts\/([^&?/]+)/,
  ];

  for (const pattern of patterns) {
    const match = url.match(pattern);
    if (match?.[1]) {
      return match[1];
    }
  }

  return null;
}
