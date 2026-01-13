/**
 * Video Player Store
 * Manages global video playback state for modal and PiP modes
 */

import { api, type FeedItem, type DiscoverVideoResult, type SavedVideo, type CollectionItem } from '$lib/api/client';
import { buildEmbedConfig, type EmbedConfig } from '$lib/utils/embedUrl';
import {
  isMediaSessionSupported,
  updateMediaMetadata,
  updatePlaybackState,
  updatePositionState,
  registerMediaSessionHandlers,
  unregisterMediaSessionHandlers,
  clearMediaSession
} from '$lib/utils/mediaSession';
import { persistentStreamCache } from '$lib/stores/streamCache.svelte';

// Custom events for cross-component playback control
export const PLAYER_EVENTS = {
  PLAY: 'videoPlayer:play',
  PAUSE: 'videoPlayer:pause',
  SEEK: 'videoPlayer:seek',
  SEEK_TO: 'videoPlayer:seekTo',
} as const;

export interface VideoItem {
  platform: string;
  videoId: string;
  videoUrl: string;
  title: string;
  thumbnailUrl: string | null;
  channelName: string | null;
  channelUrl: string | null;
  duration: number | null;
  embedConfig: EmbedConfig;
  // For progress tracking
  sourceType?: 'feed' | 'saved' | 'discover' | 'offline' | 'collection';
  sourceId?: number; // Database ID for feed/saved/collection items
  collectionId?: number; // Collection ID for collection items
  watchProgress?: number; // Existing progress in seconds
  // Content type for mixed queues (video + audio)
  contentType?: 'video' | 'audio';
  // Podcast-specific fields
  audioUrl?: string | null;
  // Direct video stream URL (HLS, MP4, etc.)
  videoStreamUrl?: string | null;
  // Offline playback - direct blob URL
  offlineStreamUrl?: string | null;
  isOffline?: boolean;
  // Metadata for display
  description?: string | null;
  viewCount?: number | null;
  likeCount?: number | null;
  uploadDate?: string | null;
}

export interface StreamInfo {
  video_id: string;
  platform: string;
  title?: string;
  stream_url?: string;
  audio_url?: string;
  thumbnail_url?: string;
  duration_seconds?: number;
  is_authenticated: boolean;
  is_premium: boolean;
  quality?: string;
  format?: string;
  error?: string;
}

export type PlayerMode = 'modal' | 'pip' | 'closed';

// Stream cache for pre-fetched stream URLs
const streamCache = new Map<string, StreamInfo>();

/**
 * Fetch and cache stream info for a video
 */
async function fetchStreamInfo(platform: string, videoId: string): Promise<StreamInfo | null> {
  const cacheKey = `${platform}:${videoId}`;

  // Return cached if available (in-memory)
  if (streamCache.has(cacheKey)) {
    return streamCache.get(cacheKey)!;
  }

  // Check persistent cache
  const persistent = persistentStreamCache.get(platform, videoId);
  if (persistent) {
    streamCache.set(cacheKey, persistent);
    return persistent;
  }

  try {
    const response = await fetch(`/api/stream/${platform}/${videoId}`);
    if (response.ok) {
      const info = await response.json();
      // Cache in both memory and persistent storage
      streamCache.set(cacheKey, info);
      persistentStreamCache.set(platform, videoId, info);
      return info;
    }
  } catch {
    // Stream API not available
  }
  return null;
}

/**
 * Get cached stream info (does not fetch)
 * Checks both in-memory cache and persistent cache
 */
export function getCachedStreamInfo(platform: string, videoId: string): StreamInfo | null {
  const cacheKey = `${platform}:${videoId}`;

  // Check in-memory cache first (faster)
  if (streamCache.has(cacheKey)) {
    return streamCache.get(cacheKey)!;
  }

  // Check persistent cache (survives page reload)
  const persistent = persistentStreamCache.get(platform, videoId);
  if (persistent) {
    // Promote to in-memory cache for faster subsequent access
    streamCache.set(cacheKey, persistent);
    return persistent;
  }

  return null;
}

