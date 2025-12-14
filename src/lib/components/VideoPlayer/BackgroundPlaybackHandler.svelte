<script lang="ts">
  import { videoPlayer } from '$lib/stores/videoPlayer.svelte';
  import { playbackPreferences } from '$lib/stores/playbackPreferences.svelte';

  /**
   * Global handler for background playback across all video player modes.
   * This component should be mounted in the root layout to ensure it's always active.
   *
   * When the user switches tabs with a video playing:
   * - If background playback is enabled, attempts to continue playback
   * - For iframes: switches to PiP mode for better background handling
   * - For direct video: attempts native Picture-in-Picture
   */

  // Track whether we automatically switched to PiP
  let autoSwitchedToPiP = $state(false);

  const isPlaying = $derived(videoPlayer.isOpen);
  const isModal = $derived(videoPlayer.isModal);
  const isPiP = $derived(videoPlayer.isPiP);

  function handleVisibilityChange() {
    // Only act if a video is open and background playback is enabled
    if (!isPlaying || !playbackPreferences.backgroundPlayback) return;

    if (document.hidden) {
      console.log('[Background] Tab hidden, mode:', isModal ? 'modal' : 'pip');

      // Tab became hidden - try to keep playback going
      if (isModal) {
        // Switch modal to PiP for better background playback
        videoPlayer.switchToPiP();
        autoSwitchedToPiP = true;
        console.log('[Background] Auto-switched to PiP');
      }
      // If already in PiP, video should continue playing
    } else {
      console.log('[Background] Tab visible, autoSwitched:', autoSwitchedToPiP);

      // Tab became visible again
      if (autoSwitchedToPiP && isPiP) {
        // Switch back to modal if we auto-switched
        videoPlayer.switchToModal();
        autoSwitchedToPiP = false;
        console.log('[Background] Auto-switched back to modal');
      }
    }
  }

  // Reset auto-switch flag when player closes
  $effect(() => {
    if (!isPlaying) {
      autoSwitchedToPiP = false;
    }
  });

  // Attach visibility listener
  $effect(() => {
    if (typeof document === 'undefined') return;

    document.addEventListener('visibilitychange', handleVisibilityChange);
    return () => document.removeEventListener('visibilitychange', handleVisibilityChange);
  });
</script>

<!-- This component has no UI - it just handles background playback logic -->
