<script lang="ts">
	/**
	 * Chapter List
	 *
	 * Displays chapters for a video/podcast with clickable timestamps.
	 * Supports generating chapters via transcription.
	 */
	import { apiClient, type Chapter, type TranscriptionStatus } from '$lib/api/client';

	interface Props {
		feedItemId: number;
		currentTime?: number;
		onSeek?: (seconds: number) => void;
	}

	let { feedItemId, currentTime = 0, onSeek }: Props = $props();

	// State
	let chapters = $state<Chapter[]>([]);
	let transcriptionStatus = $state<TranscriptionStatus | null>(null);
	let loading = $state(false);
	let generating = $state(false);
	let error = $state<string | null>(null);
	let expanded = $state(true);
	let pollInterval = $state<number | null>(null);

	// Current chapter based on time
	const currentChapter = $derived(() => {
		if (!chapters.length) return null;
		for (let i = chapters.length - 1; i >= 0; i--) {
			if (currentTime >= chapters[i].start_seconds) {
				return chapters[i];
			}
		}
		return null;
	});

	// Load chapters and status
	async function loadData() {
		loading = true;
		error = null;

		try {
			const [chaptersRes, statusRes] = await Promise.all([
				apiClient.getChapters(feedItemId),
				apiClient.getTranscriptionStatus(feedItemId),
			]);

			chapters = chaptersRes.chapters;
			transcriptionStatus = statusRes;

			// Start polling if processing
			if (statusRes.status === 'processing') {
				startPolling();
			}
		} catch (e) {
			error = 'Failed to load chapters';
			console.error(e);
		} finally {
			loading = false;
		}
	}

	// Start transcription
	async function startTranscription() {
		generating = true;
		error = null;

		try {
			await apiClient.startTranscription(feedItemId, { generate_chapters: true });
			transcriptionStatus = { feed_item_id: feedItemId, status: 'processing', progress: 0 };
			startPolling();
		} catch (e) {
			error = 'Failed to start transcription';
			console.error(e);
		} finally {
			generating = false;
		}
	}

	// Poll for transcription status
	function startPolling() {
		if (pollInterval) return;

		pollInterval = window.setInterval(async () => {
			try {
				const status = await apiClient.getTranscriptionStatus(feedItemId);
				transcriptionStatus = status;

				if (status.status === 'completed') {
					stopPolling();
					// Reload chapters
					const chaptersRes = await apiClient.getChapters(feedItemId);
					chapters = chaptersRes.chapters;
				} else if (status.status === 'failed') {
					stopPolling();
					error = status.error_message || 'Transcription failed';
				}
			} catch (e) {
				console.error('Status poll error:', e);
			}
		}, 3000);
	}

	function stopPolling() {
		if (pollInterval) {
			window.clearInterval(pollInterval);
			pollInterval = null;
		}
	}

	function handleChapterClick(chapter: Chapter) {
		onSeek?.(chapter.start_seconds);
	}

	function formatTime(seconds: number): string {
		const hrs = Math.floor(seconds / 3600);
		const mins = Math.floor((seconds % 3600) / 60);
		const secs = Math.floor(seconds % 60);

		if (hrs > 0) {
			return `${hrs}:${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
		}
		return `${mins}:${secs.toString().padStart(2, '0')}`;
	}

	// Load on mount
	$effect(() => {
		if (feedItemId) {
			loadData();
		}

		return () => {
			stopPolling();
		};
	});
</script>

<div class="chapter-list">
	<button class="chapter-header" onclick={() => (expanded = !expanded)}>
		<span class="header-title">
			Chapters
			{#if chapters.length > 0}
				<span class="chapter-count">({chapters.length})</span>
			{/if}
		</span>
		<span class="expand-icon" class:expanded>{expanded ? '−' : '+'}</span>
	</button>

	{#if expanded}
		<div class="chapter-content">
			{#if loading}
				<div class="status-message">Loading...</div>
			{:else if error}
				<div class="status-message error">{error}</div>
			{:else if transcriptionStatus?.status === 'processing'}
				<div class="status-message">
					<div class="progress-bar">
						<div class="progress-fill" style="width: {transcriptionStatus.progress || 0}%"></div>
					</div>
					<span>Transcribing... {transcriptionStatus.progress || 0}%</span>
				</div>
			{:else if chapters.length === 0}
				<div class="no-chapters">
					<p>No chapters available</p>
					{#if transcriptionStatus?.status !== 'completed'}
						<button
							class="generate-btn"
							onclick={startTranscription}
							disabled={generating}
						>
							{generating ? 'Starting...' : 'Generate Chapters'}
						</button>
						<p class="hint">Uses AI to transcribe and create chapter timestamps</p>
					{/if}
				</div>
			{:else}
				<ul class="chapters">
					{#each chapters as chapter (chapter.id)}
						<li
							class="chapter-item"
							class:active={currentChapter?.id === chapter.id}
						>
							<button
								class="chapter-btn"
								onclick={() => handleChapterClick(chapter)}
							>
								<span class="chapter-time">{formatTime(chapter.start_seconds)}</span>
								<span class="chapter-title">{chapter.title}</span>
								{#if chapter.confidence && chapter.confidence < 0.8}
									<span class="low-confidence" title="Low confidence match">?</span>
								{/if}
							</button>
						</li>
					{/each}
				</ul>
			{/if}
		</div>
	{/if}
</div>

<style>
	.chapter-list {
		background: var(--color-bg-tertiary, #1a1a1a);
		border-radius: var(--radius-sm);
		overflow: hidden;
	}

	.chapter-header {
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

	.chapter-header:hover {
		background: var(--color-bg-hover, rgba(255, 255, 255, 0.05));
	}

	.header-title {
		display: flex;
		align-items: center;
		gap: var(--spacing-xs);
	}

	.chapter-count {
		color: var(--color-text-secondary);
		font-weight: normal;
	}

	.expand-icon {
		font-size: 1.2rem;
		color: var(--color-text-secondary);
		transition: transform 0.2s ease;
	}

	.chapter-content {
		padding: 0 var(--spacing-md) var(--spacing-md);
	}

	.status-message {
		padding: var(--spacing-sm);
		color: var(--color-text-secondary);
		font-size: 0.875rem;
		text-align: center;
	}

	.status-message.error {
		color: var(--color-error, #ff4444);
	}

	.progress-bar {
		width: 100%;
		height: 4px;
		background: var(--color-bg-secondary);
		border-radius: 2px;
		margin-bottom: var(--spacing-xs);
		overflow: hidden;
	}

	.progress-fill {
		height: 100%;
		background: var(--color-primary);
		transition: width 0.3s ease;
	}

	.no-chapters {
		text-align: center;
		padding: var(--spacing-md);
	}

	.no-chapters p {
		margin: 0 0 var(--spacing-sm);
		color: var(--color-text-secondary);
		font-size: 0.875rem;
	}

	.generate-btn {
		padding: var(--spacing-sm) var(--spacing-md);
		background: var(--color-primary);
		color: var(--color-text-on-primary, white);
		border: none;
		border-radius: var(--radius-sm);
		cursor: pointer;
		font-size: 0.875rem;
		font-weight: 500;
	}

	.generate-btn:hover:not(:disabled) {
		opacity: 0.9;
	}

	.generate-btn:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.hint {
		font-size: 0.75rem;
		opacity: 0.7;
		margin-top: var(--spacing-sm);
	}

	.chapters {
		list-style: none;
		margin: 0;
		padding: 0;
		max-height: 200px;
		overflow-y: auto;
	}

	.chapter-item {
		border-radius: var(--radius-xs);
	}

	.chapter-item.active {
		background: var(--color-primary-alpha, rgba(100, 150, 255, 0.15));
	}

	.chapter-btn {
		width: 100%;
		display: flex;
		align-items: center;
		gap: var(--spacing-sm);
		padding: var(--spacing-xs) var(--spacing-sm);
		background: none;
		border: none;
		color: var(--color-text);
		cursor: pointer;
		text-align: left;
		font-size: 0.8125rem;
	}

	.chapter-btn:hover {
		background: var(--color-bg-hover, rgba(255, 255, 255, 0.05));
	}

	.chapter-time {
		flex-shrink: 0;
		font-family: monospace;
		color: var(--color-primary);
		font-size: 0.75rem;
	}

	.chapter-title {
		flex: 1;
		overflow: hidden;
		text-overflow: ellipsis;
		white-space: nowrap;
	}

	.low-confidence {
		flex-shrink: 0;
		color: var(--color-warning, #ffa500);
		font-size: 0.75rem;
	}
</style>
