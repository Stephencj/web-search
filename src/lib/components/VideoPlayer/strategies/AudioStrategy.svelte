<script lang="ts">
	/**
	 * Audio Strategy
	 *
	 * Uses native HTML5 audio element for podcast/audio content.
	 * Fast startup, supports background playback natively.
	 */
	import type { StrategyProps } from './types';
	import { videoPlayer, formatDuration } from '$lib/stores/videoPlayer.svelte';

	interface Props extends StrategyProps {}

	let { video, startTime = 0, autoplay = true, callbacks }: Props = $props();

	let audioElement: HTMLAudioElement | null = null;
	let isReady = $state(false);

	function handleCanPlay() {
		if (!isReady) {
			isReady = true;
			videoPlayer.updateMediaMetadata();

			// Seek to start time
			if (startTime > 0 && audioElement) {
				audioElement.currentTime = startTime;
			}

			callbacks?.onReady?.();
		}
	}

	function handlePlay() {
		videoPlayer.setPlaybackState(true);
		callbacks?.onPlay?.();
	}

	function handlePause() {
		videoPlayer.setPlaybackState(false);
		callbacks?.onPause?.();
	}

	function handleEnded() {
		callbacks?.onEnded?.();
	}

	function handleTimeUpdate() {
		if (audioElement) {
			videoPlayer.updatePosition(audioElement.currentTime, audioElement.duration || 0);
			callbacks?.onTimeUpdate?.(audioElement.currentTime, audioElement.duration || 0);
		}
	}

	// Export audio element for external control
	export function getAudioElement(): HTMLAudioElement | null {
		return audioElement;
	}
</script>

<div class="audio-player">
	<div class="audio-artwork">
		{#if video.thumbnailUrl}
			<img src={video.thumbnailUrl} alt={video.title} class="album-art" />
		{:else}
			<div class="album-art-placeholder">
				<svg viewBox="0 0 24 24" fill="currentColor" width="80" height="80">
					<path
						d="M12 3v10.55c-.59-.34-1.27-.55-2-.55-2.21 0-4 1.79-4 4s1.79 4 4 4 4-1.79 4-4V7h4V3h-6z"
					/>
				</svg>
			</div>
		{/if}
	</div>
	<div class="audio-controls">
		<audio
			bind:this={audioElement}
			src={video.videoUrl}
			controls
			autoplay={autoplay}
			oncanplay={handleCanPlay}
			onplay={handlePlay}
			onpause={handlePause}
			onended={handleEnded}
			ontimeupdate={handleTimeUpdate}
			class="audio-element"
		>
			Your browser does not support audio playback.
		</audio>
		{#if video.duration}
			<div class="audio-duration">
				Duration: {formatDuration(video.duration)}
			</div>
		{/if}
	</div>
</div>

<style>
	.audio-player {
		display: flex;
		flex-direction: column;
		align-items: center;
		justify-content: center;
		width: 100%;
		height: 100%;
		padding: var(--spacing-xl);
		background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
		gap: var(--spacing-lg);
	}

	.audio-artwork {
		flex-shrink: 0;
		width: 100%;
		max-width: 400px;
		aspect-ratio: 1;
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.album-art {
		width: 100%;
		height: 100%;
		object-fit: cover;
		border-radius: var(--radius-lg);
		box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
	}

	.album-art-placeholder {
		width: 100%;
		height: 100%;
		display: flex;
		align-items: center;
		justify-content: center;
		background: linear-gradient(135deg, #2d2d44 0%, #1a1a2e 100%);
		border-radius: var(--radius-lg);
		color: var(--color-text-muted);
	}

	.audio-controls {
		width: 100%;
		max-width: 600px;
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: var(--spacing-md);
	}

	.audio-element {
		width: 100%;
		height: 48px;
		border-radius: var(--radius-md);
	}

	.audio-element::-webkit-media-controls-panel {
		background: var(--color-bg-secondary);
	}

	.audio-duration {
		color: var(--color-text-muted);
		font-size: 0.875rem;
	}

	@media (max-width: 640px) {
		.audio-player {
			padding: var(--spacing-md);
		}

		.audio-artwork {
			max-width: 250px;
		}
	}
</style>
