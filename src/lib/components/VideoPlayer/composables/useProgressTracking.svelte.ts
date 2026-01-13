/**
 * Progress Tracking Composable
 *
 * Handles saving watch progress to both localStorage (fast) and API (durable).
 * Supports marking videos as watched at 90% completion.
 *
 * Usage:
 *   const progress = useProgressTracking(() => currentVideo);
 *   progress.start(getCurrentTime, getDuration);
 *   // ... on pause/close
 *   progress.stop();
 */

import { watchProgress } from '$lib/stores/watchProgress.svelte';
import { api } from '$lib/api/client';
import type { VideoItem } from '$lib/stores/videoPlayer.svelte';

export interface ProgressTrackingOptions {
	onMarkedWatched?: () => void;
	apiSaveInterval?: number;
	localSaveInterval?: number;
	watchedThreshold?: number;
}

export interface ProgressTracker {
	start(getCurrentTime: () => number, getDuration: () => number): void;
	stop(): void;
	saveLocal(currentTime: number): void;
	saveToApi(currentTime: number): Promise<void>;
	markAsWatched(finalProgress: number): Promise<void>;
	getInitialPlayhead(savedPlayhead?: number): number;
}

const DEFAULT_API_SAVE_INTERVAL = 15000; // 15 seconds
const DEFAULT_LOCAL_SAVE_INTERVAL = 3000; // 3 seconds
const DEFAULT_WATCHED_THRESHOLD = 0.9; // 90%

export function useProgressTracking(
	getVideo: () => VideoItem | null,
	options: ProgressTrackingOptions = {}
): ProgressTracker {
	const {
		onMarkedWatched,
		apiSaveInterval = DEFAULT_API_SAVE_INTERVAL,
		localSaveInterval = DEFAULT_LOCAL_SAVE_INTERVAL,
		watchedThreshold = DEFAULT_WATCHED_THRESHOLD
	} = options;

	let apiInterval: ReturnType<typeof setInterval> | null = null;
	let localInterval: ReturnType<typeof setInterval> | null = null;
	let lastApiSaveProgress = 0;
	let lastLocalSaveProgress = 0;
	let isWatched = false;

	/**
	 * Save progress to localStorage (fast, immediate backup)
	 */
	function saveLocal(currentTime: number): void {
		const video = getVideo();
		if (!video?.sourceId || video.sourceType === 'discover') return;
		if (Math.abs(currentTime - lastLocalSaveProgress) < 2) return; // Skip tiny changes

		// Collection items use local storage only (no API)
		const sourceType = video.sourceType === 'collection' ? 'collection' : (video.sourceType as 'feed' | 'saved');
		watchProgress.save(sourceType, video.sourceId, Math.floor(currentTime));
		lastLocalSaveProgress = currentTime;
	}

	/**
	 * Save progress to API (slower, server sync)
	 */
	async function saveToApi(currentTime: number): Promise<void> {
		const video = getVideo();
		if (!video?.sourceId || video.sourceType === 'discover') return;
		if (Math.abs(currentTime - lastApiSaveProgress) < 5) return; // Skip small changes

		// Always save locally first
		saveLocal(currentTime);

		try {
			if (video.sourceType === 'feed') {
				await api.updateFeedItemProgress(video.sourceId, Math.floor(currentTime));
			} else if (video.sourceType === 'saved') {
				await api.updateSavedVideoProgress(video.sourceId, Math.floor(currentTime));
			} else if (video.sourceType === 'collection' && video.collectionId) {
				await api.updateCollectionItemProgress(video.collectionId, video.sourceId, Math.floor(currentTime));
			}
			lastApiSaveProgress = currentTime;
			// Mark as synced in local store
			if (video.sourceType !== 'collection') {
				watchProgress.markSynced(video.sourceType as 'feed' | 'saved', video.sourceId);
			}
		} catch (e) {
			console.warn('[ProgressTracking] API save failed:', e);
			// Local save already happened, progress is preserved
		}
	}

	/**
	 * Mark video as watched (called at threshold or end)
	 */
	async function markAsWatched(finalProgress: number): Promise<void> {
		if (isWatched) return;

		const video = getVideo();
		if (!video?.sourceId || video.sourceType === 'discover') return;

		try {
			if (video.sourceType === 'feed') {
				await api.markFeedItemWatched(video.sourceId, Math.floor(finalProgress));
			} else if (video.sourceType === 'saved') {
				await api.markSavedVideoWatched(video.sourceId, Math.floor(finalProgress));
			} else if (video.sourceType === 'collection' && video.collectionId) {
				await api.markCollectionItemWatched(video.collectionId, video.sourceId, true);
			}
			// Clear local progress since video is now marked watched
			const sourceType = video.sourceType === 'collection' ? 'collection' : (video.sourceType as 'feed' | 'saved');
			watchProgress.clear(sourceType, video.sourceId);
			isWatched = true;
			onMarkedWatched?.();
		} catch (e) {
			console.warn('[ProgressTracking] Mark watched failed:', e);
		}
	}

	/**
	 * Check if video should be marked as watched
	 */
	function checkWatchedThreshold(currentTime: number, duration: number): void {
		if (isWatched) return;
		if (duration > 0 && currentTime / duration >= watchedThreshold) {
			markAsWatched(currentTime);
		}
	}

	/**
	 * Start periodic progress tracking
	 */
	function start(getCurrentTime: () => number, getDuration: () => number): void {
		stop(); // Clear any existing intervals
		isWatched = false;
		lastApiSaveProgress = 0;
		lastLocalSaveProgress = 0;

		// Fast local save
		localInterval = setInterval(() => {
			saveLocal(getCurrentTime());
		}, localSaveInterval);

		// API save + watched check
		apiInterval = setInterval(() => {
			const time = getCurrentTime();
			const dur = getDuration();
			saveToApi(time);
			checkWatchedThreshold(time, dur);
		}, apiSaveInterval);
	}

	/**
	 * Stop tracking and save final progress
	 */
	function stop(): void {
		if (localInterval) {
			clearInterval(localInterval);
			localInterval = null;
		}
		if (apiInterval) {
			clearInterval(apiInterval);
			apiInterval = null;
		}
	}

	/**
	 * Get initial playhead position (from mode switch or saved progress)
	 */
	function getInitialPlayhead(savedPlayhead?: number): number {
		// First priority: saved playhead from mode switch
		if (savedPlayhead && savedPlayhead > 0) {
			return savedPlayhead;
		}

		const video = getVideo();

		// Get effective progress (max of local and API)
		if (video?.sourceId && video.sourceType && video.sourceType !== 'discover') {
			const sourceType = video.sourceType === 'collection' ? 'collection' : (video.sourceType as 'feed' | 'saved');
			const effectiveProgress = watchProgress.getEffective(
				sourceType,
				video.sourceId,
				video.watchProgress
			);
			if (effectiveProgress && effectiveProgress > 0) {
				return effectiveProgress;
			}
		}

		// Fallback to API progress only
		if (video?.watchProgress && video.watchProgress > 0) {
			return video.watchProgress;
		}

		return 0;
	}

	return {
		start,
		stop,
		saveLocal,
		saveToApi,
		markAsWatched,
		getInitialPlayhead
	};
}
