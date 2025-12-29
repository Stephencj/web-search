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

	// YouTube with cached stream - use direct
	if (video.platform === 'youtube' && hasStreamInfo) {
		return 'direct_stream';
	}

	// YouTube - use embed for instant start
	if (video.platform === 'youtube') {
		return 'embed';
	}

	// Other platforms - use embed
	if (video.embedConfig.supportsEmbed) {
		return 'embed';
	}

	// Fallback
	return 'embed';
}
