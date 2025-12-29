/**
 * Multi-Tier Stream Cache V2
 *
 * L1: Memory cache (100 entries, 4-hour TTL) - instant access
 * L2: IndexedDB cache (500 entries, 5-hour TTL) - persists across reloads
 * L3: Network fetch - fallback with background caching
 *
 * Features:
 * - LRU eviction with priority protection for queue items
 * - Proactive prefetching support
 * - Extraction status tracking for in-flight requests
 */

import type { StreamInfo } from './videoPlayer.svelte';

// Cache configuration
const MEMORY_MAX_ENTRIES = 100;
const MEMORY_TTL_MS = 4 * 60 * 60 * 1000; // 4 hours

const IDB_MAX_ENTRIES = 500;
const IDB_TTL_MS = 5 * 60 * 60 * 1000; // 5 hours

const DB_NAME = 'websearch-stream-cache';
const DB_VERSION = 1;
const STREAM_STORE = 'streams';

export type CachePriority = 'critical' | 'high' | 'normal' | 'low';

export type ExtractionStatus = 'idle' | 'extracting' | 'ready' | 'failed';

export interface CacheEntry {
	info: StreamInfo;
	cachedAt: number;
	expiresAt: number;
	accessCount: number;
	lastAccessedAt: number;
	priority: CachePriority;
}

interface IDBCacheEntry extends CacheEntry {
	key: string; // platform:videoId
}

interface ExtractionState {
	status: ExtractionStatus;
	startedAt: number;
	promise?: Promise<StreamInfo | null>;
	error?: string;
}

// IndexedDB singleton
let db: IDBDatabase | null = null;
let dbReady: Promise<IDBDatabase> | null = null;

async function openDB(): Promise<IDBDatabase> {
	if (db) return db;
	if (dbReady) return dbReady;

	dbReady = new Promise((resolve, reject) => {
		if (typeof indexedDB === 'undefined') {
			reject(new Error('IndexedDB not available'));
			return;
		}

		const request = indexedDB.open(DB_NAME, DB_VERSION);

		request.onerror = () => reject(request.error);
		request.onsuccess = () => {
			db = request.result;
			resolve(db);
		};

		request.onupgradeneeded = (event) => {
			const database = (event.target as IDBOpenDBRequest).result;

			if (!database.objectStoreNames.contains(STREAM_STORE)) {
				const store = database.createObjectStore(STREAM_STORE, { keyPath: 'key' });
				store.createIndex('expiresAt', 'expiresAt', { unique: false });
				store.createIndex('accessCount', 'accessCount', { unique: false });
				store.createIndex('priority', 'priority', { unique: false });
			}
		};
	});

	return dbReady;
}

class MultiTierStreamCache {
	// L1: Memory cache
	private memoryCache = new Map<string, CacheEntry>();

	// Extraction tracking
	private extractionStates = new Map<string, ExtractionState>();

	// Protected keys (queue items that shouldn't be evicted)
	private protectedKeys = new Set<string>();

	constructor() {
		// Load hot entries from IndexedDB on init
		this.warmMemoryCache();
	}

	private makeKey(platform: string, videoId: string): string {
		return `${platform}:${videoId}`;
	}

	private isExpired(entry: CacheEntry): boolean {
		return Date.now() > entry.expiresAt;
	}

	/**
	 * Pre-warm memory cache from IndexedDB
	 */
	private async warmMemoryCache(): Promise<void> {
		try {
			const database = await openDB();
			const transaction = database.transaction([STREAM_STORE], 'readonly');
			const store = transaction.objectStore(STREAM_STORE);
			const request = store.getAll();

			request.onsuccess = () => {
				const entries = request.result as IDBCacheEntry[];
				const now = Date.now();

				// Sort by access count (most accessed first), take top entries
				const valid = entries
					.filter((e) => e.expiresAt > now)
					.sort((a, b) => b.accessCount - a.accessCount)
					.slice(0, MEMORY_MAX_ENTRIES);

				for (const entry of valid) {
					this.memoryCache.set(entry.key, {
						info: entry.info,
						cachedAt: entry.cachedAt,
						expiresAt: entry.expiresAt,
						accessCount: entry.accessCount,
						lastAccessedAt: entry.lastAccessedAt,
						priority: entry.priority
					});
				}

				console.log(`[StreamCacheV2] Warmed memory cache with ${valid.length} entries`);
			};
		} catch (e) {
			console.warn('[StreamCacheV2] Failed to warm memory cache:', e);
		}
	}

