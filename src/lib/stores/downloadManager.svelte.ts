/**
 * Download Manager
 * Manages video downloads for offline access with progress tracking.
 */

import {
	storeVideo,
	isVideoOffline,
	deleteVideo,
	listDownloadedVideos,
	getStorageUsed,
	type DownloadMetadata
} from './offlineStorage';

export type DownloadStatus = 'queued' | 'downloading' | 'completed' | 'failed' | 'paused';

export interface DownloadState {
	platform: string;
	videoId: string;
	title: string;
	thumbnailUrl: string | null;
	status: DownloadStatus;
	progress: number; // 0-100
	downloadedBytes: number;
	totalBytes: number;
	error?: string;
	startedAt?: number;
	completedAt?: number;
}

// Reactive state using Svelte 5 runes
let downloads = $state<Map<string, DownloadState>>(new Map());
let offlineVideos = $state<DownloadMetadata[]>([]);
let storageUsed = $state<number>(0);
let isInitialized = $state(false);

// Default storage limit: 2GB
const DEFAULT_STORAGE_LIMIT = 2 * 1024 * 1024 * 1024;
let storageLimit = $state(DEFAULT_STORAGE_LIMIT);

/**
 * Initialize the download manager
 */
async function initialize() {
	if (isInitialized) return;

	try {
		offlineVideos = await listDownloadedVideos();
		storageUsed = await getStorageUsed();
		isInitialized = true;
	} catch (e) {
		console.error('[DownloadManager] Failed to initialize:', e);
	}
}

/**
 * Get the download key for a video
 */
function getKey(platform: string, videoId: string): string {
	return `${platform}:${videoId}`;
}

/**
 * Check if a video is available offline
 */
async function checkOffline(platform: string, videoId: string): Promise<boolean> {
	return isVideoOffline(platform, videoId);
}

/**
 * Get the current download state for a video
 */
function getDownloadState(platform: string, videoId: string): DownloadState | null {
	return downloads.get(getKey(platform, videoId)) || null;
}

/**
 * Update download state
 */
function updateDownloadState(platform: string, videoId: string, update: Partial<DownloadState>) {
	const key = getKey(platform, videoId);
	const existing = downloads.get(key);
	if (existing) {
		downloads.set(key, { ...existing, ...update });
		downloads = new Map(downloads); // Trigger reactivity
	}
}

/**
 * Queue a video for download
 */
async function queueDownload(video: {
	platform: string;
	videoId: string;
	title: string;
	thumbnailUrl: string | null;
}): Promise<boolean> {
	const key = getKey(video.platform, video.videoId);

	// Check if already downloaded
	if (await isVideoOffline(video.platform, video.videoId)) {
		console.log('[DownloadManager] Video already downloaded:', key);
		return false;
	}

	// Check if already in queue
	if (downloads.has(key)) {
		console.log('[DownloadManager] Video already in download queue:', key);
		return false;
	}

	// Add to queue
	const state: DownloadState = {
		platform: video.platform,
		videoId: video.videoId,
		title: video.title,
		thumbnailUrl: video.thumbnailUrl,
		status: 'queued',
		progress: 0,
		downloadedBytes: 0,
		totalBytes: 0
	};

	downloads.set(key, state);
	downloads = new Map(downloads);

	// Start download
	startDownload(video.platform, video.videoId).catch((e) => {
		console.error('[DownloadManager] Download failed:', e);
	});

	return true;
}

/**
 * Start downloading a video
 * Note: This requires a backend endpoint to provide the downloadable video stream
 */
