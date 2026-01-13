<script lang="ts">
	/**
	 * Player Info
	 *
	 * Shows video title, channel info, metadata, and external link.
	 */
	import type { VideoItem } from '$lib/stores/videoPlayer.svelte';
	import { getPlatformName } from '$lib/utils/embedUrl';

	interface Props {
		video: VideoItem;
		compact?: boolean;
	}

	let { video, compact = false }: Props = $props();

	const platformName = $derived(getPlatformName(video.platform));

	// Format view/like counts (e.g., 1.2M, 500K)
	function formatCount(count: number | null | undefined): string {
		if (!count) return '';
		if (count >= 1_000_000) {
			return `${(count / 1_000_000).toFixed(1)}M`;
		}
		if (count >= 1_000) {
			return `${(count / 1_000).toFixed(1)}K`;
		}
		return count.toLocaleString();
	}

	// Format date relative to now
	function formatDate(dateStr: string | null | undefined): string {
		if (!dateStr) return '';
		const date = new Date(dateStr);
		const now = new Date();
		const diffMs = now.getTime() - date.getTime();
		const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24));

		if (diffDays === 0) return 'Today';
		if (diffDays === 1) return 'Yesterday';
		if (diffDays < 7) return `${diffDays} days ago`;
		if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`;
		if (diffDays < 365) return `${Math.floor(diffDays / 30)} months ago`;
		return `${Math.floor(diffDays / 365)} years ago`;
	}

	// Expandable description state
	let descriptionExpanded = $state(false);

	function toggleDescription() {
		descriptionExpanded = !descriptionExpanded;
	}

	// Truncate description
	const truncatedDescription = $derived(() => {
		if (!video.description) return '';
		if (video.description.length <= 150) return video.description;
		return video.description.slice(0, 150) + '...';
	});

	const showExpandButton = $derived(video.description && video.description.length > 150);
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

		{#if !compact}
			<div class="meta-stats">
				{#if video.viewCount}
					<span class="stat" title="{video.viewCount.toLocaleString()} views">
						<svg viewBox="0 0 24 24" fill="currentColor" width="14" height="14">
							<path d="M12 4.5C7 4.5 2.73 7.61 1 12c1.73 4.39 6 7.5 11 7.5s9.27-3.11 11-7.5c-1.73-4.39-6-7.5-11-7.5zM12 17c-2.76 0-5-2.24-5-5s2.24-5 5-5 5 2.24 5 5-2.24 5-5 5zm0-8c-1.66 0-3 1.34-3 3s1.34 3 3 3 3-1.34 3-3-1.34-3-3-3z"/>
						</svg>
						{formatCount(video.viewCount)}
					</span>
				{/if}
				{#if video.likeCount}
					<span class="stat" title="{video.likeCount.toLocaleString()} likes">
						<svg viewBox="0 0 24 24" fill="currentColor" width="14" height="14">
							<path d="M1 21h4V9H1v12zm22-11c0-1.1-.9-2-2-2h-6.31l.95-4.57.03-.32c0-.41-.17-.79-.44-1.06L14.17 1 7.59 7.59C7.22 7.95 7 8.45 7 9v10c0 1.1.9 2 2 2h9c.83 0 1.54-.5 1.84-1.22l3.02-7.05c.09-.23.14-.47.14-.73v-2z"/>
						</svg>
						{formatCount(video.likeCount)}
					</span>
				{/if}
				{#if video.uploadDate}
					<span class="stat upload-date">
						{formatDate(video.uploadDate)}
					</span>
				{/if}
			</div>
		{/if}

		<a href={video.videoUrl} target="_blank" rel="noopener noreferrer" class="external-link">
			Open on {platformName}
		</a>
	</div>

	{#if !compact && video.description}
		<div class="description-section">
			<p class="description" class:expanded={descriptionExpanded}>
				{#if descriptionExpanded}
					{video.description}
				{:else}
					{truncatedDescription()}
				{/if}
			</p>
			{#if showExpandButton}
				<button class="expand-btn" onclick={toggleDescription}>
					{descriptionExpanded ? 'Show less' : 'Show more'}
				</button>
			{/if}
		</div>
	{/if}
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
		flex-wrap: wrap;
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

	.meta-stats {
		display: flex;
		align-items: center;
		gap: var(--spacing-md);
	}

	.stat {
		display: flex;
		align-items: center;
		gap: 4px;
		color: var(--color-text-secondary);
		font-size: 0.8rem;
	}

	.stat svg {
		opacity: 0.7;
	}

	.upload-date {
		color: var(--color-text-muted);
	}

	.external-link {
		color: var(--color-primary);
		text-decoration: none;
		margin-left: auto;
	}

	.external-link:hover {
		text-decoration: underline;
	}

	.description-section {
		margin-top: var(--spacing-md);
		padding-top: var(--spacing-md);
		border-top: 1px solid var(--color-border);
	}

	.description {
		margin: 0;
		font-size: 0.875rem;
		color: var(--color-text-secondary);
		line-height: 1.5;
		white-space: pre-wrap;
		word-break: break-word;
	}

	.description.expanded {
		max-height: none;
	}

	.expand-btn {
		margin-top: var(--spacing-sm);
		padding: 0;
		background: none;
		border: none;
		color: var(--color-primary);
		font-size: 0.8rem;
		cursor: pointer;
	}

	.expand-btn:hover {
		text-decoration: underline;
	}
</style>
