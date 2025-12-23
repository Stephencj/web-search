<script lang="ts">
	/**
	 * Player Content
	 *
	 * Dynamically renders the appropriate playback strategy based on video type
	 * and available resources (cached streams, etc.).
	 */
	import type { VideoItem, StreamInfo } from '$lib/stores/videoPlayer.svelte';
	import type { StrategyType, PlaybackCallbacks } from '../strategies/types';
	import { getBestStrategy } from '../strategies/types';
	import EmbedStrategy from '../strategies/EmbedStrategy.svelte';
	import DirectStreamStrategy from '../strategies/DirectStreamStrategy.svelte';
	import YouTubeApiStrategy from '../strategies/YouTubeApiStrategy.svelte';
	import AudioStrategy from '../strategies/AudioStrategy.svelte';
	import EmbedFallback from '../EmbedFallback.svelte';

	interface Props {
		video: VideoItem;
		streamInfo?: StreamInfo | null;
		startTime?: number;
		autoplay?: boolean;
		preferredStrategy?: StrategyType;
		callbacks?: PlaybackCallbacks;
	}

	let {
		video,
		streamInfo = null,
		startTime = 0,
		autoplay = true,
		preferredStrategy,
		callbacks
	}: Props = $props();

	// Determine the strategy to use
	const activeStrategy = $derived.by(() => {
		// If preferred strategy is specified and valid, use it
		if (preferredStrategy) {
			// Validate preferred strategy is possible
			if (preferredStrategy === 'direct_stream' && streamInfo?.stream_url) {
				return 'direct_stream';
			}
			if (preferredStrategy === 'audio' && (video.contentType === 'audio' || video.platform === 'redbar' || video.platform === 'podcast')) {
				return 'audio';
			}
			if (preferredStrategy === 'youtube_api' && video.platform === 'youtube') {
				return 'youtube_api';
			}
			if (preferredStrategy === 'embed' && video.embedConfig.supportsEmbed) {
				return 'embed';
			}
		}

		// Auto-detect best strategy
		return getBestStrategy(video, !!streamInfo?.stream_url);
	});

	const isAudio = $derived(video.contentType === 'audio' || video.platform === 'redbar' || video.platform === 'podcast');
	const hasDirectStream = $derived(!!streamInfo?.stream_url);
	const canEmbed = $derived(video.embedConfig.supportsEmbed);
</script>

<div class="player-content">
	{#if activeStrategy === 'audio'}
		<AudioStrategy {video} {startTime} {autoplay} {callbacks} />
	{:else if activeStrategy === 'direct_stream' && hasDirectStream}
		<DirectStreamStrategy {video} {startTime} {autoplay} {callbacks} {streamInfo} />
	{:else if activeStrategy === 'youtube_api' && video.platform === 'youtube'}
		<YouTubeApiStrategy {video} {startTime} {callbacks} />
	{:else if activeStrategy === 'embed' && canEmbed}
		<EmbedStrategy {video} {callbacks} />
	{:else}
		<EmbedFallback {video} reason={video.embedConfig.fallbackReason} />
	{/if}
</div>

<style>
	.player-content {
		position: relative;
		width: 100%;
		height: 100%;
		background: black;
	}
</style>
