<script lang="ts">
	/**
	 * YouTube API Strategy
	 *
	 * Uses YouTube IFrame API for playback control and end detection.
	 * Essential for queue auto-advance since embed iframes don't emit events.
	 * Medium startup time (1-3s for API load).
	 */
	import type { StrategyProps } from './types';
	import {
		loadYouTubeAPI,
		createYouTubePlayer,
		type YouTubePlayer,
		YT_PLAYER_STATE
	} from '$lib/utils/youtubeApi';
	import { videoPlayer } from '$lib/stores/videoPlayer.svelte';

	interface Props extends StrategyProps {}

	let { video, startTime = 0, callbacks }: Props = $props();

	let ytPlayer: YouTubePlayer | null = null;
	let isReady = $state(false);
	let isLoading = $state(true);
	let containerId = $derived(`yt-player-${video.videoId}`);

	async function initPlayer() {
		isLoading = true;
		isReady = false;

		try {
			await loadYouTubeAPI();

			// Clean up existing player
			if (ytPlayer) {
				try {
					ytPlayer.destroy();
				} catch {}
				ytPlayer = null;
			}

			// Wait for DOM element
			await new Promise((resolve) => setTimeout(resolve, 150));

			const container = document.getElementById(containerId);
			if (!container) {
				console.warn('[YouTubeApiStrategy] Container not found');
				callbacks?.onError?.('Player container not found');
				return;
			}

			ytPlayer = createYouTubePlayer(containerId, video.videoId, {
				onReady: () => {
					isReady = true;
					isLoading = false;
					videoPlayer.updateMediaMetadata();

					// Seek to start time
					if (startTime > 0 && ytPlayer) {
						try {
							ytPlayer.seekTo(startTime, true);
						} catch {}
					}

					// Start playback
					if (ytPlayer) {
						ytPlayer.playVideo();
					}

					callbacks?.onReady?.();
				},
				onStateChange: (state) => {
					if (state === YT_PLAYER_STATE.PLAYING) {
						videoPlayer.setPlaybackState(true);
						callbacks?.onPlay?.();
					} else if (state === YT_PLAYER_STATE.PAUSED) {
						videoPlayer.setPlaybackState(false);
						callbacks?.onPause?.();
					} else if (state === YT_PLAYER_STATE.BUFFERING) {
						callbacks?.onBuffering?.();
					}

					// Update position when playing
					if (state === YT_PLAYER_STATE.PLAYING && ytPlayer) {
						const time = ytPlayer.getCurrentTime();
						const dur = ytPlayer.getDuration();
						videoPlayer.updatePosition(time, dur);
						callbacks?.onTimeUpdate?.(time, dur);
					}
				},
				onEnded: () => {
					videoPlayer.setPlaybackState(false);
					callbacks?.onEnded?.();
				},
				onError: (error) => {
					console.warn('[YouTubeApiStrategy] Player error:', error);
					callbacks?.onError?.(`YouTube error: ${error}`);
				}
			});
		} catch (error) {
			isLoading = false;
			console.warn('[YouTubeApiStrategy] Init failed:', error);
			callbacks?.onError?.('Failed to initialize YouTube player');
		}
	}

	// Initialize on mount
	$effect(() => {
		if (video) {
			initPlayer();
		}

		return () => {
			if (ytPlayer) {
				try {
					ytPlayer.destroy();
				} catch {}
				ytPlayer = null;
			}
		};
	});

	// Export player access
	export function getYtPlayer(): YouTubePlayer | null {
		return ytPlayer;
	}

	export function isPlayerReady(): boolean {
		return isReady;
	}
</script>

<div class="yt-player-wrapper">
	{#if isLoading || !isReady}
		<div class="loading-spinner">
			<div class="spinner"></div>
		</div>
	{/if}
	<div id={containerId} class="yt-player-container" class:loaded={isReady}></div>
</div>

<style>
	.yt-player-wrapper {
		position: relative;
		width: 100%;
		height: 100%;
	}

	.yt-player-container {
		position: absolute;
		inset: 0;
		width: 100%;
		height: 100%;
		opacity: 0;
		transition: opacity 0.3s ease;
	}

	.yt-player-container.loaded {
		opacity: 1;
	}

	.loading-spinner {
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
		border: 3px solid var(--color-border);
		border-top-color: var(--color-primary);
		border-radius: 50%;
		animation: spin 1s linear infinite;
	}

	@keyframes spin {
		to {
			transform: rotate(360deg);
		}
	}
</style>
