/**
 * Playback Control Composable
 *
 * Handles global play/pause/seek events from media session and cross-component communication.
 * Provides unified interface for controlling any active player (YouTube API, video element, audio element).
 *
 * Usage:
 *   const controls = usePlaybackControl();
 *   controls.registerHandlers(player);
 *   // ... on cleanup
 *   controls.cleanup();
 */

import { PLAYER_EVENTS } from '$lib/stores/videoPlayer.svelte';

export interface PlayerElements {
	getYtPlayer?: () => { playVideo: () => void; pauseVideo: () => void; seekTo: (t: number, b: boolean) => void; getCurrentTime: () => number; getDuration: () => number } | null;
	getVideoElement?: () => HTMLVideoElement | null;
	getAudioElement?: () => HTMLAudioElement | null;
	isYtPlayerReady?: () => boolean;
}

export interface PlaybackControlResult {
	play: () => void;
	pause: () => void;
	seek: (offset: number) => void;
	seekTo: (time: number) => void;
	getCurrentTime: () => number;
	getDuration: () => number;
	registerHandlers: (elements: PlayerElements) => void;
	cleanup: () => void;
}

export function usePlaybackControl(): PlaybackControlResult {
	let playerElements: PlayerElements = {};
	let cleanupFns: (() => void)[] = [];

	function getActivePlayer(): 'yt' | 'video' | 'audio' | null {
		if (playerElements.isYtPlayerReady?.() && playerElements.getYtPlayer?.()) {
			return 'yt';
		}
		if (playerElements.getVideoElement?.()) {
			return 'video';
		}
		if (playerElements.getAudioElement?.()) {
			return 'audio';
		}
		return null;
	}

	function play(): void {
		const active = getActivePlayer();
		switch (active) {
			case 'yt':
				playerElements.getYtPlayer?.()?.playVideo();
				break;
			case 'video':
				playerElements.getVideoElement?.()?.play().catch(() => {});
				break;
			case 'audio':
				playerElements.getAudioElement?.()?.play().catch(() => {});
				break;
		}
	}

	function pause(): void {
		const active = getActivePlayer();
		switch (active) {
			case 'yt':
				playerElements.getYtPlayer?.()?.pauseVideo();
				break;
			case 'video':
				playerElements.getVideoElement?.()?.pause();
				break;
			case 'audio':
				playerElements.getAudioElement?.()?.pause();
				break;
		}
	}

	function getCurrentTime(): number {
		const active = getActivePlayer();
		switch (active) {
			case 'yt':
				try {
					return playerElements.getYtPlayer?.()?.getCurrentTime() ?? 0;
				} catch {
					return 0;
				}
			case 'video':
				return playerElements.getVideoElement?.()?.currentTime ?? 0;
			case 'audio':
				return playerElements.getAudioElement?.()?.currentTime ?? 0;
			default:
				return 0;
		}
	}

	function getDuration(): number {
		const active = getActivePlayer();
		switch (active) {
			case 'yt':
				try {
					return playerElements.getYtPlayer?.()?.getDuration() ?? 0;
				} catch {
					return 0;
				}
			case 'video': {
				const el = playerElements.getVideoElement?.();
				return el?.duration ?? 0;
			}
			case 'audio': {
				const el = playerElements.getAudioElement?.();
				return el?.duration ?? 0;
			}
			default:
				return 0;
		}
	}

	function seek(offset: number): void {
		const currentTime = getCurrentTime();
		const duration = getDuration();
		const newTime = Math.max(0, Math.min(currentTime + offset, duration));
		seekTo(newTime);
	}

	function seekTo(time: number): void {
		const active = getActivePlayer();
		switch (active) {
			case 'yt':
				playerElements.getYtPlayer?.()?.seekTo(time, true);
				break;
			case 'video': {
				const el = playerElements.getVideoElement?.();
				if (el) el.currentTime = time;
				break;
			}
			case 'audio': {
				const el = playerElements.getAudioElement?.();
				if (el) el.currentTime = time;
				break;
			}
		}
	}

	function registerHandlers(elements: PlayerElements): void {
		playerElements = elements;

		// Global event handlers
		function handlePlay() {
			play();
		}
		function handlePause() {
			pause();
		}
		function handleSeek(e: Event) {
			const detail = (e as CustomEvent).detail;
			if (detail?.offset !== undefined) {
				seek(detail.offset);
			}
		}
		function handleSeekTo(e: Event) {
			const detail = (e as CustomEvent).detail;
			if (detail?.time !== undefined) {
				seekTo(detail.time);
			}
		}

		window.addEventListener(PLAYER_EVENTS.PLAY, handlePlay);
		window.addEventListener(PLAYER_EVENTS.PAUSE, handlePause);
		window.addEventListener(PLAYER_EVENTS.SEEK, handleSeek);
		window.addEventListener(PLAYER_EVENTS.SEEK_TO, handleSeekTo);

		cleanupFns.push(() => {
			window.removeEventListener(PLAYER_EVENTS.PLAY, handlePlay);
			window.removeEventListener(PLAYER_EVENTS.PAUSE, handlePause);
			window.removeEventListener(PLAYER_EVENTS.SEEK, handleSeek);
			window.removeEventListener(PLAYER_EVENTS.SEEK_TO, handleSeekTo);
		});
	}

	function cleanup(): void {
		for (const fn of cleanupFns) {
			fn();
		}
		cleanupFns = [];
		playerElements = {};
	}

	return {
		play,
		pause,
		seek,
		seekTo,
		getCurrentTime,
		getDuration,
		registerHandlers,
		cleanup
	};
}

/**
 * Dispatch a global player event
 */
export function dispatchPlayerEvent(eventName: string, detail?: unknown): void {
	if (typeof window !== 'undefined') {
		window.dispatchEvent(new CustomEvent(eventName, { detail }));
	}
}
