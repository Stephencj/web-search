<script lang="ts">
	/**
	 * Embed Strategy
	 *
	 * Uses platform's native embed iframe for instant playback.
	 * Works for all platforms that support embedding.
	 * Fastest startup but limited control and may have ads.
	 */
	import type { StrategyProps } from './types';
	import EmbedFallback from '../EmbedFallback.svelte';

	interface Props extends StrategyProps {}

	let { video, callbacks }: Props = $props();

	let iframeLoaded = $state(false);
	let iframeError = $state(false);

	const embedUrl = $derived(video.embedConfig.embedUrl);
	const canEmbed = $derived(video.embedConfig.supportsEmbed && !iframeError);

	function handleLoad() {
		iframeLoaded = true;
		callbacks?.onReady?.();
	}

	function handleError() {
		iframeError = true;
		callbacks?.onError?.('Embed failed to load');
	}

	// Reset state when video changes
	$effect(() => {
		if (video) {
			iframeLoaded = false;
			iframeError = false;
		}
	});
</script>

{#if canEmbed && embedUrl}
	<div class="iframe-container">
		{#if !iframeLoaded}
			<div class="loading-spinner">
				<div class="spinner"></div>
			</div>
		{/if}
		<iframe
			src={embedUrl}
			title={video.title}
			allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share; fullscreen"
			allowfullscreen
			referrerpolicy="no-referrer-when-downgrade"
			onload={handleLoad}
			onerror={handleError}
			class:loaded={iframeLoaded}
		></iframe>
	</div>
{:else}
	<EmbedFallback {video} reason={video.embedConfig.fallbackReason} />
{/if}

<style>
	.iframe-container {
		position: relative;
		width: 100%;
		height: 100%;
	}

	.iframe-container iframe {
		position: absolute;
		inset: 0;
		width: 100%;
		height: 100%;
		border: none;
		opacity: 0;
		transition: opacity 0.3s ease;
	}

	.iframe-container iframe.loaded {
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