	/**
	 * Get from cache (L1 -> L2)
	 */
	async get(platform: string, videoId: string): Promise<StreamInfo | null> {
		const key = this.makeKey(platform, videoId);

		// L1: Check memory cache
		const memEntry = this.memoryCache.get(key);
		if (memEntry && !this.isExpired(memEntry)) {
			// Update access stats
			memEntry.accessCount++;
			memEntry.lastAccessedAt = Date.now();
			return memEntry.info;
		}

		// L2: Check IndexedDB
		try {
			const entry = await this.getFromIDB(key);
			if (entry && !this.isExpired(entry)) {
				// Promote to memory cache
				entry.accessCount++;
				entry.lastAccessedAt = Date.now();
				this.memoryCache.set(key, entry);
				this.evictMemoryIfNeeded();

				// Update access stats in IDB (async, don't await)
				this.updateAccessStats(key, entry.accessCount, entry.lastAccessedAt);

				return entry.info;
			}
		} catch (e) {
			console.warn('[StreamCacheV2] IDB read failed:', e);
		}

		return null;
	}

	/**
	 * Synchronous memory-only check (for hot path)
	 */
	getSync(platform: string, videoId: string): StreamInfo | null {
		const key = this.makeKey(platform, videoId);
		const memEntry = this.memoryCache.get(key);
		if (memEntry && !this.isExpired(memEntry)) {
			memEntry.accessCount++;
			memEntry.lastAccessedAt = Date.now();
			return memEntry.info;
		}
		return null;
	}

	/**
	 * Store in cache (L1 + L2)
	 */
	async set(
		platform: string,
		videoId: string,
		info: StreamInfo,
		priority: CachePriority = 'normal'
	): Promise<void> {
		const key = this.makeKey(platform, videoId);
		const now = Date.now();

		const entry: CacheEntry = {
			info,
			cachedAt: now,
			expiresAt: now + IDB_TTL_MS,
			accessCount: 1,
			lastAccessedAt: now,
			priority
		};

		// L1: Store in memory
		this.memoryCache.set(key, { ...entry, expiresAt: now + MEMORY_TTL_MS });
		this.evictMemoryIfNeeded();

		// L2: Store in IndexedDB
		try {
			await this.setInIDB(key, entry);
		} catch (e) {
			console.warn('[StreamCacheV2] IDB write failed:', e);
		}

		// Clear extraction state
		this.extractionStates.delete(key);
	}

	/**
	 * Check if cached (sync, memory only)
	 */
	has(platform: string, videoId: string): boolean {
		const key = this.makeKey(platform, videoId);
		const entry = this.memoryCache.get(key);
		return !!entry && !this.isExpired(entry);
	}

	/**
	 * Check if cached (async, includes IDB)
	 */
	async hasAsync(platform: string, videoId: string): Promise<boolean> {
		if (this.has(platform, videoId)) return true;

		const key = this.makeKey(platform, videoId);
		try {
			const entry = await this.getFromIDB(key);
			return !!entry && !this.isExpired(entry);
		} catch {
			return false;
		}
	}

	/**
	 * Get extraction status
	 */
	getExtractionStatus(platform: string, videoId: string): ExtractionState | null {
		const key = this.makeKey(platform, videoId);
		return this.extractionStates.get(key) || null;
	}

	/**
	 * Set extraction status (for tracking in-flight requests)
	 */
	setExtractionStatus(
		platform: string,
		videoId: string,
		status: ExtractionStatus,
		promise?: Promise<StreamInfo | null>,
		error?: string
	): void {
		const key = this.makeKey(platform, videoId);

		if (status === 'idle') {
			this.extractionStates.delete(key);
		} else {
			this.extractionStates.set(key, {
				status,
				startedAt: Date.now(),
				promise,
				error
			});
		}
	}

	/**
	 * Protect keys from eviction (for queue items)
	 */
	protect(platform: string, videoId: string): void {
		const key = this.makeKey(platform, videoId);
		this.protectedKeys.add(key);
	}

	/**
	 * Remove protection
	 */
	unprotect(platform: string, videoId: string): void {
		const key = this.makeKey(platform, videoId);
		this.protectedKeys.delete(key);
	}

	/**
	 * Clear all protections
	 */
	clearProtections(): void {
		this.protectedKeys.clear();
	}

	/**
	 * Remove from cache
	 */
	async remove(platform: string, videoId: string): Promise<void> {
		const key = this.makeKey(platform, videoId);
		this.memoryCache.delete(key);
		this.extractionStates.delete(key);
		this.protectedKeys.delete(key);

		try {
			await this.deleteFromIDB(key);
		} catch (e) {
			console.warn('[StreamCacheV2] IDB delete failed:', e);
		}
	}

	/**
	 * Clear all caches
	 */
	async clear(): Promise<void> {
		this.memoryCache.clear();
		this.extractionStates.clear();
		this.protectedKeys.clear();

		try {
			const database = await openDB();
			const transaction = database.transaction([STREAM_STORE], 'readwrite');
			const store = transaction.objectStore(STREAM_STORE);
			store.clear();
		} catch (e) {
			console.warn('[StreamCacheV2] IDB clear failed:', e);
		}
	}

