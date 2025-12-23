/**
 * Persistent Stream Cache
 * Stores stream URLs in localStorage for faster video startup in collections.
 * Stream URLs typically expire after ~6 hours, so we include expiration tracking.
 */

import type { StreamInfo } from './videoPlayer.svelte';

const STORAGE_KEY = 'websearch-stream-cache';
const CACHE_TTL_MS = 5 * 60 * 60 * 1000; // 5 hours (YouTube streams last ~6h)
const MAX_ENTRIES = 50; // Limit cache size

interface CachedStream {
	info: StreamInfo;
	cachedAt: number;
	expiresAt: number;
}

type StreamCacheStore = Record<string, CachedStream>;

function loadFromStorage(): StreamCacheStore {
	if (typeof window === 'undefined') return {};
	try {
		const data = localStorage.getItem(STORAGE_KEY);
		return data ? JSON.parse(data) : {};
	} catch {
		return {};
	}
}

function saveToStorage(store: StreamCacheStore) {
	if (typeof window === 'undefined') return;
	try {
		localStorage.setItem(STORAGE_KEY, JSON.stringify(store));
	} catch (e) {
		console.warn('[StreamCache] Storage save failed:', e);
	}
}

function isExpired(entry: CachedStream): boolean {
	return Date.now() > entry.expiresAt;
}

function pruneStore(store: StreamCacheStore): StreamCacheStore {
	const entries = Object.entries(store);
	// Remove expired entries
	const valid = entries.filter(([_, entry]) => !isExpired(entry));
	// Keep only newest if over limit
	if (valid.length > MAX_ENTRIES) {
		valid.sort((a, b) => b[1].cachedAt - a[1].cachedAt);
		return Object.fromEntries(valid.slice(0, MAX_ENTRIES));
	}
	return Object.fromEntries(valid);
}

class PersistentStreamCache {
	private store: StreamCacheStore;
	private memoryCache: Map<string, StreamInfo>;

	constructor() {
		this.store = loadFromStorage();
		this.memoryCache = new Map();
		// Load valid cached entries into memory
		for (const [key, entry] of Object.entries(this.store)) {
			if (!isExpired(entry)) {
				this.memoryCache.set(key, entry.info);
			}
		}
	}

	/**
	 * Get cached stream info
	 */
	get(platform: string, videoId: string): StreamInfo | null {
		const key = `${platform}:${videoId}`;

		// Check memory first
		if (this.memoryCache.has(key)) {
			return this.memoryCache.get(key)!;
		}

		// Check persistent storage
		const cached = this.store[key];
		if (cached && !isExpired(cached)) {
			this.memoryCache.set(key, cached.info);
			return cached.info;
		}

		return null;
	}

	/**
	 * Cache stream info
	 */
	set(platform: string, videoId: string, info: StreamInfo): void {
		const key = `${platform}:${videoId}`;
		const now = Date.now();

		// Store in memory
		this.memoryCache.set(key, info);

		// Store persistently
		this.store[key] = {
			info,
			cachedAt: now,
			expiresAt: now + CACHE_TTL_MS
		};

		this.store = pruneStore(this.store);
		saveToStorage(this.store);
	}

	/**
	 * Check if a stream is cached and valid
	 */
	has(platform: string, videoId: string): boolean {
		return this.get(platform, videoId) !== null;
	}

	/**
	 * Remove a cached entry
	 */
	remove(platform: string, videoId: string): void {
		const key = `${platform}:${videoId}`;
		this.memoryCache.delete(key);
		delete this.store[key];
		saveToStorage(this.store);
	}

	/**
	 * Clear all cached entries
	 */
	clear(): void {
		this.memoryCache.clear();
		this.store = {};
		saveToStorage(this.store);
	}

	/**
	 * Get cache statistics
	 */
	getStats(): { count: number; platforms: Record<string, number> } {
		const platforms: Record<string, number> = {};
		for (const key of Object.keys(this.store)) {
			const platform = key.split(':')[0];
			platforms[platform] = (platforms[platform] || 0) + 1;
		}
		return { count: Object.keys(this.store).length, platforms };
	}
}

// Singleton instance
export const persistentStreamCache = new PersistentStreamCache();

/**
 * Pre-cache a video stream in the background
 */
export async function precacheVideoStream(platform: string, videoId: string): Promise<void> {
	// Only YouTube supports direct streams currently
	if (platform !== 'youtube') return;

	// Skip if already cached
	if (persistentStreamCache.has(platform, videoId)) {
		console.log('[StreamCache] Already cached:', platform, videoId);
		return;
	}

	try {
		const response = await fetch(`/api/stream/${platform}/${videoId}`);
		if (response.ok) {
			const info = await response.json();
			persistentStreamCache.set(platform, videoId, info);
			console.log('[StreamCache] Pre-cached:', platform, videoId);
		}
	} catch (e) {
		console.warn('[StreamCache] Pre-cache failed:', platform, videoId, e);
	}
}

/**
 * Pre-cache multiple video streams in parallel
 */
export async function precacheVideoStreams(
	videos: Array<{ platform: string; videoId: string }>
): Promise<void> {
	const promises = videos
		.filter((v) => v.platform === 'youtube') // Only YouTube supports streams
		.filter((v) => !persistentStreamCache.has(v.platform, v.videoId))
		.map((v) => precacheVideoStream(v.platform, v.videoId));

	await Promise.allSettled(promises);
}
