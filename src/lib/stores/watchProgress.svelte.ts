/**
 * Watch Progress Store
 * Manages local persistence of video watch progress with API sync
 *
 * This provides immediate localStorage backup for watch progress,
 * ensuring progress is never lost due to network failures or page crashes.
 */

const STORAGE_KEY = 'websearch-watch-progress';
const MAX_ENTRIES = 100; // Limit storage size

interface ProgressEntry {
	seconds: number;
	timestamp: number;
	synced: boolean;
}

type ProgressStore = Record<string, ProgressEntry>;

function loadFromStorage(): ProgressStore {
	if (typeof window === 'undefined') return {};
	try {
		const data = localStorage.getItem(STORAGE_KEY);
		return data ? JSON.parse(data) : {};
	} catch {
		return {};
	}
}

function saveToStorage(store: ProgressStore) {
	if (typeof window === 'undefined') return;
	try {
		localStorage.setItem(STORAGE_KEY, JSON.stringify(store));
	} catch (e) {
		console.warn('[WatchProgress] Storage save failed:', e);
	}
}

function pruneStore(store: ProgressStore): ProgressStore {
	const entries = Object.entries(store);
	if (entries.length <= MAX_ENTRIES) return store;

	// Sort by timestamp, keep newest
	entries.sort((a, b) => b[1].timestamp - a[1].timestamp);
	return Object.fromEntries(entries.slice(0, MAX_ENTRIES));
}

class WatchProgressStore {
	private store: ProgressStore;

	constructor() {
		this.store = loadFromStorage();
	}

	/**
	 * Save progress locally (immediate persistence)
	 */
	save(sourceType: 'feed' | 'saved', sourceId: number, seconds: number): void {
		const key = `${sourceType}:${sourceId}`;
		this.store[key] = {
			seconds,
			timestamp: Date.now(),
			synced: false
		};
		this.store = pruneStore(this.store);
		saveToStorage(this.store);
	}

	/**
	 * Get local progress for a video
	 */
	get(sourceType: 'feed' | 'saved', sourceId: number): number | null {
		const key = `${sourceType}:${sourceId}`;
		return this.store[key]?.seconds ?? null;
	}

	/**
	 * Get effective progress (max of local and API)
	 */
	getEffective(
		sourceType: 'feed' | 'saved' | 'discover',
		sourceId: number | undefined,
		apiProgress: number | undefined
	): number | undefined {
		if (sourceType === 'discover' || !sourceId) {
			return apiProgress;
		}
		const localProgress = this.get(sourceType as 'feed' | 'saved', sourceId);
		const maxProgress = Math.max(localProgress ?? 0, apiProgress ?? 0);
		return maxProgress > 0 ? maxProgress : undefined;
	}

	/**
	 * Mark progress as synced with API
	 */
	markSynced(sourceType: 'feed' | 'saved', sourceId: number): void {
		const key = `${sourceType}:${sourceId}`;
		if (this.store[key]) {
			this.store[key].synced = true;
			saveToStorage(this.store);
		}
	}

	/**
	 * Clear progress for a video (after marking as watched)
	 */
	clear(sourceType: 'feed' | 'saved', sourceId: number): void {
		const key = `${sourceType}:${sourceId}`;
		delete this.store[key];
		saveToStorage(this.store);
	}

	/**
	 * Get all unsynced entries for background sync
	 */
	getUnsynced(): Array<{ sourceType: 'feed' | 'saved'; sourceId: number; seconds: number }> {
		return Object.entries(this.store)
			.filter(([_, entry]) => !entry.synced)
			.map(([key, entry]) => {
				const [sourceType, sourceIdStr] = key.split(':');
				return {
					sourceType: sourceType as 'feed' | 'saved',
					sourceId: parseInt(sourceIdStr, 10),
					seconds: entry.seconds
				};
			});
	}

	/**
	 * Check if we have local progress for a video
	 */
	has(sourceType: 'feed' | 'saved', sourceId: number): boolean {
		const key = `${sourceType}:${sourceId}`;
		return key in this.store;
	}

	/**
	 * Get timestamp of when progress was last saved
	 */
	getTimestamp(sourceType: 'feed' | 'saved', sourceId: number): number | null {
		const key = `${sourceType}:${sourceId}`;
		return this.store[key]?.timestamp ?? null;
	}
}

// Singleton instance
export const watchProgress = new WatchProgressStore();
