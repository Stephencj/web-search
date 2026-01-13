<script lang="ts">
	/**
	 * Quality Selector
	 *
	 * Dropdown to select video quality.
	 * Works with HLS (hls.js level switching) and DirectStream (re-fetch with quality param).
	 */
	import { qualityPreferences, type QualityLevel } from '$lib/stores/qualityPreferences.svelte';

	export interface QualityOption {
		value: string;
		label: string;
		height?: number;
		bitrate?: number;
	}

	interface Props {
		currentQuality: string | null;
		availableQualities: QualityOption[];
		onQualityChange: (quality: string) => void;
		isLoading?: boolean;
		compact?: boolean;
	}

	let {
		currentQuality,
		availableQualities,
		onQualityChange,
		isLoading = false,
		compact = false
	}: Props = $props();

	let showDropdown = $state(false);

	// Close dropdown when clicking outside
	function handleClickOutside(event: MouseEvent) {
		const target = event.target as HTMLElement;
		if (!target.closest('.quality-selector')) {
			showDropdown = false;
		}
	}

	function toggleDropdown() {
		showDropdown = !showDropdown;
	}

	function selectQuality(quality: string) {
		onQualityChange(quality);
		showDropdown = false;
	}

	// Format quality label for display
	function formatQualityLabel(quality: string | null): string {
		if (!quality || quality === 'auto') return 'Auto';
		if (quality === 'best') return 'Best';
		if (quality === 'worst') return 'Low';
		return quality;
	}

	// Get sorted options (auto first, then by height descending)
	const sortedOptions = $derived.by(() => {
		const sorted = [...availableQualities].sort((a, b) => {
			// Auto always first
			if (a.value === 'auto') return -1;
			if (b.value === 'auto') return 1;
			// Then by height descending
			return (b.height || 0) - (a.height || 0);
		});
		return sorted;
	});

	$effect(() => {
		if (showDropdown) {
			document.addEventListener('click', handleClickOutside);
		}
		return () => {
			document.removeEventListener('click', handleClickOutside);
		};
	});
</script>

<div class="quality-selector" class:compact>
	<button
		class="quality-trigger"
		class:loading={isLoading}
		onclick={toggleDropdown}
		disabled={isLoading || availableQualities.length === 0}
		title="Select video quality"
	>
		<svg viewBox="0 0 24 24" fill="currentColor" width="16" height="16">
			<path d="M19.35 10.04A7.49 7.49 0 0 0 12 4C9.11 4 6.6 5.64 5.35 8.04A5.994 5.994 0 0 0 0 14c0 3.31 2.69 6 6 6h13c2.76 0 5-2.24 5-5 0-2.64-2.05-4.78-4.65-4.96zM14 13v4h-4v-4H7l5-5 5 5h-3z"/>
		</svg>
		<span class="quality-label">{formatQualityLabel(currentQuality)}</span>
		{#if !compact}
			<svg class="chevron" class:open={showDropdown} viewBox="0 0 24 24" fill="currentColor" width="14" height="14">
				<path d="M7.41 8.59L12 13.17l4.59-4.58L18 10l-6 6-6-6 1.41-1.41z"/>
			</svg>
		{/if}
	</button>

	{#if showDropdown}
		<div class="quality-dropdown">
			{#each sortedOptions as option}
				<button
					class="quality-option"
					class:selected={option.value === currentQuality}
					onclick={() => selectQuality(option.value)}
				>
					<span class="option-label">{option.label}</span>
					{#if option.value === currentQuality}
						<svg viewBox="0 0 24 24" fill="currentColor" width="16" height="16">
							<path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/>
						</svg>
					{/if}
				</button>
			{/each}
		</div>
	{/if}
</div>

<style>
	.quality-selector {
		position: relative;
	}

	.quality-trigger {
		display: flex;
		align-items: center;
		gap: 4px;
		padding: var(--spacing-xs) var(--spacing-sm);
		background: transparent;
		border: 1px solid var(--color-border);
		border-radius: var(--radius-md);
		color: var(--color-text-secondary);
		cursor: pointer;
		font-size: 0.75rem;
		font-weight: 500;
		transition: all 0.2s;
	}

	.quality-trigger:hover:not(:disabled) {
		color: var(--color-text);
		background: var(--color-bg-secondary);
		border-color: var(--color-text-secondary);
	}

	.quality-trigger:disabled {
		opacity: 0.5;
		cursor: not-allowed;
	}

	.quality-trigger.loading {
		opacity: 0.7;
	}

	.quality-label {
		min-width: 2.5em;
	}

	.compact .quality-trigger {
		padding: 2px 6px;
		font-size: 0.65rem;
	}

	.compact .quality-label {
		min-width: 2em;
	}

	.chevron {
		transition: transform 0.2s;
	}

	.chevron.open {
		transform: rotate(180deg);
	}

	.quality-dropdown {
		position: absolute;
		top: 100%;
		right: 0;
		margin-top: 4px;
		min-width: 120px;
		background: var(--color-surface);
		border: 1px solid var(--color-border);
		border-radius: var(--radius-md);
		box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
		z-index: 1000;
		overflow: hidden;
	}

	.quality-option {
		width: 100%;
		display: flex;
		align-items: center;
		justify-content: space-between;
		padding: var(--spacing-sm) var(--spacing-md);
		background: transparent;
		border: none;
		color: var(--color-text);
		cursor: pointer;
		font-size: 0.875rem;
		text-align: left;
		transition: background 0.15s;
	}

	.quality-option:hover {
		background: var(--color-bg-secondary);
	}

	.quality-option.selected {
		background: var(--color-bg-secondary);
		color: var(--color-primary);
	}

	.option-label {
		flex: 1;
	}
</style>
