<script lang="ts">
	/**
	 * Direct Stream Strategy
	 *
	 * Uses native HTML5 video element with direct stream URL.
	 * Highest quality, no ads, supports background playback.
	 * Requires stream extraction (YouTube only currently).
	 */
	import type { StrategyProps } from './types';
	import { videoPlayer } from '$lib/stores/videoPlayer.svelte';

	interface Props extends StrategyProps {}

	let { video, startTime = 0, autoplay = true, callbacks, streamInfo }: Props = $props();

	let videoElement: HTMLVideoElement | null = null;
	let audioElement: HTMLAudioElement | null = null;
	let isReady = $state(false);

	const streamUrl = $derived(streamInfo?.stream_url);
	const audioUrl = $derived(streamInfo?.audio_url);
	const quality = $derived(streamInfo?.quality);
	const isDash = $derived(!!audioUrl);

	function handleCanPlay() {
		if (!isReady) {
			isReady = true;
			callbacks?.onReady?.();

			// Seek to start time if provided
			if (startTime > 0 && videoElement) {
				videoElement.currentTime = startTime;
			}
		}
	}

	function handlePlay() {
		// Sync audio for DASH
		if (audioElement && videoElement) {
			audioElement.currentTime = videoElement.currentTime;
			audioElement.play().catch(() => {});
		}
		videoPlayer.setPlaybackState(true);
		callbacks?.onPlay?.();
	}

	function handlePause() {
		// Sync audio pause
		if (audioElement) {
			audioElement.pause();
		}
		videoPlayer.setPlaybackState(false);
		callbacks?.onPause?.();
	}

	function handleEnded() {
		callbacks?.onEnded?.();
	}

	function handleTimeUpdate() {
		if (videoElement) {
			videoPlayer.updatePosition(videoElement.currentTime, videoElement.duration || 0);
			callbacks?.onTimeUpdate?.(videoElement.currentTime, videoElement.duration || 0);
		}
	}

	function handleSeeked() {
		// Sync audio when seeking
		if (audioElement && videoElement) {
			audioElement.currentTime = videoElement.currentTime;
		}
	}

	function handleWaiting() {
		callbacks?.onBuffering?.();
	}

	function handleError() {
		callbacks?.onError?.('Video playback failed');
	}

	// Export video element for external control
	export function getVideoElement(): HTMLVideoElement | null {
		return videoElement;
	}

	export function getAudioElement(): HTMLAudioElement | null {
		return audioElement;
	}
</script>

{#if streamUrl}
	<div class="direct-player">
		<video
			bind:this={videoElement}
			src={streamUrl}
			controls
			autoplay={autoplay}
			playsinline
			class="direct-video"
			oncanplay={handleCanPlay}
			onplay={handlePlay}
			onpause={handlePause}
			onended={handleEnded}
			ontimeupdate={handleTimeUpdate}
			onseeked={handleSeeked}
			onwaiting={handleWaiting}
			onerror={handleError}
		>
			Your browser does not support video playback.
		</video>
		{#if audioUrl}
			<!-- Separate audio stream for DASH playback -->
			<audio bind:this={audioElement} src={audioUrl} class="hidden-audio"></audio>
		{/if}
		{#if quality}
			<span class="quality-badge">{quality}</span>
		{/if}
	</div>
{:else}
	<div class="no-stream">
		<p>No stream available</p>
	</div>
{/if}

<style>
	.direct-player {
		position: relative;
		width: 100%;
		height: 100%;
	}

	.direct-video {
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

	.hidden-audio {
		display: none;
	}

	.no-stream {
		display: flex;
		align-items: center;
		justify-content: center;
		width: 100%;
		height: 100%;
		background: black;
		color: var(--color-text-muted);
	}
</style>
