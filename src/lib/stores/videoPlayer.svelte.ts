/**
 * Video Player Store
 * Manages global video playback state for modal and PiP modes
 */

import { api, type FeedItem, type DiscoverVideoResult, type SavedVideo } from '$lib/api/client';
import { buildEmbedConfig, type EmbedConfig } from '$lib/utils/embedUrl';

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
  sourceType?: 'feed' | 'saved' | 'discover';
  sourceId?: number; // Database ID for feed/saved items
  watchProgress?: number; // Existing progress in seconds
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

  // Return cached if available
  if (streamCache.has(cacheKey)) {
    return streamCache.get(cacheKey)!;
  }

  try {
    const response = await fetch(`/api/stream/${platform}/${videoId}`);
    if (response.ok) {
      const info = await response.json();
      streamCache.set(cacheKey, info);
      return info;
    }
  } catch {
    // Stream API not available
  }
  return null;
}

/**
 * Get cached stream info (does not fetch)
 */
export function getCachedStreamInfo(platform: string, videoId: string): StreamInfo | null {
  return streamCache.get(`${platform}:${videoId}`) || null;
}

/**
 * Pre-fetch stream info for upcoming videos
 */
export async function prefetchStreams(videos: VideoItem[]): Promise<void> {
  const fetchPromises = videos
    .filter(v => v.platform === 'youtube') // Only YouTube supports direct streams
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
     * Switch current video to PiP mode (preserves playhead via savePlayhead call)
     */
    switchToPiP() {
      if (currentVideo) {
        mode = 'pip';
      }
    },

    /**
     * Switch from PiP back to modal (preserves playhead via savePlayhead call)
     */
    switchToModal() {
      if (currentVideo) {
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
