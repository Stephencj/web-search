/**
 * Video Player Store
 * Manages global video playback state for modal and PiP modes
 */

import type { FeedItem, DiscoverVideoResult, SavedVideo } from '$lib/api/client';
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
}

export type PlayerMode = 'modal' | 'pip' | 'closed';

/**
 * Video player state using Svelte 5 runes
 */
function createVideoPlayerStore() {
  let currentVideo = $state<VideoItem | null>(null);
  let mode = $state<PlayerMode>('closed');

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

    /**
     * Open video in modal mode
     */
    openModal(video: VideoItem) {
      currentVideo = video;
      mode = 'modal';
    },

    /**
     * Switch current video to PiP mode
     */
    switchToPiP() {
      if (currentVideo) {
        mode = 'pip';
      }
    },

    /**
     * Switch from PiP back to modal
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
    },

    /**
     * Set a new video (keeps current mode if open)
     */
    setVideo(video: VideoItem) {
      currentVideo = video;
      if (mode === 'closed') {
        mode = 'modal';
      }
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
    channelName: item.channel?.name || null,
    channelUrl: item.channel?.channel_url || null,
    duration: item.duration_seconds,
    embedConfig,
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
