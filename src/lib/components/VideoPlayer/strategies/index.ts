/**
 * VideoPlayer Strategies
 *
 * Interchangeable playback backends for different platforms and scenarios.
 */

export { default as EmbedStrategy } from './EmbedStrategy.svelte';
export { default as DirectStreamStrategy } from './DirectStreamStrategy.svelte';
export { default as YouTubeApiStrategy } from './YouTubeApiStrategy.svelte';
export { default as AudioStrategy } from './AudioStrategy.svelte';

export * from './types';
