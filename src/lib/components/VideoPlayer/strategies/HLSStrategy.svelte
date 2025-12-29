<script lang="ts">
	/**
	 * HLS Strategy
	 *
	 * Uses hls.js for HTTP Live Streaming (HLS) playback.
	 * Supports Red Bar Radio and other HLS sources.
	 * Includes watch progress tracking for long-form content.
	 */
	import Hls from 'hls.js';
	import type { StrategyProps } from './types';
	import { videoPlayer, formatDuration, PLAYER_EVENTS } from '$lib/stores/videoPlayer.svelte';
	import { onMount, onDestroy } from 'svelte';

	interface Props extends StrategyProps {}

	let { video, startTime = 0, autoplay = true, callbacks, streamInfo }: Props = $props();

	let videoElement: HTMLVideoElement | null = null;
	let hls: Hls | null = null;
	let isReady = $state(false);
	let isPlaying = $state(false);
	let currentTime = $state(0);
	let duration = $state(0);
	let quality = $state<string | null>(null);
	let availableQualities = $state<Array<{ height: number; bitrate: number }>>([]);
	let error = $state<string | null>(null);
	let isBuffering = $state(false);

	// Get HLS URL from streamInfo or video
	const hlsUrl = $derived(
		streamInfo?.stream_url ||
			video.videoStreamUrl ||
			(video.videoUrl?.includes('.m3u8') ? video.videoUrl : null)
	);

	// Progress percentage
	let progress = $derived(duration > 0 ? (currentTime / duration) * 100 : 0);

	function initHls() {
		if (!videoElement || !hlsUrl) return;

		// Check for native HLS support (Safari)
		if (videoElement.canPlayType('application/vnd.apple.mpegurl')) {
			videoElement.src = hlsUrl;
			videoElement.addEventListener('loadedmetadata', () => {
				if (startTime > 0) {
					videoElement!.currentTime = startTime;
				}
				if (autoplay) {
					videoElement!.play().catch(() => {});
				}
			});
			return;
		}

		// Use hls.js for other browsers
		if (Hls.isSupported()) {
			hls = new Hls({
				enableWorker: true,
				lowLatencyMode: false,
				backBufferLength: 90,
			});

			hls.loadSource(hlsUrl);
			hls.attachMedia(videoElement);

			hls.on(Hls.Events.MANIFEST_PARSED, (_event, data) => {
				// Get available qualities
				availableQualities = data.levels.map((level) => ({
					height: level.height,
					bitrate: level.bitrate,
				}));

				// Set current quality
				if (data.levels.length > 0) {
					const currentLevel = data.levels[hls!.currentLevel] || data.levels[0];
					quality = currentLevel.height ? `${currentLevel.height}p` : null;
				}

				// Seek to start time and autoplay
				if (startTime > 0 && videoElement) {
					videoElement.currentTime = startTime;
				}
				if (autoplay && videoElement) {
					videoElement.play().catch(() => {});
				}
			});

			hls.on(Hls.Events.LEVEL_SWITCHED, (_event, data) => {
				const level = hls!.levels[data.level];
				if (level) {
					quality = level.height ? `${level.height}p` : null;
				}
			});

			hls.on(Hls.Events.ERROR, (_event, data) => {
				if (data.fatal) {
					switch (data.type) {
						case Hls.ErrorTypes.NETWORK_ERROR:
							error = 'Network error - trying to recover...';
							hls!.startLoad();
							break;
						case Hls.ErrorTypes.MEDIA_ERROR:
							error = 'Media error - trying to recover...';
							hls!.recoverMediaError();
							break;
						default:
							error = 'Fatal playback error';
							destroyHls();
							callbacks?.onError?.(error);
							break;
					}
				}
			});
		} else {
			error = 'HLS playback is not supported in this browser';
			callbacks?.onError?.(error);
		}
	}

	function destroyHls() {
		if (hls) {
			hls.destroy();
			hls = null;
		}
	}

	function handleCanPlay() {
		if (!isReady) {
			isReady = true;
			duration = videoElement?.duration || 0;
			videoPlayer.updateMediaMetadata();
			callbacks?.onReady?.();
		}
		isBuffering = false;
	}

	function handlePlay() {
		isPlaying = true;
		videoPlayer.setPlaybackState(true);
		callbacks?.onPlay?.();
	}

	function handlePause() {
		isPlaying = false;
		videoPlayer.setPlaybackState(false);
		callbacks?.onPause?.();
	}

	function handleEnded() {
		isPlaying = false;
		callbacks?.onEnded?.();
	}

	function handleTimeUpdate() {
		if (videoElement) {
			currentTime = videoElement.currentTime;
			duration = videoElement.duration || 0;
			videoPlayer.updatePosition(currentTime, duration);
			// Call the callback for watch progress tracking
			callbacks?.onTimeUpdate?.(currentTime, duration);
		}
	}

	function handleWaiting() {
		isBuffering = true;
		callbacks?.onBuffering?.();
	}

	function handleError() {
		error = 'Video playback failed';
		callbacks?.onError?.(error);
	}

	function togglePlayPause() {
		if (!videoElement) return;
		if (isPlaying) {
			videoElement.pause();
		} else {
			videoElement.play();
		}
	}

	function skip(seconds: number) {
		if (!videoElement) return;
		const newTime = Math.max(0, Math.min(duration, videoElement.currentTime + seconds));
		videoElement.currentTime = newTime;
	}

	function handleProgressClick(e: MouseEvent) {
		if (!videoElement) return;
		const bar = e.currentTarget as HTMLElement;
		const rect = bar.getBoundingClientRect();
		const percent = (e.clientX - rect.left) / rect.width;
		videoElement.currentTime = percent * duration;
	}

	// Listen for global player events
	function handlePlayerPlay() {
		videoElement?.play();
	}

	function handlePlayerPause() {
		videoElement?.pause();
	}

	function handlePlayerSeek(e: CustomEvent) {
		if (!videoElement) return;
		const { offset } = e.detail as { offset: number };
		skip(offset);
	}

	function handlePlayerSeekTo(e: CustomEvent) {
		if (!videoElement) return;
		const { time } = e.detail as { time: number };
		videoElement.currentTime = time;
	}

	$effect(() => {
		if (typeof window !== 'undefined') {
			window.addEventListener(PLAYER_EVENTS.PLAY, handlePlayerPlay);
			window.addEventListener(PLAYER_EVENTS.PAUSE, handlePlayerPause);
			window.addEventListener(PLAYER_EVENTS.SEEK, handlePlayerSeek as EventListener);
			window.addEventListener(PLAYER_EVENTS.SEEK_TO, handlePlayerSeekTo as EventListener);

			return () => {
				window.removeEventListener(PLAYER_EVENTS.PLAY, handlePlayerPlay);
				window.removeEventListener(PLAYER_EVENTS.PAUSE, handlePlayerPause);
				window.removeEventListener(PLAYER_EVENTS.SEEK, handlePlayerSeek as EventListener);
				window.removeEventListener(PLAYER_EVENTS.SEEK_TO, handlePlayerSeekTo as EventListener);
			};
		}
	});

	// Initialize HLS when component mounts
	$effect(() => {
		if (videoElement && hlsUrl) {
			initHls();
		}
	});

	// Cleanup on unmount
	onDestroy(() => {
		destroyHls();
	});

	// Export video element for external control
	export function getVideoElement(): HTMLVideoElement | null {
		return videoElement;
	}
