<script lang="ts">
	/**
	 * Video Player Modal V2
	 *
	 * Refactored modal player using the new modular architecture:
	 * - Uses PlayerContent for strategy selection
	 * - Uses PlayerHeader and PlayerInfo for UI
	 * - Uses composables for shared logic
	 * - Integrates with playerState for lifecycle management
	 */
	import { videoPlayer, type StreamInfo } from '$lib/stores/videoPlayer.svelte';
	import { playerState } from '$lib/stores/playerState.svelte';
	import { playbackPreferences } from '$lib/stores/playbackPreferences.svelte';
	import { streamCache, fetchStreamInfo } from '$lib/stores/streamCacheV2.svelte';
	import { prefetchQueueVideos } from '$lib/stores/prefetchQueue.svelte';
	import { useProgressTracking } from './composables/useProgressTracking.svelte';
	import { usePlaybackControl } from './composables/usePlaybackControl.svelte';
	import { PlayerContent, PlayerHeader, PlayerInfo } from './core';
	import type { StrategyType, PlaybackCallbacks } from './strategies/types';

	interface Props {
		onMarkWatched?: () => void;
	}

	let { onMarkWatched }: Props = $props();

	// Stream state
	let streamInfo = $state<StreamInfo | null>(null);
	let useDirectStream = $state(false);

	// Strategy override
	let preferredStrategy = $state<StrategyType | undefined>(undefined);

	// Delay content render to ensure modal is visible (helps with autoplay)
	let contentReady = $state(false);

	// Composables
	const progress = useProgressTracking(
		() => videoPlayer.currentVideo,
		{ onMarkedWatched: onMarkWatched }
	);
	const controls = usePlaybackControl();

	// Derived values
	const video = $derived(videoPlayer.currentVideo);
	const isOpen = $derived(videoPlayer.isModal && video !== null);
	const videoKey = $derived(videoPlayer.videoKey);
	const theaterMode = $derived(playbackPreferences.theaterMode);
	const savedPlayhead = $derived(videoPlayer.savedPlayhead);
	const shouldResumePlayback = $derived(videoPlayer.shouldResumePlayback);

	// Callbacks for strategy components
	const strategyCallbacks: PlaybackCallbacks = {
		onReady: () => {
			// Clear saved playhead after restore
			if (savedPlayhead > 0) {
				videoPlayer.clearSavedPlayhead();
			}
			// Resume playback if switching modes
			if (shouldResumePlayback) {
				videoPlayer.clearShouldResumePlayback();
			}
			// Start progress tracking
			progress.start(controls.getCurrentTime, controls.getDuration);
		},
		onPlay: () => {
			videoPlayer.setPlaybackState(true);
		},
		onPause: () => {
			videoPlayer.setPlaybackState(false);
			// Save progress on pause
			const time = controls.getCurrentTime();
			if (time > 0) {
				progress.saveToApi(time);
			}
		},
		onEnded: () => {
			// Mark as watched
			const duration = controls.getDuration();
			progress.markAsWatched(duration);
			progress.stop();
			// Auto-advance
			if (!videoPlayer.playNext()) {
				handleClose();
			}
		},
		onTimeUpdate: (time, duration) => {
			videoPlayer.updatePosition(time, duration);
		},
		onBuffering: () => {
			// Potential upgrade opportunity
			playerState.onBuffering();
		},
		onError: (error) => {
			console.warn('[ModalV2] Strategy error:', error);
		}
	};

	/**
	 * Fetch stream info for the current video
	 */
	async function loadStreamInfo() {
		if (!video) return;

		// Handle offline videos - use the pre-loaded blob URL
		if (video.isOffline && video.offlineStreamUrl) {
			streamInfo = {
				video_id: video.videoId,
				platform: video.platform,
				title: video.title,
				stream_url: video.offlineStreamUrl,
				audio_url: video.contentType === 'audio' ? video.offlineStreamUrl : undefined,
				thumbnail_url: video.thumbnailUrl ?? undefined,
				duration_seconds: video.duration ?? undefined,
				is_authenticated: false,
				is_premium: false,
				quality: 'offline',
			};
			useDirectStream = true;
			return;
		}

		// Only fetch streams for YouTube currently
		if (video.platform !== 'youtube') return;

		// Check cache first
		const cached = streamCache.getSync(video.platform, video.videoId);
		if (cached) {
			streamInfo = cached;
			useDirectStream = !!cached.stream_url;
			return;
		}

		// Fetch in background
		const result = await fetchStreamInfo(video.platform, video.videoId, 'critical');
		if (result) {
			streamInfo = result;
			useDirectStream = !!result.stream_url;
		}

		// Prefetch upcoming
		const upcoming = videoPlayer.getUpcomingVideos(3);
		if (upcoming.length > 0) {
			prefetchQueueVideos(upcoming, videoPlayer.currentIndex);
		}
	}

	function handleClose() {
		// Save final progress
		const time = controls.getCurrentTime();
		if (time > 0) {
			progress.saveLocal(time);
		}
		progress.stop();
		controls.cleanup();
		playerState.cleanup();
		videoPlayer.close();

		// Reset state
		streamInfo = null;
		useDirectStream = false;
		preferredStrategy = undefined;
	}

	function handleSwitchToPiP() {
		const time = controls.getCurrentTime();
		if (time > 0) {
			progress.saveToApi(time);
		}
		progress.stop();
		videoPlayer.savePlayhead(time);
		videoPlayer.switchToPiP();
	}

	function toggleTheaterMode() {
		playbackPreferences.toggleTheaterMode();
	}

	function toggleDirectStream() {
		if (streamInfo?.stream_url) {
			useDirectStream = !useDirectStream;
			preferredStrategy = useDirectStream ? 'direct_stream' : 'embed';
		}
	}

	function handleBackdropClick(event: MouseEvent) {
		if (event.target === event.currentTarget) {
			handleClose();
		}
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape') {
			handleClose();
		} else if (event.key === 'p' || event.key === 'P') {
			handleSwitchToPiP();
		} else if (event.key === 't' || event.key === 'T') {
			toggleTheaterMode();
		} else if (event.key === 'ArrowLeft' && videoPlayer.hasPrevious) {
			videoPlayer.playPrevious();
		} else if (event.key === 'ArrowRight' && videoPlayer.hasNext) {
			videoPlayer.playNext();
		}
	}

	// Initialize when video changes
	$effect(() => {
		if (video) {
			// Reset state
			streamInfo = null;
			useDirectStream = false;
			preferredStrategy = undefined;
			contentReady = false;
			progress.stop();

			// Initialize player state
			playerState.initializePlayback(video, videoPlayer.queue, videoPlayer.currentIndex);

			// Load stream info
			loadStreamInfo();

			// Small delay to ensure modal is fully visible before rendering iframe
			// This helps browsers recognize the user gesture for autoplay
			const timer = setTimeout(() => {
				contentReady = true;
			}, 50);

			return () => clearTimeout(timer);
		}
	});

	// Register playback control handlers
	$effect(() => {
		if (isOpen) {
			controls.registerHandlers({
				getVideoElement: () => document.querySelector('.direct-video') as HTMLVideoElement | null,
				getAudioElement: () => document.querySelector('.audio-element') as HTMLAudioElement | null,
				isYtPlayerReady: () => !!document.querySelector('.yt-player-container.loaded')
			});
		}

		return () => {
			controls.cleanup();
		};
	});

	// Save progress on visibility change
	$effect(() => {
		if (!isOpen) return;

		function handleVisibilityChange() {
			if (document.hidden) {
				progress.saveLocal(controls.getCurrentTime());
			}
		}

		function handleBeforeUnload() {
			progress.saveLocal(controls.getCurrentTime());
		}

		document.addEventListener('visibilitychange', handleVisibilityChange);
		window.addEventListener('beforeunload', handleBeforeUnload);

		return () => {
			document.removeEventListener('visibilitychange', handleVisibilityChange);
			window.removeEventListener('beforeunload', handleBeforeUnload);
		};
	});

	// Cleanup on unmount
	$effect(() => {
		return () => {
			progress.stop();
			controls.cleanup();
		};
	});
