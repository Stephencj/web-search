<script lang="ts">
	/**
	 * Native PiP Tracker
	 *
	 * Listens for native browser Picture-in-Picture events (iOS Safari)
	 * and updates the videoPlayer store accordingly.
	 * This allows the modal to be dismissed while video continues in native PiP.
	 */
	import { videoPlayer } from '$lib/stores/videoPlayer.svelte';

	function handleEnterPiP() {
		videoPlayer.setNativePiPActive(true);
	}

	function handleLeavePiP() {
		videoPlayer.setNativePiPActive(false);
	}

	$effect(() => {
		if (typeof document === 'undefined') return;

		// Check initial state in case PiP was already active
		if (document.pictureInPictureElement) {
			videoPlayer.setNativePiPActive(true);
		}

		// Listen for PiP events on document (captures all video elements)
		document.addEventListener('enterpictureinpicture', handleEnterPiP);
		document.addEventListener('leavepictureinpicture', handleLeavePiP);

		return () => {
			document.removeEventListener('enterpictureinpicture', handleEnterPiP);
			document.removeEventListener('leavepictureinpicture', handleLeavePiP);
		};
	});
</script>
