<script lang="ts">
	import { downloadManager, type DownloadState } from '$lib/stores/downloadManager.svelte';
	import { formatBytes } from '$lib/stores/offlineStorage';

	interface Props {
		platform: string;
		videoId: string;
		title: string;
		thumbnailUrl?: string | null;
		size?: 'sm' | 'md';
	}

	let { platform, videoId, title, thumbnailUrl = null, size = 'md' }: Props = $props();

	let isOffline = $state(false);
	let downloadState = $state<DownloadState | null>(null);

	// Check if video is already downloaded
	$effect(() => {
		downloadManager.checkOffline(platform, videoId).then((offline) => {
			isOffline = offline;
		});
	});

	// Track download state
	$effect(() => {
		downloadState = downloadManager.getDownloadState(platform, videoId) || null;
	});

	const isDownloading = $derived(downloadState?.status === 'downloading');
	const isQueued = $derived(downloadState?.status === 'queued');
	const isFailed = $derived(downloadState?.status === 'failed');
	const progress = $derived(downloadState?.progress || 0);

	function handleClick() {
		if (isOffline) {
			// Already downloaded - could show options menu
			return;
		}

		if (isDownloading || isQueued) {
			// Cancel download
			downloadManager.cancelDownload(platform, videoId);
			return;
		}

		// Queue download
		downloadManager.queueDownload({
			platform,
			videoId,
			title,
			thumbnailUrl
		});
	}

	function handleRemove() {
		downloadManager.removeOfflineVideo(platform, videoId);
		isOffline = false;
	}

	const buttonClass = $derived(
		size === 'sm'
			? 'p-1.5 rounded-md text-xs'
			: 'p-2 rounded-lg text-sm'
	);
</script>

{#if isOffline}
	<!-- Downloaded indicator with remove option -->
	<button
		type="button"
		class="{buttonClass} bg-green-500/20 text-green-400 hover:bg-red-500/20 hover:text-red-400 transition-colors group"
		title="Downloaded - Click to remove"
		onclick={handleRemove}
	>
		<span class="group-hover:hidden">
			<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7" />
			</svg>
		</span>
		<span class="hidden group-hover:inline">
			<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
				<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-7 7-7-7" />
			</svg>
		</span>
	</button>
{:else if isDownloading}
	<!-- Downloading with progress -->
	<button
		type="button"
		class="{buttonClass} bg-blue-500/20 text-blue-400 hover:bg-red-500/20 hover:text-red-400 transition-colors relative"
		title="Downloading... Click to cancel"
		onclick={handleClick}
	>
		<div class="relative w-4 h-4">
			<svg class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
				<circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
				<path
					class="opacity-75"
					fill="currentColor"
					d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
				/>
			</svg>
		</div>
		{#if size === 'md'}
			<span class="ml-1 text-xs">{progress}%</span>
		{/if}
	</button>
{:else if isQueued}
	<!-- Queued -->
	<button
		type="button"
		class="{buttonClass} bg-yellow-500/20 text-yellow-400 hover:bg-red-500/20 hover:text-red-400 transition-colors"
		title="Queued - Click to cancel"
		onclick={handleClick}
	>
		<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
			<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
		</svg>
	</button>
{:else if isFailed}
	<!-- Failed - retry -->
	<button
		type="button"
		class="{buttonClass} bg-red-500/20 text-red-400 hover:bg-red-500/30 transition-colors"
		title="Download failed - Click to retry"
		onclick={handleClick}
	>
		<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
			<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
		</svg>
	</button>
{:else}
	<!-- Download button -->
	<button
		type="button"
		class="{buttonClass} bg-zinc-700/50 text-zinc-300 hover:bg-zinc-600/50 hover:text-white transition-colors"
		title="Download for offline"
		onclick={handleClick}
	>
		<svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
			<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
		</svg>
	</button>
{/if}
