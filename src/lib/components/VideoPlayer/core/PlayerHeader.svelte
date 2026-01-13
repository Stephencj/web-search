<script lang="ts">
	/**
	 * Player Header
	 *
	 * Common header for both Modal and PiP players.
	 * Shows platform badge, queue controls, and action buttons.
	 */
	import { videoPlayer, formatDuration } from '$lib/stores/videoPlayer.svelte';
	import { getPlatformName, getPlatformColor } from '$lib/utils/embedUrl';
	import type { StreamInfo } from '$lib/stores/videoPlayer.svelte';
	import QualitySelector, { type QualityOption } from './QualitySelector.svelte';

	interface Props {
		compact?: boolean;
		streamInfo?: StreamInfo | null;
		useDirectStream?: boolean;
		onToggleDirectStream?: () => void;
		onToggleTheaterMode?: () => void;
		onSwitchToPiP?: () => void;
		onSwitchToModal?: () => void;
		onClose?: () => void;
		theaterMode?: boolean;
		showTheaterToggle?: boolean;
		showPiPToggle?: boolean;
		showModalToggle?: boolean;
		// Quality selector props
		currentQuality?: string | null;
		availableQualities?: QualityOption[];
		onQualityChange?: (quality: string) => void;
		showQualitySelector?: boolean;
		qualityLoading?: boolean;
	}

	let {
		compact = false,
		streamInfo = null,
		useDirectStream = false,
		onToggleDirectStream,
		onToggleTheaterMode,
		onSwitchToPiP,
		onSwitchToModal,
		onClose,
		theaterMode = false,
		showTheaterToggle = true,
		showPiPToggle = true,
		showModalToggle = false,
		// Quality selector defaults
		currentQuality = null,
		availableQualities = [],
		onQualityChange,
		showQualitySelector = false,
		qualityLoading = false
	}: Props = $props();

	const video = $derived(videoPlayer.currentVideo);
	const platformName = $derived(video ? getPlatformName(video.platform) : '');
	const platformColor = $derived(video ? getPlatformColor(video.platform) : '#666');
	const isPremium = $derived(streamInfo?.is_premium ?? false);
	const hasNext = $derived(videoPlayer.hasNext);
	const hasPrevious = $derived(videoPlayer.hasPrevious);
	const queuePosition = $derived(
		videoPlayer.queueLength > 0
			? `${videoPlayer.currentIndex + 1}/${videoPlayer.queueLength}`
			: null
	);

	function handlePrevious() {
		videoPlayer.playPrevious();
	}

	function handleNext() {
		videoPlayer.playNext();
	}
</script>

