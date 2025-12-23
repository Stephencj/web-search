/**
 * Offline Storage
 * IndexedDB wrapper for storing downloaded videos for offline access.
 */

const DB_NAME = 'websearch-offline';
const DB_VERSION = 1;
const VIDEO_STORE = 'videos';
const METADATA_STORE = 'metadata';

export interface DownloadMetadata {
	platform: string;
	videoId: string;
	title: string;
	thumbnailUrl: string | null;
	duration: number | null;
	fileSize: number;
	mimeType: string;
	downloadedAt: number;
	quality?: string;
}

interface VideoBlob {
	key: string; // platform:videoId
	blob: Blob;
	metadata: DownloadMetadata;
}

let db: IDBDatabase | null = null;

/**
 * Open the IndexedDB database
 */
async function openDB(): Promise<IDBDatabase> {
	if (db) return db;

	return new Promise((resolve, reject) => {
		const request = indexedDB.open(DB_NAME, DB_VERSION);

		request.onerror = () => reject(request.error);
		request.onsuccess = () => {
			db = request.result;
			resolve(db);
		};

		request.onupgradeneeded = (event) => {
			const database = (event.target as IDBOpenDBRequest).result;

			// Store for video blobs
			if (!database.objectStoreNames.contains(VIDEO_STORE)) {
				database.createObjectStore(VIDEO_STORE, { keyPath: 'key' });
			}

			// Store for metadata only (for listing without loading blobs)
			if (!database.objectStoreNames.contains(METADATA_STORE)) {
				const metaStore = database.createObjectStore(METADATA_STORE, { keyPath: 'key' });
				metaStore.createIndex('platform', 'platform', { unique: false });
				metaStore.createIndex('downloadedAt', 'downloadedAt', { unique: false });
			}
		};
	});
}

/**
 * Store a downloaded video
 */
export async function storeVideo(
	platform: string,
	videoId: string,
	blob: Blob,
	metadata: Omit<DownloadMetadata, 'platform' | 'videoId' | 'fileSize' | 'downloadedAt'>
): Promise<void> {
	const database = await openDB();
	const key = `${platform}:${videoId}`;

	const fullMetadata: DownloadMetadata = {
		...metadata,
		platform,
		videoId,
		fileSize: blob.size,
		downloadedAt: Date.now()
	};

	const videoData: VideoBlob = {
		key,
		blob,
		metadata: fullMetadata
	};

	return new Promise((resolve, reject) => {
		const transaction = database.transaction([VIDEO_STORE, METADATA_STORE], 'readwrite');

		transaction.onerror = () => reject(transaction.error);
		transaction.oncomplete = () => resolve();

		// Store video blob
		const videoStore = transaction.objectStore(VIDEO_STORE);
		videoStore.put(videoData);

		// Store metadata separately for fast listing
		const metaStore = transaction.objectStore(METADATA_STORE);
		metaStore.put({ key, ...fullMetadata });
	});
}

/**
 * Get a downloaded video blob
 */
export async function getVideo(platform: string, videoId: string): Promise<Blob | null> {
	const database = await openDB();
	const key = `${platform}:${videoId}`;

	return new Promise((resolve, reject) => {
		const transaction = database.transaction([VIDEO_STORE], 'readonly');
		const store = transaction.objectStore(VIDEO_STORE);
		const request = store.get(key);

		request.onerror = () => reject(request.error);
		request.onsuccess = () => {
			const result = request.result as VideoBlob | undefined;
			resolve(result?.blob || null);
		};
	});
}

/**
 * Get video blob URL for playback
 */
export async function getVideoUrl(platform: string, videoId: string): Promise<string | null> {
	const blob = await getVideo(platform, videoId);
	if (!blob) return null;
	return URL.createObjectURL(blob);
}

/**
 * Check if a video is available offline
 */