</script>

<svelte:window onkeydown={handleKeydown} />

{#if isOpen && video}
	<div
		class="player-overlay"
		onclick={handleBackdropClick}
		role="dialog"
		aria-modal="true"
		aria-labelledby="video-title"
	>
		<div class="player-modal" class:theater={theaterMode}>
			<PlayerHeader
				{streamInfo}
				{useDirectStream}
				onToggleDirectStream={toggleDirectStream}
				onToggleTheaterMode={toggleTheaterMode}
				onSwitchToPiP={handleSwitchToPiP}
				onClose={handleClose}
				{theaterMode}
			/>

			<div class="player-content-wrapper">
				{#if contentReady}
					{#key videoKey}
						<PlayerContent
							{video}
							{streamInfo}
							startTime={progress.getInitialPlayhead(savedPlayhead)}
							autoplay={true}
							{preferredStrategy}
							callbacks={strategyCallbacks}
						/>
					{/key}
				{:else}
					<div class="loading-placeholder">
						<div class="spinner"></div>
					</div>
				{/if}
			</div>

			<PlayerInfo {video} />
		</div>
	</div>
{/if}

<style>
	.player-overlay {
		position: fixed;
		inset: 0;
		background: rgba(0, 0, 0, 0.85);
		display: flex;
		align-items: center;
		justify-content: center;
		z-index: 1000;
		padding: var(--spacing-lg);
	}

	.player-modal {
		width: 100%;
		max-width: 1200px;
		max-height: 90vh;
		background: var(--color-bg-secondary);
		border-radius: var(--radius-lg);
		overflow: hidden;
		display: flex;
		flex-direction: column;
		transition:
			max-width 0.2s ease,
			max-height 0.2s ease,
			border-radius 0.2s ease;
	}

	.player-modal.theater {
		max-width: 100%;
		max-height: 100%;
		border-radius: 0;
	}

	.player-overlay:has(.player-modal.theater) {
		padding: 0;
		background: black;
	}

	.player-content-wrapper {
		position: relative;
		width: 100%;
		aspect-ratio: 16 / 9;
		background: black;
		flex-shrink: 0;
		min-height: 300px;
	}

	.player-modal.theater .player-content-wrapper {
		aspect-ratio: unset;
		height: 100%;
	}

	.loading-placeholder {
		position: absolute;
		inset: 0;
		display: flex;
		align-items: center;
		justify-content: center;
		background: black;
	}

	.spinner {
		width: 48px;
		height: 48px;
		border: 3px solid var(--color-border, #333);
		border-top-color: var(--color-primary, #fff);
		border-radius: 50%;
		animation: spin 1s linear infinite;
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}

	@media (max-width: 768px) {
		.player-overlay {
			padding: 0;
			align-items: flex-start;
		}

		.player-modal {
			max-width: 100%;
			max-height: 100vh;
			border-radius: 0;
		}
	}
</style>
