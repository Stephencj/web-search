<script lang="ts">
	/**
	 * Audio Strategy
	 *
	 * Uses native HTML5 audio element for podcast/audio content.
	 * Enhanced with custom controls: speed control, skip buttons, progress bar.
	 */
	import type { StrategyProps } from './types';
	import { videoPlayer, formatDuration, PLAYER_EVENTS } from '$lib/stores/videoPlayer.svelte';

	interface Props extends StrategyProps {}

	let { video, startTime = 0, autoplay = true, callbacks }: Props = $props();

	let audioElement: HTMLAudioElement | null = null;
	let isReady = $state(false);
	let isPlaying = $state(false);
	let currentTime = $state(0);
	let duration = $state(0);
	let playbackRate = $state(1);
	let isSeeking = $state(false);

	const playbackSpeeds = [0.5, 0.75, 1, 1.25, 1.5, 1.75, 2];

	// Derived progress percentage
	let progress = $derived(duration > 0 ? (currentTime / duration) * 100 : 0);

	function handleCanPlay() {
		if (!isReady) {
			isReady = true;
			duration = audioElement?.duration || 0;
			videoPlayer.updateMediaMetadata();

			// Seek to start time
			if (startTime > 0 && audioElement) {
				audioElement.currentTime = startTime;
			}

			callbacks?.onReady?.();
		}
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
		if (audioElement && !isSeeking) {
			currentTime = audioElement.currentTime;
			duration = audioElement.duration || 0;
			videoPlayer.updatePosition(currentTime, duration);
			callbacks?.onTimeUpdate?.(currentTime, duration);
		}
	}

	function togglePlayPause() {
		if (!audioElement) return;
		if (isPlaying) {
			audioElement.pause();
		} else {
			audioElement.play();
		}
	}

	function skip(seconds: number) {
		if (!audioElement) return;
		const newTime = Math.max(0, Math.min(duration, audioElement.currentTime + seconds));
		audioElement.currentTime = newTime;
	}

	function setSpeed(rate: number) {
		if (!audioElement) return;
		playbackRate = rate;
		audioElement.playbackRate = rate;
	}

	function cycleSpeed() {
		const currentIdx = playbackSpeeds.indexOf(playbackRate);
		const nextIdx = (currentIdx + 1) % playbackSpeeds.length;
		setSpeed(playbackSpeeds[nextIdx]);
	}

	function handleProgressClick(e: MouseEvent) {
		if (!audioElement) return;
		const bar = e.currentTarget as HTMLElement;
		const rect = bar.getBoundingClientRect();
		const percent = (e.clientX - rect.left) / rect.width;
		audioElement.currentTime = percent * duration;
	}

	function handleSeekStart() {
		isSeeking = true;
	}

	function handleSeekEnd(e: MouseEvent) {
		if (!audioElement) return;
		const bar = e.currentTarget as HTMLElement;
		const rect = bar.getBoundingClientRect();
		const percent = (e.clientX - rect.left) / rect.width;
		audioElement.currentTime = percent * duration;
		isSeeking = false;
	}

	// Listen for global player events
	function handlePlayerPlay() {
		audioElement?.play();
	}

	function handlePlayerPause() {
		audioElement?.pause();
	}

	function handlePlayerSeek(e: CustomEvent) {
		if (!audioElement) return;
		const { offset } = e.detail as { offset: number };
		skip(offset);
	}

	function handlePlayerSeekTo(e: CustomEvent) {
		if (!audioElement) return;
		const { time } = e.detail as { time: number };
		audioElement.currentTime = time;
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

	<!-- Hidden native audio element -->
	<audio
		bind:this={audioElement}
		src={video.audioUrl || video.videoUrl}
		autoplay={autoplay}
		oncanplay={handleCanPlay}
		onplay={handlePlay}
		onpause={handlePause}
		onended={handleEnded}
		ontimeupdate={handleTimeUpdate}
		class="hidden-audio"
	>
		Your browser does not support audio playback.
	</audio>

	<div class="audio-controls">
		<!-- Episode title -->
		<div class="episode-title">{video.title}</div>
		{#if video.channelName}
			<div class="channel-name">{video.channelName}</div>
		{/if}

		<!-- Progress bar -->
		<div class="progress-container">
			<span class="time-display">{formatDuration(Math.floor(currentTime))}</span>
			<button
				type="button"
				class="progress-bar"
				onclick={handleProgressClick}
				onmousedown={handleSeekStart}
				onmouseup={handleSeekEnd}
			>
				<div class="progress-track">
					<div class="progress-fill" style="width: {progress}%"></div>
					<div class="progress-thumb" style="left: {progress}%"></div>
				</div>
			</button>
			<span class="time-display">{formatDuration(Math.floor(duration))}</span>
		</div>

		<!-- Playback controls -->
		<div class="control-buttons">
			<!-- Skip back 15s -->
			<button type="button" class="control-btn skip-btn" onclick={() => skip(-15)} title="Back 15 seconds">
				<svg viewBox="0 0 24 24" fill="currentColor" width="24" height="24">
					<path d="M11 18V6l-8.5 6 8.5 6zm.5-6l8.5 6V6l-8.5 6z" transform="scale(-1,1) translate(-24,0)"/>
				</svg>
				<span class="skip-label">15</span>
			</button>

			<!-- Play/Pause -->
			<button type="button" class="control-btn play-btn" onclick={togglePlayPause}>
				{#if isPlaying}
					<svg viewBox="0 0 24 24" fill="currentColor" width="36" height="36">
						<path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z"/>
					</svg>
				{:else}
					<svg viewBox="0 0 24 24" fill="currentColor" width="36" height="36">
						<path d="M8 5v14l11-7z"/>
					</svg>
				{/if}
			</button>

			<!-- Skip forward 30s -->
			<button type="button" class="control-btn skip-btn" onclick={() => skip(30)} title="Forward 30 seconds">
				<svg viewBox="0 0 24 24" fill="currentColor" width="24" height="24">
					<path d="M11 18V6l-8.5 6 8.5 6zm.5-6l8.5 6V6l-8.5 6z"/>
				</svg>
				<span class="skip-label">30</span>
			</button>
		</div>

		<!-- Speed control -->
		<button type="button" class="speed-btn" onclick={cycleSpeed} title="Playback speed">
			{playbackRate}x
		</button>
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

	.hidden-audio {
		position: absolute;
		opacity: 0;
		pointer-events: none;
	}

	.audio-artwork {
		flex-shrink: 0;
		width: 100%;
		max-width: 300px;
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
		max-width: 500px;
		display: flex;
		flex-direction: column;
		align-items: center;
		gap: var(--spacing-md);
	}

	.episode-title {
		font-size: 1.1rem;
		font-weight: 600;
		text-align: center;
		color: var(--color-text);
		line-height: 1.3;
		max-width: 100%;
		overflow: hidden;
		text-overflow: ellipsis;
		display: -webkit-box;
		-webkit-line-clamp: 2;
		-webkit-box-orient: vertical;
	}

	.channel-name {
		font-size: 0.9rem;
		color: var(--color-text-muted);
		text-align: center;
	}

	.progress-container {
		display: flex;
		align-items: center;
		gap: var(--spacing-sm);
		width: 100%;
	}

	.time-display {
		font-size: 0.8rem;
		color: var(--color-text-muted);
		min-width: 50px;
		text-align: center;
		font-variant-numeric: tabular-nums;
	}

	.progress-bar {
		flex: 1;
		height: 24px;
		cursor: pointer;
		background: transparent;
		border: none;
		padding: 8px 0;
		display: flex;
		align-items: center;
	}

	.progress-track {
		position: relative;
		width: 100%;
		height: 4px;
		background: rgba(255, 255, 255, 0.2);
		border-radius: 2px;
	}

	.progress-fill {
		position: absolute;
		left: 0;
		top: 0;
		height: 100%;
		background: var(--color-primary, #8b5cf6);
		border-radius: 2px;
	}

	.progress-thumb {
		position: absolute;
		top: 50%;
		transform: translate(-50%, -50%);
		width: 14px;
		height: 14px;
		background: white;
		border-radius: 50%;
		box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
		opacity: 0;
		transition: opacity 0.2s;
	}

	.progress-bar:hover .progress-thumb {
		opacity: 1;
	}

	.control-buttons {
		display: flex;
		align-items: center;
		justify-content: center;
		gap: var(--spacing-lg);
	}

	.control-btn {
		background: transparent;
		border: none;
		color: white;
		cursor: pointer;
		padding: var(--spacing-sm);
		border-radius: 50%;
		transition: transform 0.1s, background 0.2s;
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.control-btn:hover {
		background: rgba(255, 255, 255, 0.1);
	}

	.control-btn:active {
		transform: scale(0.95);
	}

	.play-btn {
		width: 64px;
		height: 64px;
		background: var(--color-primary, #8b5cf6);
		border-radius: 50%;
	}

	.play-btn:hover {
		background: var(--color-primary-hover, #7c3aed);
	}

	.skip-btn {
		position: relative;
	}

	.skip-label {
		position: absolute;
		font-size: 10px;
		font-weight: 700;
		bottom: 6px;
	}

	.speed-btn {
		background: rgba(255, 255, 255, 0.15);
		border: none;
		color: white;
		padding: 6px 12px;
		border-radius: var(--radius-md);
		font-size: 0.85rem;
		font-weight: 600;
		cursor: pointer;
		transition: background 0.2s;
	}

	.speed-btn:hover {
		background: rgba(255, 255, 255, 0.25);
	}

	@media (max-width: 640px) {
		.audio-player {
			padding: var(--spacing-md);
		}

		.audio-artwork {
			max-width: 200px;
		}

		.episode-title {
			font-size: 1rem;
		}

		.play-btn {
			width: 56px;
			height: 56px;
		}
	}
</style>