async function startDownload(platform: string, videoId: string): Promise<void> {
	const key = getKey(platform, videoId);
	const state = downloads.get(key);
	if (!state) return;

	updateDownloadState(platform, videoId, {
		status: 'downloading',
		startedAt: Date.now()
	});

	try {
		// Fetch download info from backend
		// This endpoint needs to return the video stream
		const infoResponse = await fetch(`/api/download/${platform}/${videoId}/info`);
		if (!infoResponse.ok) {
			throw new Error(`Failed to get download info: ${infoResponse.status}`);
		}

		const info = await infoResponse.json();
		const totalBytes = info.size || 0;

		updateDownloadState(platform, videoId, { totalBytes });

		// Check storage before downloading
		if (storageUsed + totalBytes > storageLimit) {
			throw new Error('Insufficient storage space');
		}

		// Download the video
		const response = await fetch(`/api/download/${platform}/${videoId}`);
		if (!response.ok) {
			throw new Error(`Download failed: ${response.status}`);
		}

		const contentLength = response.headers.get('content-length');
		const total = contentLength ? parseInt(contentLength, 10) : totalBytes;

		if (total > 0) {
			updateDownloadState(platform, videoId, { totalBytes: total });
		}

		// Read the response as a stream with progress tracking
		const reader = response.body?.getReader();
		if (!reader) {
			throw new Error('Response body not readable');
		}

		const chunks: Uint8Array[] = [];
		let receivedBytes = 0;

		while (true) {
			const { done, value } = await reader.read();
			if (done) break;

			chunks.push(value);
			receivedBytes += value.length;

			// Update progress
			const progress = total > 0 ? Math.round((receivedBytes / total) * 100) : 0;
			updateDownloadState(platform, videoId, {
				downloadedBytes: receivedBytes,
				progress
			});
		}

		// Combine chunks into a blob
		const blob = new Blob(chunks, { type: info.mimeType || 'video/mp4' });

		// Store in IndexedDB
		await storeVideo(platform, videoId, blob, {
			title: state.title,
			thumbnailUrl: state.thumbnailUrl,
			duration: info.duration || null,
			mimeType: info.mimeType || 'video/mp4',
			quality: info.quality
		});

		// Update state
		updateDownloadState(platform, videoId, {
			status: 'completed',
			progress: 100,
			completedAt: Date.now()
		});

		// Refresh offline videos list
		offlineVideos = await listDownloadedVideos();
		storageUsed = await getStorageUsed();

		console.log('[DownloadManager] Download complete:', key);
	} catch (e) {
		const errorMessage = e instanceof Error ? e.message : 'Download failed';
		updateDownloadState(platform, videoId, {
			status: 'failed',
			error: errorMessage
		});
		console.error('[DownloadManager] Download error:', key, e);
	}
}

/**
 * Cancel a download
 */
function cancelDownload(platform: string, videoId: string): void {
	const key = getKey(platform, videoId);
	downloads.delete(key);
	downloads = new Map(downloads);
}

/**
 * Remove an offline video
 */
async function removeOfflineVideo(platform: string, videoId: string): Promise<void> {
	await deleteVideo(platform, videoId);
	offlineVideos = await listDownloadedVideos();
	storageUsed = await getStorageUsed();

	// Also remove from downloads if present
	const key = getKey(platform, videoId);
	if (downloads.has(key)) {
		downloads.delete(key);
		downloads = new Map(downloads);
	}
}

/**
 * Clear all downloads in progress
 */
function clearDownloadsQueue(): void {
	downloads.clear();
	downloads = new Map(downloads);
}

/**
 * Set storage limit
 */
function setStorageLimit(bytes: number): void {
	storageLimit = bytes;
}

// Export the download manager
export const downloadManager = {
	// Initialize
	initialize,

	// State getters (reactive)
	get downloads() {
		return downloads;
	},
	get offlineVideos() {
		return offlineVideos;
	},
	get storageUsed() {
		return storageUsed;
	},
	get storageLimit() {
		return storageLimit;
	},
	get isInitialized() {
		return isInitialized;
	},

	// Actions
	queueDownload,
	cancelDownload,
	removeOfflineVideo,
	clearDownloadsQueue,
	setStorageLimit,
	getDownloadState,
	checkOffline
};
