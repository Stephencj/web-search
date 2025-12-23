/**
 * Priority Prefetch Queue
 *
 * Manages background stream extraction with priority-based ordering.
 * Integrates with network conditions to pause/resume intelligently.
 *
 * Priority sources (highest to lowest):
 * - queue_next (100): Next video in playback queue
 * - hover (90): User hovering over thumbnail
 * - queue_upcoming (80): Videos 2-5 in queue
 * - visible_feed (60): Currently visible in viewport
 * - feed_load (50): First batch on feed load
 * - scroll_ahead (40): Below current viewport
 * - cache_warm (20): Background warming
 */

import { streamCache, fetchStreamInfo, type CachePriority } from './streamCacheV2.svelte';

export type PrefetchSource =
	| 'queue_next'
	| 'hover'
	| 'queue_upcoming'
	| 'visible_feed'
	| 'feed_load'
	| 'scroll_ahead'
	| 'cache_warm';

const SOURCE_PRIORITIES: Record<PrefetchSource, number> = {
	queue_next: 100,
	hover: 90,
	queue_upcoming: 80,
	visible_feed: 60,
	feed_load: 50,
	scroll_ahead: 40,
	cache_warm: 20
};

const SOURCE_TO_CACHE_PRIORITY: Record<PrefetchSource, CachePriority> = {
	queue_next: 'critical',
	hover: 'high',
	queue_upcoming: 'high',
	visible_feed: 'normal',
	feed_load: 'normal',
	scroll_ahead: 'low',
	cache_warm: 'low'
};

export interface PrefetchRequest {
	platform: string;
	videoId: string;
	source: PrefetchSource;
	requestedAt: number;
	retryCount: number;
}

interface QueuedRequest extends PrefetchRequest {
	priority: number;
}

// Configuration
const MAX_CONCURRENT = 2;
const MAX_RETRIES = 2;
const RETRY_DELAY_MS = 5000;
const QUEUE_PROCESS_INTERVAL_MS = 100;

class PrefetchQueueManager {
	private queue: QueuedRequest[] = [];
	private activeRequests = new Map<string, Promise<void>>();
	private isPaused = $state(false);
	private processInterval: ReturnType<typeof setInterval> | null = null;

	// Stats
	private stats = $state({
		queued: 0,
		active: 0,
		completed: 0,
		failed: 0
	});

	constructor() {
		// Start processing loop
		if (typeof window !== 'undefined') {
			this.startProcessing();
		}
	}

	private makeKey(platform: string, videoId: string): string {
		return `${platform}:${videoId}`;
	}

	private calculatePriority(request: PrefetchRequest): number {
		const basePriority = SOURCE_PRIORITIES[request.source];
		// Age penalty: reduce priority by 1 point per minute waiting
		const ageMinutes = (Date.now() - request.requestedAt) / 60000;
		const agePenalty = Math.min(ageMinutes, 20);
		// Retry penalty
		const retryPenalty = request.retryCount * 10;
		return Math.max(0, basePriority - agePenalty - retryPenalty);
	}

	/**
	 * Add a video to the prefetch queue
	 */
	enqueue(request: Omit<PrefetchRequest, 'requestedAt' | 'retryCount'>): void {
		const { platform, videoId, source } = request;
		const key = this.makeKey(platform, videoId);

		// Skip if not YouTube (only platform with stream extraction)
		if (platform !== 'youtube') return;

		// Skip if already cached
		if (streamCache.has(platform, videoId)) return;

		// Skip if already extracting
		const extractionState = streamCache.getExtractionStatus(platform, videoId);
		if (extractionState?.status === 'extracting') return;

		// Skip if already in queue - but upgrade priority if new source is higher
		const existing = this.queue.find((r) => this.makeKey(r.platform, r.videoId) === key);
		if (existing) {
			const newPriority = SOURCE_PRIORITIES[source];
			if (newPriority > existing.priority) {
				existing.source = source;
				existing.priority = newPriority;
				this.sortQueue();
			}
			return;
		}

		// Skip if currently being fetched
		if (this.activeRequests.has(key)) return;

		const fullRequest: QueuedRequest = {
			platform,
			videoId,
			source,
			requestedAt: Date.now(),
			retryCount: 0,
			priority: SOURCE_PRIORITIES[source]
		};

		this.queue.push(fullRequest);
		this.sortQueue();
		this.stats.queued = this.queue.length;
	}