// Platforms that support stream extraction via yt-dlp
const STREAM_PLATFORMS = ['youtube', 'rumble', 'odysee', 'bitchute', 'dailymotion'];

/**
 * Pre-fetch stream info for upcoming videos
 */
export async function prefetchStreams(videos: VideoItem[]): Promise<void> {
  const fetchPromises = videos
    .filter(v => STREAM_PLATFORMS.includes(v.platform))
    .map(v => fetchStreamInfo(v.platform, v.videoId));

  await Promise.allSettled(fetchPromises);
}

/**
 * Video player state using Svelte 5 runes
 */
function createVideoPlayerStore() {
  let currentVideo = $state<VideoItem | null>(null);
  let mode = $state<PlayerMode>('closed');
  let queue = $state<VideoItem[]>([]);
  let currentIndex = $state<number>(-1);
  // Track playhead position for seamless mode switching
  let savedPlayhead = $state<number>(0);
  // Unique key to force player re-initialization on video change
  let videoKey = $state<number>(0);
  // Global playback state
  let isPlaying = $state<boolean>(false);
  let currentTime = $state<number>(0);
  let duration = $state<number>(0);
  // Flag to indicate playback should continue after mode switch
  let shouldResumePlayback = $state<boolean>(false);
  // Track native browser PiP state (iOS Safari)
  let isNativePiPActive = $state<boolean>(false);
  // When true, modal is hidden but video element kept alive for native PiP
  let isHiddenForNativePiP = $state<boolean>(false);

  // Helper to dispatch custom events for player control
  function dispatchPlayerEvent(eventName: string, detail?: unknown) {
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent(eventName, { detail }));
    }
  }

  // Initialize media session handlers
  function initMediaSession() {
    if (!isMediaSessionSupported()) return;

    registerMediaSessionHandlers({
      onPlay: () => {
        dispatchPlayerEvent(PLAYER_EVENTS.PLAY);
      },
      onPause: () => {
        dispatchPlayerEvent(PLAYER_EVENTS.PAUSE);
      },
      onSeekBackward: (offset = 10) => {
        dispatchPlayerEvent(PLAYER_EVENTS.SEEK, { offset: -offset });
      },
      onSeekForward: (offset = 10) => {
        dispatchPlayerEvent(PLAYER_EVENTS.SEEK, { offset });
      },
      onSeekTo: (time) => {
        dispatchPlayerEvent(PLAYER_EVENTS.SEEK_TO, { time });
      },
      onPreviousTrack: () => {
        if (queue.length > 0 && currentIndex > 0) {
          currentIndex--;
          currentVideo = queue[currentIndex];
          savedPlayhead = 0;
          videoKey++;
          shouldResumePlayback = true;
        }
      },
      onNextTrack: () => {
        if (queue.length > 0 && currentIndex < queue.length - 1) {
          currentIndex++;
          currentVideo = queue[currentIndex];
          savedPlayhead = 0;
          videoKey++;
          shouldResumePlayback = true;
        }
      },
      onStop: () => {
        mode = 'closed';
        currentVideo = null;
        isPlaying = false;
        clearMediaSession();
      }
    });
  }

  return {
    get currentVideo() {
      return currentVideo;
    },
    get mode() {
      return mode;
    },
    get isOpen() {
      return mode !== 'closed' && currentVideo !== null;
    },
    get isModal() {
      return mode === 'modal';
    },
    get isPiP() {
      return mode === 'pip';
    },
    get queue() {
      return queue;
    },
    get currentIndex() {
      return currentIndex;
    },
    get hasNext() {
      return queue.length > 0 && currentIndex < queue.length - 1;
    },
    get hasPrevious() {
      return queue.length > 0 && currentIndex > 0;
    },
    get queueLength() {
      return queue.length;
    },
    get savedPlayhead() {
      return savedPlayhead;
    },
    get videoKey() {
      return videoKey;
    },
    get isPlaying() {
      return isPlaying;
    },
    get currentTime() {
      return currentTime;
    },
    get duration() {
      return duration;
    },
    get shouldResumePlayback() {
      return shouldResumePlayback;
    },
    get isNativePiPActive() {
      return isNativePiPActive;
    },
    get isHiddenForNativePiP() {
      return isHiddenForNativePiP;
    },

    /**
     * Initialize media session (call once on app mount)
     */
    initMediaSession,

    /**
     * Set native PiP state (called by NativePiPTracker)
     */
    setNativePiPActive(active: boolean) {
      isNativePiPActive = active;
      // Reset hidden state when native PiP exits
      if (!active) {
        isHiddenForNativePiP = false;
      }
    },

    /**
     * Hide modal but keep video alive for native PiP
     */
    setHiddenForNativePiP(hidden: boolean) {
      isHiddenForNativePiP = hidden;
    },

    /**
     * Update playback state (called by active player)
     */
    setPlaybackState(playing: boolean) {
      isPlaying = playing;
      updatePlaybackState(playing ? 'playing' : 'paused');
    },

    /**
     * Update current time and duration (called by active player)
     */
    updatePosition(time: number, dur: number) {
      currentTime = time;
      duration = dur;
      if (dur > 0) {
        updatePositionState(dur, time);
      }
    },

    /**
     * Update media session metadata when video changes
     */
    updateMediaMetadata() {
      if (currentVideo) {
        updateMediaMetadata(currentVideo);
      }
    },

    /**
     * Clear the shouldResumePlayback flag after player handles it
     */
    clearShouldResumePlayback() {
      shouldResumePlayback = false;
    },

    /**
     * Global play command - dispatches event for active player
     */
    play() {
      dispatchPlayerEvent(PLAYER_EVENTS.PLAY);
    },

    /**
     * Global pause command - dispatches event for active player
     */
    pause() {
      dispatchPlayerEvent(PLAYER_EVENTS.PAUSE);
    },

    /**
     * Global seek command - dispatches event for active player
     * @param offset - seconds to seek (positive = forward, negative = backward)
     */
    seek(offset: number) {
      dispatchPlayerEvent(PLAYER_EVENTS.SEEK, { offset });
    },

    /**
     * Global seekTo command - dispatches event for active player
     * @param time - absolute time in seconds
     */
    seekTo(time: number) {
      dispatchPlayerEvent(PLAYER_EVENTS.SEEK_TO, { time });
    },

    /**
     * Get the next N videos in the queue for pre-fetching
     */
    getUpcomingVideos(count: number = 2): VideoItem[] {
      if (queue.length === 0 || currentIndex < 0) return [];
      const start = currentIndex + 1;
      const end = Math.min(start + count, queue.length);
      return queue.slice(start, end);
    },

    /**
     * Save current playhead position (call before switching modes)
     */
    savePlayhead(time: number) {
      savedPlayhead = time;
    },

    /**
     * Clear saved playhead (call after player resumes at saved position)
     */
    clearSavedPlayhead() {
      savedPlayhead = 0;
    },

    /**
     * Open video in modal mode
     */
    openModal(video: VideoItem) {
      currentVideo = video;
      mode = 'modal';
      savedPlayhead = 0;
      videoKey++;
      // Clear queue when opening single video
      queue = [];
      currentIndex = -1;
    },

    /**
     * Open video with a queue (playlist mode)
     */
    openWithQueue(videos: VideoItem[], startIndex: number = 0) {
      if (videos.length === 0) return;
      queue = [...videos];
      currentIndex = Math.max(0, Math.min(startIndex, videos.length - 1));
      currentVideo = queue[currentIndex];
      mode = 'modal';
      savedPlayhead = 0;
      videoKey++;
    },

    /**
     * Play next video in queue
     */
    playNext() {
      if (queue.length > 0 && currentIndex < queue.length - 1) {
        currentIndex++;
        currentVideo = queue[currentIndex];
        savedPlayhead = 0;
        videoKey++;
        return true;
      }
      return false;
    },

    /**
     * Play previous video in queue
     */
    playPrevious() {
      if (queue.length > 0 && currentIndex > 0) {
        currentIndex--;
        currentVideo = queue[currentIndex];
        savedPlayhead = 0;
        videoKey++;
        return true;
      }
      return false;
    },

    /**
     * Jump to specific video in queue by index
     */
    goToIndex(index: number) {
      if (index >= 0 && index < queue.length && index !== currentIndex) {
        currentIndex = index;
        currentVideo = queue[currentIndex];
        savedPlayhead = 0;
        videoKey++;
        shouldResumePlayback = true;
        return true;
      }
      return false;
    },

    /**
     * Switch current video to PiP mode (preserves playhead via savePlayhead call)
     */
    switchToPiP() {
      if (currentVideo) {
        // Remember if video was playing so PiP can resume
        shouldResumePlayback = isPlaying;
        mode = 'pip';
      }
    },

    /**
     * Switch from PiP back to modal (preserves playhead via savePlayhead call)
     */
    switchToModal() {
      if (currentVideo) {
        // Remember if video was playing so modal can resume
        shouldResumePlayback = isPlaying;
        mode = 'modal';
      }
    },

    /**
     * Close the player completely
     */
    close() {
      mode = 'closed';
      currentVideo = null;
      queue = [];
      currentIndex = -1;
      savedPlayhead = 0;
      isPlaying = false;
      shouldResumePlayback = false;
      currentTime = 0;
      duration = 0;
      clearMediaSession();
    },

    /**
     * Set a new video (keeps current mode if open)
     */
    setVideo(video: VideoItem) {
      currentVideo = video;
      savedPlayhead = 0;
      videoKey++;
      if (mode === 'closed') {
        mode = 'modal';
      }
    },

    /**
     * Clear the queue but keep current video
     */
    clearQueue() {
      queue = [];
      currentIndex = -1;
    },
  };
}

