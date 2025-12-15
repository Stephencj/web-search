<script lang="ts">
  import { hiddenChannelsStore } from '$lib/stores/hiddenChannels.svelte';

  interface Props {
    platform: string;
    channelId: string;
    channelName: string;
    channelAvatarUrl?: string | null;
    onhidden?: () => void;
  }

  let {
    platform,
    channelId,
    channelName,
    channelAvatarUrl = null,
    onhidden,
  }: Props = $props();

  let hiding = $state(false);

  async function handleHide(e: MouseEvent | TouchEvent) {
    e.preventDefault();
    e.stopPropagation();

    if (hiding) return;
    hiding = true;

    try {
      const success = await hiddenChannelsStore.hide({
        platform,
        channel_id: channelId,
        channel_name: channelName,
        channel_avatar_url: channelAvatarUrl,
      });

      if (success) {
        onhidden?.();
      }
    } finally {
      hiding = false;
    }
  }
</script>

<button
  type="button"
  class="hide-btn"
  onclick={handleHide}
  title="Hide this channel"
  aria-label="Hide this channel from results"
  disabled={hiding}
>
  <svg viewBox="0 0 24 24" fill="currentColor" width="16" height="16">
    <!-- Eye with slash icon -->
    <path d="M12 7c2.76 0 5 2.24 5 5 0 .65-.13 1.26-.36 1.83l2.92 2.92c1.51-1.26 2.7-2.89 3.43-4.75-1.73-4.39-6-7.5-11-7.5-1.4 0-2.74.25-3.98.7l2.16 2.16C10.74 7.13 11.35 7 12 7zM2 4.27l2.28 2.28.46.46C3.08 8.3 1.78 10.02 1 12c1.73 4.39 6 7.5 11 7.5 1.55 0 3.03-.3 4.38-.84l.42.42L19.73 22 21 20.73 3.27 3 2 4.27zM7.53 9.8l1.55 1.55c-.05.21-.08.43-.08.65 0 1.66 1.34 3 3 3 .22 0 .44-.03.65-.08l1.55 1.55c-.67.33-1.41.53-2.2.53-2.76 0-5-2.24-5-5 0-.79.2-1.53.53-2.2zm4.31-.78l3.15 3.15.02-.16c0-1.66-1.34-3-3-3l-.17.01z"/>
  </svg>
</button>

<style>
  .hide-btn {
    position: absolute;
    top: 6px;
    left: 6px;
    width: 32px;
    height: 32px;
    border-radius: 50%;
    background: rgba(0, 0, 0, 0.6);
    border: none;
    color: white;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    opacity: 0;
    transition: opacity 0.2s, background 0.2s, transform 0.2s;
    z-index: 10;
    touch-action: manipulation;
    -webkit-tap-highlight-color: transparent;
  }

  .hide-btn:hover {
    background: #ef4444;
    transform: scale(1.1);
  }

  .hide-btn:active {
    transform: scale(0.95);
  }

  .hide-btn:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  /* Show on hover for parent (desktop) */
  :global(.video-card:hover) .hide-btn,
  :global(.channel-card:hover) .hide-btn,
  :global(.result-card:hover) .hide-btn {
    opacity: 1;
  }

  /* Always show on mobile */
  @media (max-width: 768px) {
    .hide-btn {
      opacity: 1;
      width: 28px;
      height: 28px;
    }

    .hide-btn svg {
      width: 14px;
      height: 14px;
    }
  }
</style>
