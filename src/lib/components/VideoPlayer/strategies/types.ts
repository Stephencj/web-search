/**
 * Playback Strategy Types
 *
 * Defines the interface that all playback strategies must implement.
 */

import type { VideoItem, StreamInfo } from '$lib/stores/videoPlayer.svelte';

export interface PlaybackState {
	isPlaying: boolean;
	currentTime: number;
	duration: number;
	buffered: number;
	volume: number;
	playbackRate: number;
	isReady: boolean;
	isLoading: boolean;
	error: string | null;
}

export interface PlaybackCallbacks {
	onReady?: () => void;
	onPlay?: () => void;
	onPause?: () => void;
	onEnded?: () => void;
	onError?: (error: string) => void;
	onTimeUpdate?: (time: number, duration: number) => void;
	onBuffering?: () => void;
}

export interface StrategyProps {
	video: VideoItem;
	startTime?: number;
	autoplay?: boolean;
	callbacks?: PlaybackCallbacks;
	streamInfo?: StreamInfo | null;
}

export type StrategyType = 'embed' | 'youtube_api' | 'direct_stream' | 'audio' | 'hls';

// Platforms that support stream extraction via yt-dlp
const STREAM_PLATFORMS = ['youtube', 'rumble', 'odysee', 'bitchute', 'dailymotion'];

/**
 * Get the best strategy for a video
 */
export function getBestStrategy(video: VideoItem, hasStreamInfo: boolean, streamInfo?: StreamInfo | null): StrategyType {
	// Red Bar with HLS video stream - use HLS strategy for video playback
	// Check both video.videoStreamUrl (from feed items) and streamInfo (from API fetch)
	const hasHlsStream = video.videoStreamUrl || streamInfo?.stream_url?.includes('.m3u8');
	if (video.platform === 'redbar' && hasHlsStream) {
		return 'hls';
	}

	// Red Bar without video stream - fallback to audio
	if (video.platform === 'redbar') {
		return 'audio';
	}

	// Podcast content - audio strategy
	if (video.contentType === 'audio' || video.platform === 'podcast') {
		return 'audio';
	}

	// Platforms with stream extraction support - use direct stream when available
	if (STREAM_PLATFORMS.includes(video.platform) && hasStreamInfo && streamInfo?.stream_url) {
		return 'direct_stream';
	}

	// Platforms with stream extraction but no cached stream yet - use embed for instant start
	if (STREAM_PLATFORMS.includes(video.platform) && video.embedConfig.supportsEmbed) {
		return 'embed';
	}

	// Other platforms - use embed
	if (video.embedConfig.supportsEmbed) {
		return 'embed';
	}

	// Fallback
	return 'embed';
}
