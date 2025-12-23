/**
 * Playback State Machine
 *
 * Manages video playback lifecycle with clean state transitions.
 * Integrates with videoPlayer store for mode/queue management.
 *
 * States:
 * - idle: No video loaded
 * - embed_loading: Embed iframe is loading
 * - embed_playing: Playing via embed
 * - stream_extracting: Background yt-dlp extraction in progress
 * - stream_ready: Direct stream available, ready to upgrade
 * - upgrading: Transitioning from embed to direct stream
 * - direct_playing: Playing via native video element
 * - upgrade_failed: Direct stream failed, staying on embed
 * - error: Playback error occurred
 */

import type { VideoItem, StreamInfo } from './videoPlayer.svelte';
import { streamCache, fetchStreamInfo, type CachePriority } from './streamCacheV2.svelte';
import { prefetchQueueVideos } from './prefetchQueue.svelte';

export type PlaybackLifecycleState =
	| 'idle'
	| 'embed_loading'
	| 'embed_playing'
	| 'stream_extracting'
	| 'stream_ready'
	| 'upgrading'
	| 'direct_playing'
	| 'upgrade_failed'
	| 'error';

export type PlaybackStrategyType = 'embed' | 'youtube_api' | 'direct_stream' | 'audio' | 'none';

export interface PlaybackCapabilities {
	canEmbed: boolean;
	canDirectStream: boolean;
	canUseYouTubeApi: boolean;
	canDetectEnd: boolean;
	hasAds: boolean;
}

interface UpgradeOpportunity {
	type: 'pause' | 'buffer' | 'background' | 'preloaded' | 'manual';
	timestamp: number;
}