	/**
	 * Add multiple videos to the prefetch queue
	 */
	enqueueMany(requests: Array<Omit<PrefetchRequest, 'requestedAt' | 'retryCount'>>): void {
		for (const request of requests) {
			this.enqueue(request);
		}
	}

	/**
	 * Remove a video from the queue
	 */
	dequeue(platform: string, videoId: string): void {
		const key = this.makeKey(platform, videoId);
		this.queue = this.queue.filter((r) => this.makeKey(r.platform, r.videoId) !== key);
		this.stats.queued = this.queue.length;
	}

	/**
	 * Cancel an active prefetch
	 */
	cancel(platform: string, videoId: string): void {
		const key = this.makeKey(platform, videoId);
		this.dequeue(platform, videoId);
		// Note: Can't actually cancel fetch, but it won't be re-queued
	}

	/**
	 * Clear the entire queue
	 */
	clear(): void {
		this.queue = [];
		this.stats.queued = 0;
	}

	/**
	 * Pause queue processing
	 */
	pause(): void {
		this.isPaused = true;
	}

	/**
	 * Resume queue processing
	 */
	resume(): void {
		this.isPaused = false;
	}

	/**
	 * Get current stats
	 */
	getStats(): typeof this.stats {
		return this.stats;
	}

	/**
	 * Check if queue is paused
	 */
	get paused(): boolean {
		return this.isPaused;
	}

	private sortQueue(): void {
		// Recalculate priorities and sort
		for (const request of this.queue) {
			request.priority = this.calculatePriority(request);
		}
		this.queue.sort((a, b) => b.priority - a.priority);
	}

	private startProcessing(): void {
		if (this.processInterval) return;

		this.processInterval = setInterval(() => {
			this.processQueue();
		}, QUEUE_PROCESS_INTERVAL_MS);
	}

	private async processQueue(): Promise<void> {
		if (this.isPaused) return;
		if (this.activeRequests.size >= MAX_CONCURRENT) return;
		if (this.queue.length === 0) return;

		// Check network conditions
		if (!this.shouldPrefetch()) {
			return;
		}

		// Get next request
		const request = this.queue.shift();
		if (!request) return;

		this.stats.queued = this.queue.length;

		const key = this.makeKey(request.platform, request.videoId);

		// Double-check it's not already cached
		if (streamCache.has(request.platform, request.videoId)) {
			return;
		}

		// Start fetch
		const cachePriority = SOURCE_TO_CACHE_PRIORITY[request.source];
		const fetchPromise = this.executeFetch(request, cachePriority);
		this.activeRequests.set(key, fetchPromise);
		this.stats.active = this.activeRequests.size;

		fetchPromise.finally(() => {
			this.activeRequests.delete(key);
			this.stats.active = this.activeRequests.size;
		});
	}

	private async executeFetch(request: QueuedRequest, cachePriority: CachePriority): Promise<void> {
		try {
			const result = await fetchStreamInfo(request.platform, request.videoId, cachePriority);

			if (result) {
				this.stats.completed++;
			} else {
				// Retry logic
				if (request.retryCount < MAX_RETRIES) {
					setTimeout(() => {
						this.queue.push({
							...request,
							retryCount: request.retryCount + 1,
							priority: this.calculatePriority({
								...request,
								retryCount: request.retryCount + 1
							})
						});
						this.sortQueue();
						this.stats.queued = this.queue.length;
					}, RETRY_DELAY_MS);
				} else {
					this.stats.failed++;
				}
			}
		} catch {
			this.stats.failed++;
		}
	}

