<script lang="ts">
	/**
	 * Queue Panel
	 *
	 * Displays the playlist/queue of videos with thumbnails.
	 * Allows jumping to any video in the queue.
	 */
	import { videoPlayer, formatDuration, type VideoItem } from '$lib/stores/videoPlayer.svelte';

	interface Props {
		onVideoSelect?: (index: number) => void;
		compact?: boolean;
	}

	let { onVideoSelect, compact = false }: Props = $props();

	// State
	let expanded = $state(true);

	// Derived from store
	const queue = $derived(videoPlayer.queue);
	const currentIndex = $derived(videoPlayer.currentIndex);
	const upNextCount = $derived(queue.length - currentIndex - 1);

	function handleVideoClick(index: number) {
		if (onVideoSelect) {
			onVideoSelect(index);
		} else {
			videoPlayer.goToIndex(index);
		}
	}

	function getVideoStatus(index: number): 'played' | 'current' | 'upcoming' {
		if (index < currentIndex) return 'played';
		if (index === currentIndex) return 'current';
		return 'upcoming';
	}
</script>

{#if queue.length > 1}
	<div class="queue-panel" class:compact>
		<button class="queue-header" onclick={() => (expanded = !expanded)}>
			<span class="header-title">
				Up Next
				{#if upNextCount > 0}
					<span class="queue-count">({upNextCount})</span>
				{/if}
			</span>
			<span class="expand-icon">{expanded ? '−' : '+'}</span>
		</button>

		{#if expanded}
			<div class="queue-content">
				<ul class="queue-list">
					{#each queue as video, index (index)}
						{@const status = getVideoStatus(index)}
						<li class="queue-item" class:current={status === 'current'} class:played={status === 'played'}>
							<button
								class="queue-btn"
								onclick={() => handleVideoClick(index)}
								disabled={status === 'current'}
							>
								<span class="queue-index">{index + 1}</span>
								{#if video.thumbnailUrl}
									<img
										src={video.thumbnailUrl}
										alt=""
										class="queue-thumbnail"
										loading="lazy"
									/>
								{:else}
									<div class="queue-thumbnail placeholder"></div>
								{/if}
								<div class="queue-info">
									<span class="queue-title">{video.title}</span>
									{#if video.channelName}
										<span class="queue-channel">{video.channelName}</span>
									{/if}
								</div>
								{#if video.duration}
									<span class="queue-duration">{formatDuration(video.duration)}</span>
								{/if}
								{#if status === 'current'}
									<span class="now-playing">
										<span class="playing-icon"></span>
									</span>
								{/if}
							</button>
						</li>
					{/each}
				</ul>
			</div>
		{/if}
	</div>
{/if}

<style>
	.queue-panel {
		background: var(--color-bg-tertiary, #1a1a1a);
		border-radius: var(--radius-sm);
		overflow: hidden;
		margin-top: var(--spacing-md);
	}

	.queue-panel.compact {
		margin-top: var(--spacing-sm);
	}

	.queue-header {
		width: 100%;
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: var(--spacing-sm) var(--spacing-md);
		background: none;
		border: none;
		color: var(--color-text);
		cursor: pointer;
		font-size: 0.875rem;
		font-weight: 600;
	}

	.queue-header:hover {
		background: var(--color-bg-hover, rgba(255, 255, 255, 0.05));
	}

	.header-title {
		display: flex;
		align-items: center;
		gap: var(--spacing-xs);
	}

	.queue-count {
		color: var(--color-text-secondary);
		font-weight: normal;
	}

	.expand-icon {
		font-size: 1.2rem;
		color: var(--color-text-secondary);
	}

	.queue-content {
		padding: 0 var(--spacing-sm) var(--spacing-sm);
	}

	.queue-list {
		list-style: none;
		margin: 0;
		padding: 0;
		max-height: 280px;
		overflow-y: auto;
	}

	.compact .queue-list {
		max-height: 180px;
	}

	.queue-item {
		border-radius: var(--radius-sm);
		margin-bottom: 2px;
	}

	.queue-item.current {
		background: var(--color-primary-alpha, rgba(100, 150, 255, 0.15));
	}

	.queue-item.played {
		opacity: 0.5;
	}

	.queue-btn {
		width: 100%;
		display: flex;
		align-items: center;
		gap: var(--spacing-sm);
		padding: var(--spacing-xs);
		background: none;
		border: none;
		color: var(--color-text);
		cursor: pointer;
		text-align: left;
		border-radius: var(--radius-sm);
	}

	.queue-btn:hover:not(:disabled) {
		background: var(--color-bg-hover, rgba(255, 255, 255, 0.05));
	}

	.queue-btn:disabled {
		cursor: default;
	}

	.queue-index {
		flex-shrink: 0;
		width: 20px;
		font-size: 0.75rem;
		color: var(--color-text-muted);
		text-align: center;
	}

	.queue-thumbnail {
		flex-shrink: 0;
		width: 64px;
		height: 36px;
		object-fit: cover;
		border-radius: var(--radius-xs);
		background: var(--color-bg-secondary);
	}

	.queue-thumbnail.placeholder {
		display: flex;
		align-items: center;
		justify-content: center;
	}

	.compact .queue-thumbnail {
		width: 48px;
		height: 27px;
	}

	.queue-info {
		flex: 1;
		min-width: 0;
		display: flex;
		flex-direction: column;
		gap: 2px;
	}

	.queue-title {
		font-size: 0.8125rem;
		font-weight: 500;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.queue-channel {
		font-size: 0.7rem;
		color: var(--color-text-secondary);
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.queue-duration {
		flex-shrink: 0;
		font-size: 0.75rem;
		font-family: monospace;
		color: var(--color-text-secondary);
	}

	.now-playing {
		flex-shrink: 0;
		display: flex;
		align-items: center;
		justify-content: center;
		width: 24px;
	}

	.playing-icon {
		display: flex;
		align-items: flex-end;
		gap: 2px;
		height: 14px;
	}

	.playing-icon::before,
	.playing-icon::after {
		content: '';
		display: block;
		width: 3px;
		background: var(--color-primary);
		animation: playing-bar 0.8s ease-in-out infinite;
	}

	.playing-icon::before {
		height: 60%;
		animation-delay: 0s;
	}

	.playing-icon::after {
		height: 100%;
		animation-delay: 0.3s;
	}

	@keyframes playing-bar {
		0%, 100% {
			transform: scaleY(0.5);
		}
		50% {
			transform: scaleY(1);
		}
	}

	/* Scrollbar styling */
	.queue-list::-webkit-scrollbar {
		width: 6px;
	}

	.queue-list::-webkit-scrollbar-track {
		background: transparent;
	}

	.queue-list::-webkit-scrollbar-thumb {
		background: var(--color-border);
		border-radius: 3px;
	}

	.queue-list::-webkit-scrollbar-thumb:hover {
		background: var(--color-text-muted);
	}
</style>
