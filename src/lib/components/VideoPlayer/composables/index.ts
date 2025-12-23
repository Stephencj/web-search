/**
 * VideoPlayer Composables
 *
 * Shared logic extracted from VideoPlayerModal and PiPPlayer.
 */

export { useProgressTracking, type ProgressTracker, type ProgressTrackingOptions } from './useProgressTracking.svelte';
export { usePlaybackControl, dispatchPlayerEvent, type PlaybackControlResult, type PlayerElements } from './usePlaybackControl.svelte';