export async function isVideoOffline(platform: string, videoId: string): Promise<boolean> {
	const database = await openDB();
	const key = `${platform}:${videoId}`;

	return new Promise((resolve, reject) => {
		const transaction = database.transaction([METADATA_STORE], 'readonly');
		const store = transaction.objectStore(METADATA_STORE);
		const request = store.get(key);

		request.onerror = () => reject(request.error);
		request.onsuccess = () => {
			resolve(!!request.result);
		};
	});
}

/**
 * Get metadata for a downloaded video
 */
export async function getVideoMetadata(
	platform: string,
	videoId: string
): Promise<DownloadMetadata | null> {
	const database = await openDB();
	const key = `${platform}:${videoId}`;

	return new Promise((resolve, reject) => {
		const transaction = database.transaction([METADATA_STORE], 'readonly');
		const store = transaction.objectStore(METADATA_STORE);
		const request = store.get(key);

		request.onerror = () => reject(request.error);
		request.onsuccess = () => {
			const result = request.result;
			if (result) {
				// eslint-disable-next-line @typescript-eslint/no-unused-vars
				const { key: _, ...metadata } = result;
				resolve(metadata as DownloadMetadata);
			} else {
				resolve(null);
			}
		};
	});
}

/**
 * List all downloaded videos
 */
export async function listDownloadedVideos(): Promise<DownloadMetadata[]> {
	const database = await openDB();

	return new Promise((resolve, reject) => {
		const transaction = database.transaction([METADATA_STORE], 'readonly');
		const store = transaction.objectStore(METADATA_STORE);
		const request = store.getAll();

		request.onerror = () => reject(request.error);
		request.onsuccess = () => {
			const results = request.result.map((r: { key: string } & DownloadMetadata) => {
				// eslint-disable-next-line @typescript-eslint/no-unused-vars
				const { key: _, ...metadata } = r;
				return metadata as DownloadMetadata;
			});
			// Sort by download date, newest first
			results.sort((a: DownloadMetadata, b: DownloadMetadata) => b.downloadedAt - a.downloadedAt);
			resolve(results);
		};
	});
}

/**
 * Delete a downloaded video
 */
export async function deleteVideo(platform: string, videoId: string): Promise<void> {
	const database = await openDB();
	const key = `${platform}:${videoId}`;

	return new Promise((resolve, reject) => {
		const transaction = database.transaction([VIDEO_STORE, METADATA_STORE], 'readwrite');

		transaction.onerror = () => reject(transaction.error);
		transaction.oncomplete = () => resolve();

		const videoStore = transaction.objectStore(VIDEO_STORE);
		videoStore.delete(key);

		const metaStore = transaction.objectStore(METADATA_STORE);
		metaStore.delete(key);
	});
}

/**
 * Clear all downloaded videos
 */
export async function clearAllVideos(): Promise<void> {
	const database = await openDB();

	return new Promise((resolve, reject) => {
		const transaction = database.transaction([VIDEO_STORE, METADATA_STORE], 'readwrite');

		transaction.onerror = () => reject(transaction.error);
		transaction.oncomplete = () => resolve();

		const videoStore = transaction.objectStore(VIDEO_STORE);
		videoStore.clear();

		const metaStore = transaction.objectStore(METADATA_STORE);
		metaStore.clear();
	});
}

/**
 * Get total storage used by downloaded videos
 */
export async function getStorageUsed(): Promise<number> {
	const videos = await listDownloadedVideos();
	return videos.reduce((total, v) => total + v.fileSize, 0);
}

/**
 * Get storage quota information
 */
export async function getStorageQuota(): Promise<{ used: number; quota: number } | null> {
	if (!navigator.storage || !navigator.storage.estimate) {
		return null;
	}

	try {
		const estimate = await navigator.storage.estimate();
		return {
			used: estimate.usage || 0,
			quota: estimate.quota || 0
		};
	} catch {
		return null;
	}
}

/**
 * Format bytes to human readable string
 */
export function formatBytes(bytes: number): string {
	if (bytes === 0) return '0 B';
	const k = 1024;
	const sizes = ['B', 'KB', 'MB', 'GB'];
	const i = Math.floor(Math.log(bytes) / Math.log(k));
	return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}