	/**
	 * Get cache statistics
	 */
	async getStats(): Promise<{
		memoryCount: number;
		idbCount: number;
		extracting: number;
		platforms: Record<string, number>;
	}> {
		const platforms: Record<string, number> = {};
		let idbCount = 0;

		for (const key of this.memoryCache.keys()) {
			const platform = key.split(':')[0];
			platforms[platform] = (platforms[platform] || 0) + 1;
		}

		try {
			const database = await openDB();
			const transaction = database.transaction([STREAM_STORE], 'readonly');
			const store = transaction.objectStore(STREAM_STORE);
			const countRequest = store.count();

			await new Promise<void>((resolve) => {
				countRequest.onsuccess = () => {
					idbCount = countRequest.result;
					resolve();
				};
			});
		} catch {
			// Ignore
		}

		return {
			memoryCount: this.memoryCache.size,
			idbCount,
			extracting: this.extractionStates.size,
			platforms
		};
	}

	// Private IDB helpers

	private async getFromIDB(key: string): Promise<CacheEntry | null> {
		const database = await openDB();

		return new Promise((resolve, reject) => {
			const transaction = database.transaction([STREAM_STORE], 'readonly');
			const store = transaction.objectStore(STREAM_STORE);
			const request = store.get(key);

			request.onerror = () => reject(request.error);
			request.onsuccess = () => {
				const result = request.result as IDBCacheEntry | undefined;
				if (result) {
					// eslint-disable-next-line @typescript-eslint/no-unused-vars
					const { key: _, ...entry } = result;
					resolve(entry);
				} else {
					resolve(null);
				}
			};
		});
	}

	private async setInIDB(key: string, entry: CacheEntry): Promise<void> {
		const database = await openDB();

		// First, check if we need to evict
		await this.evictIDBIfNeeded();

		return new Promise((resolve, reject) => {
			const transaction = database.transaction([STREAM_STORE], 'readwrite');
			const store = transaction.objectStore(STREAM_STORE);
			const request = store.put({ key, ...entry });

			request.onerror = () => reject(request.error);
			request.onsuccess = () => resolve();
		});
	}

	private async deleteFromIDB(key: string): Promise<void> {
		const database = await openDB();

		return new Promise((resolve, reject) => {
			const transaction = database.transaction([STREAM_STORE], 'readwrite');
			const store = transaction.objectStore(STREAM_STORE);
			const request = store.delete(key);

			request.onerror = () => reject(request.error);
			request.onsuccess = () => resolve();
		});
	}

	private async updateAccessStats(
		key: string,
		accessCount: number,
		lastAccessedAt: number
	): Promise<void> {
		try {
			const database = await openDB();
			const transaction = database.transaction([STREAM_STORE], 'readwrite');
			const store = transaction.objectStore(STREAM_STORE);
			const getRequest = store.get(key);

			getRequest.onsuccess = () => {
				const entry = getRequest.result as IDBCacheEntry | undefined;
				if (entry) {
					entry.accessCount = accessCount;
					entry.lastAccessedAt = lastAccessedAt;
					store.put(entry);
				}
			};
		} catch {
			// Ignore - stats update is best-effort
		}
	}

	private evictMemoryIfNeeded(): void {
		if (this.memoryCache.size <= MEMORY_MAX_ENTRIES) return;

		// Get entries sorted by priority, then access count, then last accessed
		const entries = Array.from(this.memoryCache.entries())
			.filter(([key]) => !this.protectedKeys.has(key))
			.sort(([, a], [, b]) => {
				// Priority order: critical > high > normal > low
				const priorityOrder = { critical: 0, high: 1, normal: 2, low: 3 };
				const priorityDiff = priorityOrder[b.priority] - priorityOrder[a.priority];
				if (priorityDiff !== 0) return priorityDiff;

				// Then by access count (descending - keep more accessed)
				const accessDiff = a.accessCount - b.accessCount;
				if (accessDiff !== 0) return accessDiff;

				// Then by last accessed (ascending - evict least recently used)
				return a.lastAccessedAt - b.lastAccessedAt;
			});

		// Evict oldest/lowest priority entries
		const toEvict = entries.slice(0, this.memoryCache.size - MEMORY_MAX_ENTRIES);
		for (const [key] of toEvict) {
			this.memoryCache.delete(key);
		}
	}

