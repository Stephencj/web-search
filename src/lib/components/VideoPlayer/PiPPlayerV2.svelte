<script lang="ts">
	/**
	 * PiP Player V2
	 *
	 * Refactored Picture-in-Picture player using the new modular architecture.
	 * Shares logic with Modal via composables and core components.
	 */
	import { videoPlayer, type StreamInfo } from '$lib/stores/videoPlayer.svelte';
	import { playerState } from '$lib/stores/playerState.svelte';
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
	let preferredStrategy = $state<StrategyType | undefined>(undefined);

	// Position and size
	let position = $state({ x: 20, y: 20 });
	let isDragging = $state(false);
	let dragOffset = { x: 0, y: 0 };
	let size = $state<'small' | 'medium'>('small');

	// Composables
	const progress = useProgressTracking(
		() => videoPlayer.currentVideo,
		{ onMarkedWatched: onMarkWatched }
	);
	const controls = usePlaybackControl();

	// Derived values
	const video = $derived(videoPlayer.currentVideo);
	const isOpen = $derived(videoPlayer.isPiP && video !== null);
	const videoKey = $derived(videoPlayer.videoKey);
	const savedPlayhead = $derived(videoPlayer.savedPlayhead);
	const shouldResumePlayback = $derived(videoPlayer.shouldResumePlayback);

	// Size dimensions
	const dimensions = $derived({
		width: size === 'small' ? 320 : 480,
		height: size === 'small' ? 180 : 270
	});

	// Callbacks for strategy components
	const strategyCallbacks: PlaybackCallbacks = {
		onReady: () => {
			if (savedPlayhead > 0) {
				videoPlayer.clearSavedPlayhead();
			}
			if (shouldResumePlayback) {
				videoPlayer.clearShouldResumePlayback();
			}
			progress.start(controls.getCurrentTime, controls.getDuration);
		},
		onPlay: () => {
			videoPlayer.setPlaybackState(true);
		},
		onPause: () => {
			videoPlayer.setPlaybackState(false);
			const time = controls.getCurrentTime();
			if (time > 0) {
				progress.saveToApi(time);
			}
		},
		onEnded: () => {
			const duration = controls.getDuration();
			progress.markAsWatched(duration);
			progress.stop();
			if (!videoPlayer.playNext()) {
				handleClose();
			}
		},
		onTimeUpdate: (time, duration) => {
			videoPlayer.updatePosition(time, duration);
		},
		onBuffering: () => {
			playerState.onBuffering();
		},
		onError: (error) => {
			console.warn('[PiPV2] Strategy error:', error);
		}
	};

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

		const cached = streamCache.getSync(video.platform, video.videoId);
		if (cached) {
			streamInfo = cached;
			useDirectStream = !!cached.stream_url;
			return;
		}

		const result = await fetchStreamInfo(video.platform, video.videoId, 'high');
		if (result) {
			streamInfo = result;
			useDirectStream = !!result.stream_url;
		}

		const upcoming = videoPlayer.getUpcomingVideos(3);
		if (upcoming.length > 0) {
			prefetchQueueVideos(upcoming, videoPlayer.currentIndex);
		}
	}

	function handleClose() {
		const time = controls.getCurrentTime();
		if (time > 0) {
			progress.saveLocal(time);
		}
		progress.stop();
		controls.cleanup();
		playerState.cleanup();
		videoPlayer.close();
		streamInfo = null;
		useDirectStream = false;
		preferredStrategy = undefined;
	}

	function handleSwitchToModal() {
		const time = controls.getCurrentTime();
		if (time > 0) {
			progress.saveToApi(time);
		}
		progress.stop();
		videoPlayer.savePlayhead(time);
		videoPlayer.switchToModal();
	}

	function toggleSize() {
		size = size === 'small' ? 'medium' : 'small';
	}

	// Dragging handlers
	function handleDragStart(event: MouseEvent) {
		if ((event.target as HTMLElement).closest('.header-btn')) return;
		isDragging = true;
		dragOffset = {
			x: event.clientX - position.x,
			y: event.clientY - position.y
		};
	}

	function handleDrag(event: MouseEvent) {
		if (!isDragging) return;
		const maxX = window.innerWidth - dimensions.width - 10;
		const maxY = window.innerHeight - dimensions.height - 10;
		position = {
			x: Math.max(10, Math.min(event.clientX - dragOffset.x, maxX)),
			y: Math.max(10, Math.min(event.clientY - dragOffset.y, maxY))
		};
	}

	function handleDragEnd() {
		isDragging = false;
	}

	function handleKeydown(event: KeyboardEvent) {
		if (event.key === 'Escape') {
			handleClose();
		} else if (event.key === 'm' || event.key === 'M') {
			handleSwitchToModal();
		}
	}

	// Initialize when video changes
	$effect(() => {
		if (video) {
			streamInfo = null;
			useDirectStream = false;
			preferredStrategy = undefined;
			progress.stop();
			playerState.initializePlayback(video, videoPlayer.queue, videoPlayer.currentIndex);
			loadStreamInfo();
		}
	});

	// Register playback control handlers
	$effect(() => {
		if (isOpen) {
			controls.registerHandlers({
				getVideoElement: () => document.querySelector('.pip-container .direct-video') as HTMLVideoElement | null,
				getAudioElement: () => document.querySelector('.pip-container .audio-element') as HTMLAudioElement | null,
				isYtPlayerReady: () => !!document.querySelector('.pip-container .yt-player-container.loaded')
			});
		}
		return () => controls.cleanup();
	});

	// Global drag handlers
	$effect(() => {
		if (isDragging) {
			window.addEventListener('mousemove', handleDrag);
			window.addEventListener('mouseup', handleDragEnd);
			return () => {
				window.removeEventListener('mousemove', handleDrag);
				window.removeEventListener('mouseup', handleDragEnd);
			};
		}
	});

	// Save on visibility change
	$effect(() => {
		if (!isOpen) return;

		function handleVisibilityChange() {
			if (document.hidden) {
				progress.saveLocal(controls.getCurrentTime());
			}
		}

		document.addEventListener('visibilitychange', handleVisibilityChange);
		return () => document.removeEventListener('visibilitychange', handleVisibilityChange);
	});

	// Cleanup
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
		class="pip-container"
		class:dragging={isDragging}
		style="
			left: {position.x}px;
			top: {position.y}px;
			width: {dimensions.width}px;
			height: {dimensions.height + 100}px;
		"
		onmousedown={handleDragStart}
		role="dialog"
		aria-label="Mini player"
	>
		<PlayerHeader
			compact
			{streamInfo}
			{useDirectStream}
			showTheaterToggle={false}
			showPiPToggle={false}
			showModalToggle={true}
			onSwitchToModal={handleSwitchToModal}
			onClose={handleClose}
		/>

		<div class="pip-content" style="height: {dimensions.height}px;">
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
		</div>

		<div class="pip-controls">
			<PlayerInfo {video} compact />
			<button class="size-toggle" onclick={toggleSize} title="Toggle size">
				<svg viewBox="0 0 24 24" fill="currentColor" width="16" height="16">
					{#if size === 'small'}
						<path d="M7 14H5v5h5v-2H7v-3zm-2-4h2V7h3V5H5v5zm12 7h-3v2h5v-5h-2v3zM14 5v2h3v3h2V5h-5z" />
					{:else}
						<path d="M5 16h3v3h2v-5H5v2zm3-8H5v2h5V5H8v3zm6 11h2v-3h3v-2h-5v5zm2-11V5h-2v5h5V8h-3z" />
					{/if}
				</svg>
			</button>
		</div>
	</div>
{/if}

<style>
	.pip-container {
		position: fixed;
		z-index: 1001;
		background: var(--color-bg-secondary);
		border-radius: var(--radius-lg);
		box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
		overflow: hidden;
		display: flex;
		flex-direction: column;
		cursor: move;
		user-select: none;
	}

	.pip-container.dragging {
		opacity: 0.9;
	}

	.pip-content {
		position: relative;
		width: 100%;
		background: black;
		flex-shrink: 0;
	}

	.pip-controls {
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: var(--spacing-xs) var(--spacing-sm);
		background: var(--color-bg);
		cursor: default;
	}

	.pip-controls :global(.player-info) {
		flex: 1;
		padding: 0;
		background: transparent;
	}

	.size-toggle {
		background: transparent;
		border: none;
		color: var(--color-text-secondary);
		padding: var(--spacing-xs);
		border-radius: var(--radius-sm);
		cursor: pointer;
		display: flex;
		align-items: center;
		justify-content: center;
		flex-shrink: 0;
	}

	.size-toggle:hover {
		color: var(--color-text);
		background: var(--color-bg-secondary);
	}
</style>