</script>

{#if hlsUrl}
	<div class="hls-player">
		<video
			bind:this={videoElement}
			controls
			class="hls-video"
			oncanplay={handleCanPlay}
			onplay={handlePlay}
			onpause={handlePause}
			onended={handleEnded}
			ontimeupdate={handleTimeUpdate}
			onwaiting={handleWaiting}
			onerror={handleError}
			poster={video.thumbnailUrl}
		>
			Your browser does not support video playback.
		</video>

		{#if isBuffering}
			<div class="buffering-indicator">
				<div class="spinner"></div>
			</div>
		{/if}

		{#if quality}
			<span class="quality-badge">{quality}</span>
		{/if}

		{#if error}
			<div class="error-overlay">
				<p>{error}</p>
			</div>
		{/if}
	</div>
{:else}
	<div class="no-stream">
		<p>No HLS stream available</p>
		{#if video.audioUrl}
			<p class="fallback-hint">Audio fallback available</p>
		{/if}
	</div>
{/if}

<style>
	.hls-player {
		position: relative;
		width: 100%;
		height: 100%;
		background: black;
	}

	.hls-video {
		width: 100%;
		height: 100%;
		background: black;
	}

	.quality-badge {
		position: absolute;
		top: var(--spacing-sm);
		right: var(--spacing-sm);
		padding: 2px 6px;
		background: rgba(0, 0, 0, 0.75);
		color: white;
		font-size: 0.7rem;
		font-weight: 600;
		border-radius: var(--radius-sm);
		pointer-events: none;
	}

	.buffering-indicator {
		position: absolute;
		top: 50%;
		left: 50%;
		transform: translate(-50%, -50%);
		pointer-events: none;
	}

	.spinner {
		width: 48px;
		height: 48px;
		border: 3px solid rgba(255, 255, 255, 0.3);
		border-top-color: white;
		border-radius: 50%;
		animation: spin 1s linear infinite;
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}

	.error-overlay {
		position: absolute;
		top: 0;
		left: 0;
		width: 100%;
		height: 100%;
		display: flex;
		align-items: center;
		justify-content: center;
		background: rgba(0, 0, 0, 0.8);
		color: var(--color-error, #ef4444);
		padding: var(--spacing-lg);
		text-align: center;
	}

	.no-stream {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		width: 100%;
		height: 100%;
		background: black;
		color: var(--color-text-muted);
		gap: var(--spacing-sm);
	}

	.fallback-hint {
		font-size: 0.85rem;
		color: var(--color-text-muted);
		opacity: 0.7;
	}
</style>