function createPlayerStateStore() {
	// Lifecycle state
	let lifecycleState = $state<PlaybackLifecycleState>('idle');

	// Strategy
	let activeStrategy = $state<PlaybackStrategyType>('none');
	let preferredStrategy = $state<PlaybackStrategyType>('embed'); // User preference

	// Stream info
	let streamInfo = $state<StreamInfo | null>(null);
	let streamError = $state<string | null>(null);

	// Upgrade tracking
	let upgradeAttempted = $state<boolean>(false);
	let upgradeOpportunities = $state<UpgradeOpportunity[]>([]);
	let isUpgradeReady = $state<boolean>(false);

	// Playback position (for seamless upgrades)
	let lastKnownPosition = $state<number>(0);
	let wasPlayingBeforeUpgrade = $state<boolean>(false);

	// Current video reference
	let currentVideoRef = $state<VideoItem | null>(null);

	// Extraction abort controller
	let extractionAbort: AbortController | null = null;

	/**
	 * Get platform capabilities
	 */
	function getCapabilities(platform: string): PlaybackCapabilities {
		switch (platform) {
			case 'youtube':
				return {
					canEmbed: true,
					canDirectStream: true,
					canUseYouTubeApi: true,
					canDetectEnd: true,
					hasAds: true
				};
			case 'rumble':
			case 'odysee':
			case 'bitchute':
			case 'dailymotion':
				return {
					canEmbed: true,
					canDirectStream: false,
					canUseYouTubeApi: false,
					canDetectEnd: false,
					hasAds: false
				};
			case 'redbar':
			case 'podcast':
				return {
					canEmbed: false,
					canDirectStream: true, // Direct audio URL
					canUseYouTubeApi: false,
					canDetectEnd: true,
					hasAds: false
				};
			default:
				return {
					canEmbed: false,
					canDirectStream: false,
					canUseYouTubeApi: false,
					canDetectEnd: false,
					hasAds: false
				};
		}
	}

	/**
	 * Determine best initial strategy for a video
	 */
	function determineInitialStrategy(video: VideoItem): PlaybackStrategyType {
		const caps = getCapabilities(video.platform);

		// Audio content uses audio strategy
		if (video.platform === 'redbar' || video.platform === 'podcast') {
			return 'audio';
		}

		// Check if we have a cached stream (instant direct playback)
		if (caps.canDirectStream && streamCache.has(video.platform, video.videoId)) {
			return 'direct_stream';
		}

		// YouTube: prefer embed for instant start, upgrade later
		// (unless user prefers YouTube API for queue detection)
		if (caps.canEmbed) {
			return 'embed';
		}

		return 'none';
	}

	/**
	 * Start background stream extraction
	 */
	async function startExtraction(video: VideoItem, priority: CachePriority = 'high'): Promise<void> {
		// Only YouTube supports extraction
		if (video.platform !== 'youtube') return;

		// Already cached?
		const cached = streamCache.getSync(video.platform, video.videoId);
		if (cached) {
			streamInfo = cached;
			lifecycleState =
				lifecycleState === 'embed_playing' ? 'stream_ready' : lifecycleState;
			isUpgradeReady = true;
			return;
		}

		// Already extracting?
		const state = streamCache.getExtractionStatus(video.platform, video.videoId);
		if (state?.status === 'extracting') {
			lifecycleState = 'stream_extracting';
			// Wait for existing extraction
			if (state.promise) {
				const result = await state.promise;
				if (result) {
					streamInfo = result;
					lifecycleState =
						lifecycleState === 'stream_extracting' ? 'stream_ready' : lifecycleState;
					isUpgradeReady = true;
				}
			}
			return;
		}

		// Start new extraction
		lifecycleState = lifecycleState === 'embed_playing' ? 'stream_extracting' : lifecycleState;

		try {
			const result = await fetchStreamInfo(video.platform, video.videoId, priority);
			if (result) {
				streamInfo = result;
				// Only update state if still on same video
				if (currentVideoRef?.videoId === video.videoId) {
					isUpgradeReady = true;
					if (lifecycleState === 'stream_extracting') {
						lifecycleState = 'stream_ready';
					}
				}
			} else {
				streamError = 'Stream extraction failed';
			}
		} catch (e) {
			streamError = e instanceof Error ? e.message : 'Unknown error';
		}
	}

	/**
	 * Record an upgrade opportunity
	 */
	function recordUpgradeOpportunity(type: UpgradeOpportunity['type']): void {
		if (!isUpgradeReady || upgradeAttempted) return;

		upgradeOpportunities = [
			...upgradeOpportunities,
			{ type, timestamp: Date.now() }
		];
	}

	return {
		// Getters
		get lifecycleState() {
			return lifecycleState;
		},
		get activeStrategy() {
			return activeStrategy;
		},
		get preferredStrategy() {
			return preferredStrategy;
		},
		get streamInfo() {
			return streamInfo;
		},
		get streamError() {
			return streamError;
		},
		get isUpgradeReady() {
			return isUpgradeReady;
		},
		get upgradeAttempted() {
			return upgradeAttempted;
		},
		get canUpgrade() {
			return (
				isUpgradeReady &&
				!upgradeAttempted &&
				streamInfo?.stream_url &&
				activeStrategy !== 'direct_stream'
			);
		},
		get lastKnownPosition() {
			return lastKnownPosition;
		},

		/**
		 * Get capabilities for current video
		 */
		getCapabilities(platform: string): PlaybackCapabilities {
			return getCapabilities(platform);
		},

		/**
		 * Initialize playback for a video
		 */
		async initializePlayback(video: VideoItem, queue?: VideoItem[], queueIndex?: number): Promise<void> {
			// Reset state
			lifecycleState = 'idle';
			activeStrategy = 'none';
			streamInfo = null;
			streamError = null;
			upgradeAttempted = false;
			upgradeOpportunities = [];
			isUpgradeReady = false;
			lastKnownPosition = 0;
			currentVideoRef = video;

			// Cancel any pending extraction
			if (extractionAbort) {
				extractionAbort.abort();
				extractionAbort = null;
			}

			// Determine initial strategy
			const initialStrategy = determineInitialStrategy(video);
			activeStrategy = initialStrategy;

			// Check for cached stream first
			const cached = await streamCache.get(video.platform, video.videoId);
			if (cached) {
				streamInfo = cached;
				isUpgradeReady = true;

				// If we have cached stream and prefer direct, start with it
				if (initialStrategy === 'direct_stream') {
					lifecycleState = 'direct_playing';
				} else {
					// Start with embed but mark stream as ready
					lifecycleState = 'embed_loading';
				}
			} else {
				lifecycleState = initialStrategy === 'audio' ? 'direct_playing' : 'embed_loading';

				// Start background extraction for YouTube
				if (video.platform === 'youtube') {
					startExtraction(video, 'critical');
				}
			}

			// Prefetch upcoming videos in queue
			if (queue && typeof queueIndex === 'number') {
				prefetchQueueVideos(queue, queueIndex);
			}
		},

		/**
		 * Signal that embed has loaded and is playing
		 */
		embedReady(): void {
			if (lifecycleState === 'embed_loading') {
				lifecycleState = streamInfo ? 'stream_ready' : 'embed_playing';
			}
		},

		/**
		 * Signal that direct stream has loaded and is playing
		 */
		directStreamReady(): void {
			lifecycleState = 'direct_playing';
			activeStrategy = 'direct_stream';
		},

		/**
		 * Update last known position (for seamless upgrades)
		 */
		updatePosition(time: number): void {
			lastKnownPosition = time;
		},

		/**
		 * Record that video was paused (upgrade opportunity)
		 */
		onPause(): void {
			recordUpgradeOpportunity('pause');
		},

		/**
		 * Record that video is buffering (upgrade opportunity)
		 */
		onBuffering(): void {
			recordUpgradeOpportunity('buffer');
		},

		/**
		 * Record that tab went to background (upgrade opportunity)
		 */
		onBackground(): void {
			recordUpgradeOpportunity('background');
		},

		/**
		 * Check if we should attempt upgrade now
		 */
		shouldAttemptUpgrade(): boolean {
			if (!this.canUpgrade) return false;
			if (upgradeOpportunities.length === 0) return false;

			// Prefer pauses and buffers
			const hasGoodOpportunity = upgradeOpportunities.some(
				(o) => o.type === 'pause' || o.type === 'buffer'
			);

			return hasGoodOpportunity;
		},

		/**
		 * Begin upgrade from embed to direct stream
		 */
		async attemptUpgrade(currentTime: number, isPlaying: boolean): Promise<boolean> {
			if (!this.canUpgrade || !streamInfo?.stream_url) {
				return false;
			}

			upgradeAttempted = true;
			wasPlayingBeforeUpgrade = isPlaying;
			lastKnownPosition = currentTime;
			lifecycleState = 'upgrading';

			return true;
		},

		/**
		 * Upgrade completed successfully
		 */
		upgradeComplete(): void {
			lifecycleState = 'direct_playing';
			activeStrategy = 'direct_stream';
		},

		/**
		 * Upgrade failed - stay on embed
		 */
		upgradeFailed(error?: string): void {
			lifecycleState = 'upgrade_failed';
			streamError = error || 'Upgrade failed';
			// Stay on embed strategy
		},

		/**
		 * Should resume playback after upgrade?
		 */
		get shouldResumeAfterUpgrade(): boolean {
			return wasPlayingBeforeUpgrade;
		},

		/**
		 * Set preferred strategy (user setting)
		 */
		setPreferredStrategy(strategy: PlaybackStrategyType): void {
			preferredStrategy = strategy;
		},

		/**
		 * Manually request upgrade
		 */
		requestUpgrade(): void {
			recordUpgradeOpportunity('manual');
		},

		/**
		 * Clean up when video closes
		 */
		cleanup(): void {
			lifecycleState = 'idle';
			activeStrategy = 'none';
			streamInfo = null;
			streamError = null;
			upgradeAttempted = false;
			upgradeOpportunities = [];
			isUpgradeReady = false;
			lastKnownPosition = 0;
			wasPlayingBeforeUpgrade = false;
			currentVideoRef = null;

			if (extractionAbort) {
				extractionAbort.abort();
				extractionAbort = null;
			}
		},

		/**
		 * Get stream URL for direct playback
		 */
		get streamUrl(): string | null {
			return streamInfo?.stream_url || null;
		},

		/**
		 * Get audio URL for DASH (separate audio stream)
		 */
		get audioUrl(): string | null {
			return streamInfo?.audio_url || null;
		},

		/**
		 * Is using DASH (separate video + audio)?
		 */
		get isDash(): boolean {
			return !!streamInfo?.audio_url;
		},

		/**
		 * Get quality label
		 */
		get quality(): string | null {
			return streamInfo?.quality || null;
		},

		/**
		 * Check if playing via embed (with potential ads)
		 */
		get isEmbed(): boolean {
			return activeStrategy === 'embed' || activeStrategy === 'youtube_api';
		},

		/**
		 * Check if playing ad-free direct stream
		 */
		get isDirect(): boolean {
			return activeStrategy === 'direct_stream';
		}
	};
}

// Singleton instance
export const playerState = createPlayerStateStore();

// Re-export types for convenience
export type { StreamInfo, VideoItem };