	private async evictIDBIfNeeded(): Promise<void> {
		try {
			const database = await openDB();
			const transaction = database.transaction([STREAM_STORE], 'readonly');
			const store = transaction.objectStore(STREAM_STORE);
			const countRequest = store.count();

			const count = await new Promise<number>((resolve) => {
				countRequest.onsuccess = () => resolve(countRequest.result);
			});

			if (count < IDB_MAX_ENTRIES) return;

			// Need to evict - get all entries and sort
			const getAllRequest = store.getAll();
			const entries = await new Promise<IDBCacheEntry[]>((resolve) => {
				getAllRequest.onsuccess = () => resolve(getAllRequest.result);
			});

			const now = Date.now();

			// First, remove expired entries
			const expired = entries.filter((e) => e.expiresAt < now);

			// Then sort remaining by priority/access for eviction
			const valid = entries
				.filter((e) => e.expiresAt >= now && !this.protectedKeys.has(e.key))
				.sort((a, b) => {
					const priorityOrder = { critical: 0, high: 1, normal: 2, low: 3 };
					const priorityDiff = priorityOrder[b.priority] - priorityOrder[a.priority];
					if (priorityDiff !== 0) return priorityDiff;
					return a.accessCount - b.accessCount;
				});

			// Calculate how many to evict (expired + lowest priority until under limit)
			const toEvict = [...expired];
			const remaining = entries.length - expired.length;
			if (remaining >= IDB_MAX_ENTRIES) {
				const extraEvict = remaining - IDB_MAX_ENTRIES + 50; // Evict 50 extra for buffer
				toEvict.push(...valid.slice(0, extraEvict));
			}

			// Delete evicted entries
			if (toEvict.length > 0) {
				const deleteTransaction = database.transaction([STREAM_STORE], 'readwrite');
				const deleteStore = deleteTransaction.objectStore(STREAM_STORE);
				for (const entry of toEvict) {
					deleteStore.delete(entry.key);
				}
				console.log(`[StreamCacheV2] Evicted ${toEvict.length} entries from IDB`);
			}
		} catch (e) {
			console.warn('[StreamCacheV2] IDB eviction failed:', e);
		}
	}
}

// Singleton instance
export const streamCache = new MultiTierStreamCache();

/**
 * Fetch stream info with caching
 * Returns cached if available, otherwise fetches and caches
 */
export async function fetchStreamInfo(
	platform: string,
	videoId: string,
	priority: CachePriority = 'normal',
	videoUrl?: string
): Promise<StreamInfo | null> {
	// Check cache first
	const cached = await streamCache.get(platform, videoId);
	if (cached) {
		return cached;
	}

	// Check if already extracting
	const state = streamCache.getExtractionStatus(platform, videoId);
	if (state?.status === 'extracting' && state.promise) {
		return state.promise;
	}

	// Only YouTube and Red Bar support direct streams currently
	if (platform !== 'youtube' && platform !== 'redbar') {
		return null;
	}

	// Start extraction
	const promise = (async (): Promise<StreamInfo | null> => {
		try {
			// Build URL with optional video_url query param for Red Bar
			let url = `/api/stream/${platform}/${videoId}`;
			if (videoUrl) {
				url += `?video_url=${encodeURIComponent(videoUrl)}`;
			}

			const response = await fetch(url);
			if (response.ok) {
				const info: StreamInfo = await response.json();
				await streamCache.set(platform, videoId, info, priority);
				return info;
			}
			streamCache.setExtractionStatus(platform, videoId, 'failed', undefined, 'HTTP error');
			return null;
		} catch (e) {
			streamCache.setExtractionStatus(
				platform,
				videoId,
				'failed',
				undefined,
				e instanceof Error ? e.message : 'Unknown error'
			);
			return null;
		}
	})();

	streamCache.setExtractionStatus(platform, videoId, 'extracting', promise);

	return promise;
}

/**
 * Prefetch stream info in the background
 * Lower priority, won't block or throw
 */
export async function prefetchStreamInfo(
	platform: string,
	videoId: string,
	priority: CachePriority = 'low'
): Promise<void> {
	// Skip if already cached or extracting
	if (streamCache.has(platform, videoId)) return;

	const state = streamCache.getExtractionStatus(platform, videoId);
	if (state?.status === 'extracting') return;

	// Fire and forget
	fetchStreamInfo(platform, videoId, priority).catch(() => {
		// Ignore prefetch errors
	});
}

/**
 * Prefetch multiple streams (for queue warming)
 */
export async function prefetchStreams(
	videos: Array<{ platform: string; videoId: string; priority?: CachePriority }>
): Promise<void> {
	const toPrefetch = videos.filter(
		(v) =>
			v.platform === 'youtube' &&
			!streamCache.has(v.platform, v.videoId) &&
			streamCache.getExtractionStatus(v.platform, v.videoId)?.status !== 'extracting'
	);

	// Prefetch in parallel but with limited concurrency
	const concurrency = 2;
	for (let i = 0; i < toPrefetch.length; i += concurrency) {
		const batch = toPrefetch.slice(i, i + concurrency);
		await Promise.allSettled(
			batch.map((v) => fetchStreamInfo(v.platform, v.videoId, v.priority || 'low'))
		);
	}
}