// Global singleton store
export const videoPlayer = createVideoPlayerStore();

/**
 * Convert FeedItem to VideoItem
 */
export function feedItemToVideoItem(item: FeedItem): VideoItem {
  const isPodcast = item.platform === 'podcast';
  const isRedbar = item.platform === 'redbar';
  const embedConfig = buildEmbedConfig(item.platform, item.video_id, item.video_url);
  return {
    platform: item.platform,
    videoId: item.video_id,
    videoUrl: item.video_url,
    title: item.title,
    thumbnailUrl: item.thumbnail_url,
    channelName: item.channel_name || null,
    channelUrl: null, // FeedItem doesn't have channel URL
    duration: item.duration_seconds,
    embedConfig,
    sourceType: 'feed',
    sourceId: item.id,
    watchProgress: item.watch_progress_seconds ?? undefined,
    // Red Bar defaults to video content, podcasts to audio
    contentType: isPodcast ? 'audio' : 'video',
    audioUrl: item.audio_url,
    videoStreamUrl: item.video_stream_url,
    // Metadata for display
    description: item.description,
    viewCount: item.view_count,
    likeCount: item.like_count,
    uploadDate: item.upload_date,
  };
}

/**
 * Convert DiscoverVideoResult to VideoItem
 */
export function discoverVideoToVideoItem(video: DiscoverVideoResult): VideoItem {
  const embedConfig = buildEmbedConfig(video.platform, video.video_id, video.video_url);
  return {
    platform: video.platform,
    videoId: video.video_id,
    videoUrl: video.video_url,
    title: video.title,
    thumbnailUrl: video.thumbnail_url,
    channelName: video.channel_name,
    channelUrl: video.channel_url,
    duration: video.duration_seconds,
    embedConfig,
    sourceType: 'discover',
    // Discover videos don't have progress tracking until saved
  };
}