<div class="player-header" class:compact>
	<div class="header-left">
		<span class="platform-badge" style="background-color: {platformColor}">
			{platformName}
		</span>
		{#if isPremium}
			<span class="premium-badge" title="Authenticated playback">
				<svg viewBox="0 0 24 24" fill="currentColor" width="14" height="14">
					<path
						d="M12 1L3 5v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V5l-9-4zm-2 16l-4-4 1.41-1.41L10 14.17l6.59-6.59L18 9l-8 8z"
					/>
				</svg>
				{#if !compact}Premium{/if}
			</span>
		{/if}
		{#if queuePosition && !compact}
			<div class="queue-controls">
				<button
					class="header-btn nav-btn"
					onclick={handlePrevious}
					disabled={!hasPrevious}
					title="Previous"
				>
					<svg viewBox="0 0 24 24" fill="currentColor" width="18" height="18">
						<path d="M15.41 7.41L14 6l-6 6 6 6 1.41-1.41L10.83 12z" />
					</svg>
				</button>
				<span class="queue-position">{queuePosition}</span>
				<button class="header-btn nav-btn" onclick={handleNext} disabled={!hasNext} title="Next">
					<svg viewBox="0 0 24 24" fill="currentColor" width="18" height="18">
						<path d="M8.59 16.59L10 18l6-6-6-6-1.41 1.41L13.17 12z" />
					</svg>
				</button>
			</div>
		{/if}
		{#if video?.duration && !compact}
			<span class="duration">{formatDuration(video.duration)}</span>
		{/if}
	</div>
	<div class="header-right">
		{#if showQualitySelector && availableQualities.length > 0 && onQualityChange && !compact}
			<QualitySelector
				{currentQuality}
				{availableQualities}
				{onQualityChange}
				isLoading={qualityLoading}
				{compact}
			/>
		{/if}
		{#if streamInfo?.stream_url && onToggleDirectStream && !compact}
			<button
				class="header-btn stream-toggle"
				class:active={useDirectStream}
				onclick={onToggleDirectStream}
				title={useDirectStream ? 'Switch to embed player' : 'Switch to direct stream (no ads)'}
			>
				<svg viewBox="0 0 24 24" fill="currentColor" width="18" height="18">
					<path
						d="M21 3H3c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h18c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm0 16H3V5h18v14zM9 8l7 4-7 4V8z"
					/>
				</svg>
				<span class="stream-label">{useDirectStream ? 'Direct' : 'Embed'}</span>
			</button>
		{/if}
		{#if showTheaterToggle && onToggleTheaterMode}
			<button
				class="header-btn theater-btn"
				class:active={theaterMode}
				onclick={onToggleTheaterMode}
				title={theaterMode ? 'Exit Theater Mode (T)' : 'Theater Mode (T)'}
			>
				<svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
					{#if theaterMode}
						<path
							d="M5 16h3v3h2v-5H5v2zm3-8H5v2h5V5H8v3zm6 11h2v-3h3v-2h-5v5zm2-11V5h-2v5h5V8h-3z"
						/>
					{:else}
						<path d="M7 14H5v5h5v-2H7v-3zm-2-4h2V7h3V5H5v5zm12 7h-3v2h5v-5h-2v3zM14 5v2h3v3h2V5h-5z" />
					{/if}
				</svg>
			</button>
		{/if}
		{#if showPiPToggle && onSwitchToPiP}
			<button class="header-btn pip-btn" onclick={onSwitchToPiP} title="Mini Player (P)">
				<svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
					<path
						d="M19 7h-8v6h8V7zm2-4H3c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h18c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm0 16H3V5h18v14z"
					/>
				</svg>
			</button>
		{/if}
		{#if showModalToggle && onSwitchToModal}
			<button class="header-btn expand-btn" onclick={onSwitchToModal} title="Expand (M)">
				<svg viewBox="0 0 24 24" fill="currentColor" width="20" height="20">
					<path d="M7 14H5v5h5v-2H7v-3zm-2-4h2V7h3V5H5v5zm12 7h-3v2h5v-5h-2v3zM14 5v2h3v3h2V5h-5z" />
				</svg>
			</button>
		{/if}
		{#if onClose}
			<button class="header-btn close-btn" onclick={onClose} title="Close (Escape)">
				<svg viewBox="0 0 24 24" fill="currentColor" width="24" height="24">
					<path
						d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"
					/>
				</svg>
			</button>
		{/if}
	</div>
</div>

<style>
	.player-header {
		display: flex;
		justify-content: space-between;
		align-items: center;
		padding: var(--spacing-sm) var(--spacing-md);
		background: var(--color-bg);
		border-bottom: 1px solid var(--color-border);
	}

	.player-header.compact {
		padding: var(--spacing-xs) var(--spacing-sm);
	}

	.header-left {
		display: flex;
		align-items: center;
		gap: var(--spacing-md);
	}

	.compact .header-left {
		gap: var(--spacing-sm);
	}

	.platform-badge {
		padding: 2px 8px;
		border-radius: var(--radius-sm);
		color: white;
		font-size: 0.75rem;
		font-weight: 600;
		text-transform: uppercase;
	}

	.compact .platform-badge {
		padding: 1px 4px;
		font-size: 0.65rem;
	}

	.duration {
		color: var(--color-text-secondary);
		font-size: 0.875rem;
	}

	.queue-controls {
		display: flex;
		align-items: center;
		gap: 4px;
		padding: 2px 6px;
		background: var(--color-bg-secondary);
		border-radius: var(--radius-md);
	}

	.queue-position {
		font-size: 0.75rem;
		color: var(--color-text-secondary);
		min-width: 2.5em;
		text-align: center;
	}

	.nav-btn {
		padding: 2px !important;
	}

	.nav-btn:disabled {
		opacity: 0.3;
		cursor: not-allowed;
	}

	.header-right {
		display: flex;
		align-items: center;
		gap: var(--spacing-sm);
	}

	.compact .header-right {
		gap: var(--spacing-xs);
	}

	.header-btn {
		background: transparent;
		border: none;
		color: var(--color-text-secondary);
		padding: var(--spacing-xs);
		border-radius: var(--radius-sm);
		cursor: pointer;
		display: flex;
		align-items: center;
		justify-content: center;
		transition:
			color 0.2s,
			background 0.2s;
	}

	.header-btn:hover {
		color: var(--color-text);
		background: var(--color-bg-secondary);
	}

	.premium-badge {
		display: flex;
		align-items: center;
		gap: 4px;
		padding: 2px 8px;
		border-radius: var(--radius-sm);
		background: linear-gradient(135deg, #ffd700, #ffb700);
		color: #000;
		font-size: 0.7rem;
		font-weight: 600;
		text-transform: uppercase;
	}

	.compact .premium-badge {
		padding: 1px 4px;
	}

	.stream-toggle {
		display: flex;
		align-items: center;
		gap: 4px;
		padding: var(--spacing-xs) var(--spacing-sm);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-md);
	}

	.stream-toggle.active {
		background: var(--color-primary);
		color: white;
		border-color: var(--color-primary);
	}

	.theater-btn.active {
		color: var(--color-primary);
	}

	.stream-label {
		font-size: 0.75rem;
		font-weight: 500;
	}
</style>