	private shouldPrefetch(): boolean {
		// Check if we're online
		if (typeof navigator !== 'undefined' && !navigator.onLine) {
			return false;
		}

		// Check for save-data mode
		if (typeof navigator !== 'undefined' && 'connection' in navigator) {
			const conn = (navigator as Navigator & { connection?: NetworkInformation }).connection;
			if (conn?.saveData) {
				return false;
			}
			// Skip on slow connections
			if (conn?.effectiveType === 'slow-2g' || conn?.effectiveType === '2g') {
				return false;
			}
		}

		return true;
	}

	/**
	 * Destroy the queue manager
	 */
	destroy(): void {
		if (this.processInterval) {
			clearInterval(this.processInterval);
			this.processInterval = null;
		}
	}
}

// Network Information API types
interface NetworkInformation {
	saveData?: boolean;
	effectiveType?: 'slow-2g' | '2g' | '3g' | '4g';
	downlink?: number;
	rtt?: number;
}

// Singleton instance
export const prefetchQueue = new PrefetchQueueManager();

// Convenience functions for common prefetch triggers

/**
 * Prefetch videos when feed loads
 */
export function prefetchOnFeedLoad(
	videos: Array<{ platform: string; videoId: string }>,
	limit = 10
): void {
	const youtubeVideos = videos.filter((v) => v.platform === 'youtube').slice(0, limit);

	prefetchQueue.enqueueMany(
		youtubeVideos.map((v) => ({
			platform: v.platform,
			videoId: v.videoId,
			source: 'feed_load' as const
		}))
	);
}

/**
 * Prefetch video on hover (with debounce handled by caller)
 */
export function prefetchOnHover(platform: string, videoId: string): void {
	prefetchQueue.enqueue({
		platform,
		videoId,
		source: 'hover'
	});
}

/**
 * Prefetch upcoming videos in queue
 */
export function prefetchQueueVideos(
	queue: Array<{ platform: string; videoId: string }>,
	currentIndex: number,
	count = 3
): void {
	const upcoming = queue.slice(currentIndex + 1, currentIndex + 1 + count);

	for (let i = 0; i < upcoming.length; i++) {
		const video = upcoming[i];
		prefetchQueue.enqueue({
			platform: video.platform,
			videoId: video.videoId,
			source: i === 0 ? 'queue_next' : 'queue_upcoming'
		});

		// Protect queue items from cache eviction
		if (video.platform === 'youtube') {
			streamCache.protect(video.platform, video.videoId);
		}
	}
}

/**
 * Prefetch videos entering viewport (for IntersectionObserver)
 */
export function prefetchOnVisible(platform: string, videoId: string): void {
	prefetchQueue.enqueue({
		platform,
		videoId,
		source: 'visible_feed'
	});
}

/**
 * Prefetch videos below viewport (scroll-ahead)
 */
export function prefetchOnScrollAhead(videos: Array<{ platform: string; videoId: string }>): void {
	prefetchQueue.enqueueMany(
		videos
			.filter((v) => v.platform === 'youtube')
			.map((v) => ({
				platform: v.platform,
				videoId: v.videoId,
				source: 'scroll_ahead' as const
			}))
	);
}

/**
 * Create an IntersectionObserver for viewport-based prefetching
 */
export function createPrefetchObserver(
	getVideoFromElement: (el: Element) => { platform: string; videoId: string } | null
): IntersectionObserver | null {
	if (typeof IntersectionObserver === 'undefined') {
		return null;
	}

	return new IntersectionObserver(
		(entries) => {
			for (const entry of entries) {
				if (entry.isIntersecting) {
					const video = getVideoFromElement(entry.target);
					if (video && video.platform === 'youtube') {
						prefetchOnVisible(video.platform, video.videoId);
					}
				}
			}
		},
		{
			rootMargin: '200px' // Start prefetching 200px before visible
		}
	);
}
