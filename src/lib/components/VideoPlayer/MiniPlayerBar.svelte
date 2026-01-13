<script lang="ts">
	/**
	 * Mini Player Bar
	 *
	 * A sticky footer bar that shows when a video is playing but the modal is closed.
	 * Designed for iOS compatibility - lets native video player control playback
	 * while showing progress and controls for browsing other content.
	 */
	import { videoPlayer, formatDuration } from '$lib/stores/videoPlayer.svelte';

	// Derived values from store
	const video = $derived(videoPlayer.currentVideo);
	const mode = $derived(videoPlayer.mode);
	const isPlaying = $derived(videoPlayer.isPlaying);
	const currentTime = $derived(videoPlayer.currentTime);
	const duration = $derived(videoPlayer.duration);

	// Show bar when video exists and modal is closed (pip mode or playing in background)
	const isVisible = $derived(video !== null && mode === 'pip');

	// Progress percentage
	const progress = $derived(duration > 0 ? (currentTime / duration) * 100 : 0);

	// Truncate title for display
	const truncatedTitle = $derived(() => {
		if (!video?.title) return '';
		return video.title.length > 50 ? video.title.slice(0, 50) + '...' : video.title;
	});

	function handlePlayPause() {
		if (isPlaying) {
			videoPlayer.pause();
		} else {
			videoPlayer.play();
		}
	}

	function handleOpenModal() {
		videoPlayer.switchToModal();
	}

	function handleClose() {
		videoPlayer.close();
	}

	function handleProgressClick(e: MouseEvent) {
		const bar = e.currentTarget as HTMLElement;
		const rect = bar.getBoundingClientRect();
		const percent = (e.clientX - rect.left) / rect.width;
		const newTime = percent * duration;
		videoPlayer.seekTo(newTime);
	}

	function handleKeydown(e: KeyboardEvent) {
		if (e.key === ' ' || e.key === 'k') {
			e.preventDefault();
			handlePlayPause();
		} else if (e.key === 'Escape') {
			handleClose();
		}
	}
</script>

{#if isVisible && video}
	<div
		class="mini-player-bar"
		role="region"
		aria-label="Now playing"
		onkeydown={handleKeydown}
	>
		<!-- Progress bar (clickable) -->
		<button
			class="progress-track"
			onclick={handleProgressClick}
			aria-label="Seek in video"
		>
			<div class="progress-fill" style="width: {progress}%"></div>
		</button>

		<div class="bar-content">
			<!-- Play/Pause button -->
			<button
				class="control-btn play-btn"
				onclick={handlePlayPause}
				aria-label={isPlaying ? 'Pause' : 'Play'}
			>
				{#if isPlaying}
					<svg viewBox="0 0 24 24" fill="currentColor" width="24" height="24">
						<path d="M6 19h4V5H6v14zm8-14v14h4V5h-4z" />
					</svg>
				{:else}
					<svg viewBox="0 0 24 24" fill="currentColor" width="24" height="24">
						<path d="M8 5v14l11-7z" />
					</svg>
				{/if}
			</button>

			<!-- Video info (clickable to open modal) -->
			<button class="video-info" onclick={handleOpenModal}>
				{#if video.thumbnailUrl}
					<img
						src={video.thumbnailUrl}
						alt=""
						class="thumbnail"
					/>
				{/if}
				<div class="title-container">
					<span class="title">{truncatedTitle()}</span>
					<span class="time">
						{formatDuration(Math.floor(currentTime))}
						{#if duration > 0}
							/ {formatDuration(Math.floor(duration))}
						{/if}
					</span>
				</div>
			</button>

			<!-- Close button -->
			<button
				class="control-btn close-btn"
				onclick={handleClose}
				aria-label="Close player"
			>
				<svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
					<path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z" />
				</svg>
			</button>
		</div>
	</div>
{/if}

<style>
	.mini-player-bar {
		position: fixed;
		bottom: 0;
		left: 0;
		right: 0;
		z-index: 1000;
		background: var(--color-bg-secondary);
		border-top: 1px solid var(--color-border);
		box-shadow: 0 -4px 12px rgba(0, 0, 0, 0.15);
		/* Safe area for iOS notch/home indicator */
		padding-bottom: env(safe-area-inset-bottom, 0);
	}

	.progress-track {
		width: 100%;
		height: 4px;
		background: var(--color-border);
		cursor: pointer;
		border: none;
		padding: 0;
		display: block;
		transition: height 0.15s ease;
	}

	.progress-track:hover {
		height: 6px;
	}

	.progress-fill {
		height: 100%;
		background: var(--color-primary);
		transition: width 0.1s linear;
	}

	.bar-content {
		display: flex;
		align-items: center;
		gap: var(--spacing-sm);
		padding: var(--spacing-sm) var(--spacing-md);
		min-height: 56px;
	}

	.control-btn {
		display: flex;
		align-items: center;
		justify-content: center;
		background: transparent;
		border: none;
		color: var(--color-text);
		cursor: pointer;
		padding: var(--spacing-xs);
		border-radius: var(--radius-sm);
		flex-shrink: 0;
		-webkit-tap-highlight-color: transparent;
	}

	.control-btn:hover {
		background: var(--color-bg-hover);
	}

	.control-btn:active {
		background: var(--color-bg-active);
	}

	.play-btn {
		width: 44px;
		height: 44px;
	}

	.close-btn {
		width: 36px;
		height: 36px;
		color: var(--color-text-secondary);
	}

	.video-info {
		flex: 1;
		display: flex;
		align-items: center;
		gap: var(--spacing-sm);
		background: transparent;
		border: none;
		cursor: pointer;
		padding: var(--spacing-xs);
		border-radius: var(--radius-sm);
		text-align: left;
		min-width: 0;
		-webkit-tap-highlight-color: transparent;
	}

	.video-info:hover {
		background: var(--color-bg-hover);
	}

	.thumbnail {
		width: 48px;
		height: 27px;
		object-fit: cover;
		border-radius: var(--radius-sm);
		flex-shrink: 0;
	}

	.title-container {
		display: flex;
		flex-direction: column;
		min-width: 0;
		gap: 2px;
	}

	.title {
		font-size: 0.875rem;
		font-weight: 500;
		color: var(--color-text);
		white-space: nowrap;
		overflow: hidden;
		text-overflow: ellipsis;
	}

	.time {
		font-size: 0.75rem;
		color: var(--color-text-secondary);
	}

	/* Mobile optimizations */
	@media (max-width: 640px) {
		.bar-content {
			padding: var(--spacing-xs) var(--spacing-sm);
		}

		.thumbnail {
			display: none;
		}

		.title {
			font-size: 0.8rem;
		}
	}
</style>