/**
 * Convert SavedVideo to VideoItem
 */
export function savedVideoToVideoItem(video: SavedVideo): VideoItem {
  const embedConfig = buildEmbedConfig(video.platform, video.video_id, video.video_url);
  return {
    platform: video.platform,
    videoId: video.video_id,
    videoUrl: video.video_url,
    title: video.title,
    thumbnailUrl: video.thumbnail_url,
    channelName: video.channel_name,
    channelUrl: video.channel_url,
    duration: video.duration_seconds,
    embedConfig,
    sourceType: 'saved',
    sourceId: video.id,
    watchProgress: video.watch_progress_seconds ?? undefined,
  };
}

/**
 * Format duration in HH:MM:SS or MM:SS
 */
export function formatDuration(seconds: number | null): string {
  if (!seconds) return '';
  const hrs = Math.floor(seconds / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  const secs = seconds % 60;
  if (hrs > 0) {
    return `${hrs}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }
  return `${mins}:${secs.toString().padStart(2, '0')}`;
}

/**
 * Open a feed video with fresh progress data from the API.
 * Fetches the latest watch_progress_seconds to ensure correct resume position.
 */
export async function openFeedVideo(item: FeedItem): Promise<void> {
  try {
    // Fetch fresh item data with latest progress
    const freshItem = await api.getFeedItem(item.id);
    const videoItem = feedItemToVideoItem(freshItem);
    videoPlayer.openModal(videoItem);
  } catch {
    // Fallback to cached data if API fails
    const videoItem = feedItemToVideoItem(item);
    videoPlayer.openModal(videoItem);
  }
}

/**
 * Open a saved video with fresh progress data from the API.
 * Fetches the latest watch_progress_seconds to ensure correct resume position.
 */
export async function openSavedVideo(video: SavedVideo): Promise<void> {
  try {
    // Fetch fresh video data with latest progress
    const freshVideo = await api.getSavedVideo(video.id);
    const videoItem = savedVideoToVideoItem(freshVideo);
    videoPlayer.openModal(videoItem);
  } catch {
    // Fallback to cached data if API fails
    const videoItem = savedVideoToVideoItem(video);
    videoPlayer.openModal(videoItem);
  }
}

/**
 * Convert CollectionItem to VideoItem
 * Handles video, podcast_episode, and image (as video fallback) item types
 */
export function collectionItemToVideoItem(item: CollectionItem, collectionId: number): VideoItem {
  // Check both item_type and embed_type for podcast detection (handles legacy saves)
  const isPodcast = item.item_type === 'podcast_episode' || item.embed_type === 'podcast';

  // Determine platform from embed_type
  let platform = 'other';
  if (item.embed_type === 'youtube') platform = 'youtube';
  else if (item.embed_type === 'vimeo') platform = 'vimeo';
  else if (item.embed_type === 'rumble') platform = 'rumble';
  else if (item.embed_type === 'redbar') platform = 'redbar';
  else if (isPodcast) platform = 'podcast';

  const embedConfig = buildEmbedConfig(platform, item.video_id || '', item.url);

  return {
    platform,
    videoId: item.video_id || '',
    videoUrl: item.url,
    title: item.title || 'Untitled',
    thumbnailUrl: item.thumbnail_url,
    channelName: item.domain || null,
    channelUrl: null,
    duration: null,
    embedConfig,
    contentType: isPodcast ? 'audio' : 'video',
    // For podcast episodes, the URL is the audio file
    audioUrl: isPodcast ? item.url : null,
    // Track progress for collection items
    sourceType: 'collection',
    sourceId: item.id,
    collectionId,
    watchProgress: item.watch_progress_seconds ?? undefined,
  };
}

/**
 * Create VideoItem for offline playback
 * Used when playing downloaded content from IndexedDB
 */
export function createOfflineVideoItem(
  platform: string,
  videoId: string,
  title: string,
  thumbnailUrl: string | null,
  duration: number | null,
  offlineStreamUrl: string,
  mediaType: 'video' | 'podcast_episode' = 'video'
): VideoItem {
  const isPodcast = mediaType === 'podcast_episode' || platform === 'podcast';

  // For offline content, we don't need a valid embed URL
  const embedConfig: EmbedConfig = {
    platform: platform,
    supportsEmbed: false,
    embedUrl: null,
    fallbackReason: 'Playing from offline storage',
  };

  return {
    platform,
    videoId,
    videoUrl: '', // No original URL needed for offline
    title,
    thumbnailUrl,
    channelName: null,
    channelUrl: null,
    duration,
    embedConfig,
    sourceType: 'offline',
    contentType: isPodcast ? 'audio' : 'video',
    offlineStreamUrl,
    isOffline: true,
    audioUrl: isPodcast ? offlineStreamUrl : null,
  };
}
