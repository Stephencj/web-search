<script lang="ts">
	/**
	 * Player Info
	 *
	 * Shows video title, channel info, and external link.
	 */
	import type { VideoItem } from '$lib/stores/videoPlayer.svelte';
	import { getPlatformName } from '$lib/utils/embedUrl';

	interface Props {
		video: VideoItem;
		compact?: boolean;
	}

	let { video, compact = false }: Props = $props();

	const platformName = $derived(getPlatformName(video.platform));
</script>

<div class="player-info" class:compact>
	<h2 class="video-title">{video.title}</h2>
	<div class="video-meta">
		{#if video.channelName}
			{#if video.channelUrl}
				<a href={video.channelUrl} target="_blank" rel="noopener noreferrer" class="channel-link">
					{video.channelName}
				</a>
			{:else}
				<span class="channel-name">{video.channelName}</span>
			{/if}
		{/if}
		<a href={video.videoUrl} target="_blank" rel="noopener noreferrer" class="external-link">
			Open on {platformName}
		</a>
	</div>
</div>

<style>
	.player-info {
		padding: var(--spacing-md);
		background: var(--color-bg-secondary);
	}

	.player-info.compact {
		padding: var(--spacing-sm);
	}

	.video-title {
		font-size: 1.1rem;
		font-weight: 600;
		margin: 0 0 var(--spacing-sm) 0;
		color: var(--color-text);
		line-height: 1.3;
		display: -webkit-box;
		-webkit-line-clamp: 2;
		-webkit-box-orient: vertical;
		overflow: hidden;
	}

	.compact .video-title {
		font-size: 0.9rem;
		-webkit-line-clamp: 1;
		margin-bottom: var(--spacing-xs);
	}

	.video-meta {
		display: flex;
		align-items: center;
		gap: var(--spacing-md);
		font-size: 0.875rem;
	}

	.compact .video-meta {
		font-size: 0.75rem;
		gap: var(--spacing-sm);
	}

	.channel-link,
	.channel-name {
		color: var(--color-text-secondary);
	}

	.channel-link:hover {
		color: var(--color-primary);
	}

	.external-link {
		color: var(--color-primary);
		text-decoration: none;
	}

	.external-link:hover {
		text-decoration: underline;
	}
</style>
