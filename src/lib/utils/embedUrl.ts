/**
 * Platform-specific embed URL builder utility
 * Generates embed URLs for various video platforms
 */

export type VideoPlatform = 'youtube' | 'rumble' | 'odysee' | 'bitchute' | 'dailymotion';

export interface EmbedConfig {
  platform: string;
  supportsEmbed: boolean;
  embedUrl: string | null;
  fallbackReason?: string;
}

/**
 * Platform display names and colors for UI
 */
export const platformInfo: Record<string, { name: string; color: string }> = {
  youtube: { name: 'YouTube', color: '#FF0000' },
  rumble: { name: 'Rumble', color: '#85C742' },
  odysee: { name: 'Odysee', color: '#e50054' },
  bitchute: { name: 'BitChute', color: '#ef4a23' },
  dailymotion: { name: 'Dailymotion', color: '#0066DC' },
};

/**
 * Parse Odysee URL to extract claim name and claim ID
 * Odysee URLs format: https://odysee.com/@channel:id/video-name:claim_id
 * or: https://odysee.com/video-name:claim_id
 */
export function parseOdyseeUrl(url: string): { claimName: string; claimId: string } | null {
  try {
    const urlObj = new URL(url);
    const pathname = urlObj.pathname;

    // Try to match /@channel/video:id or /video:id pattern
    const parts = pathname.split('/').filter(Boolean);

    // Get the last part which should be video-name:claim_id
    const lastPart = parts[parts.length - 1];
    if (!lastPart) return null;

    // Extract claim_id from the last part (after the colon)
    const colonIndex = lastPart.lastIndexOf(':');
    if (colonIndex === -1) return null;

    const claimName = lastPart.substring(0, colonIndex);
    const claimId = lastPart.substring(colonIndex + 1);

    if (!claimName || !claimId) return null;

    return { claimName, claimId };
  } catch {
    return null;
  }
}

/**
 * Generate embed URL for a given platform and video
 */
export function getEmbedUrl(platform: string, videoId: string, videoUrl: string): string | null {
  switch (platform.toLowerCase()) {
    case 'youtube':
      // YouTube embed: https://www.youtube.com/embed/{video_id}
      if (!videoId) return null;
      return `https://www.youtube.com/embed/${videoId}?autoplay=1&rel=0`;

    case 'rumble':
      // Rumble embed: https://rumble.com/embed/{video_id}/
      // Video ID is typically like "v4abcde" extracted from URL
      if (!videoId) return null;
      return `https://rumble.com/embed/${videoId}/`;

    case 'odysee':
      // Odysee embed: https://odysee.com/$/embed/{claim_name}/{claim_id}
      const odyseeInfo = parseOdyseeUrl(videoUrl);
      if (!odyseeInfo) return null;
      return `https://odysee.com/$/embed/${odyseeInfo.claimName}/${odyseeInfo.claimId}`;

    case 'bitchute':
      // BitChute embed: https://www.bitchute.com/embed/{video_id}/
      if (!videoId) return null;
      return `https://www.bitchute.com/embed/${videoId}/`;

    case 'dailymotion':
      // Dailymotion embed: https://www.dailymotion.com/embed/video/{video_id}
      if (!videoId) return null;
      return `https://www.dailymotion.com/embed/video/${videoId}?autoplay=1`;

    default:
      return null;
  }
}

/**
 * Check if a platform supports embedding
 */
export function canEmbed(platform: string): boolean {
  const supportedPlatforms = ['youtube', 'rumble', 'odysee', 'bitchute', 'dailymotion'];
  return supportedPlatforms.includes(platform.toLowerCase());
}

/**
 * Build complete embed configuration for a video
 */
export function buildEmbedConfig(platform: string, videoId: string, videoUrl: string): EmbedConfig {
  const normalizedPlatform = platform.toLowerCase();

  if (!canEmbed(normalizedPlatform)) {
    return {
      platform: normalizedPlatform,
      supportsEmbed: false,
      embedUrl: null,
      fallbackReason: `${platformInfo[normalizedPlatform]?.name || platform} embedding is not supported`,
    };
  }

  const embedUrl = getEmbedUrl(normalizedPlatform, videoId, videoUrl);

  if (!embedUrl) {
    return {
      platform: normalizedPlatform,
      supportsEmbed: false,
      embedUrl: null,
      fallbackReason: 'Could not generate embed URL for this video',
    };
  }

  return {
    platform: normalizedPlatform,
    supportsEmbed: true,
    embedUrl,
  };
}

/**
 * Get platform display name
 */
export function getPlatformName(platform: string): string {
  return platformInfo[platform.toLowerCase()]?.name || platform;
}

/**
 * Get platform color
 */
export function getPlatformColor(platform: string): string {
  return platformInfo[platform.toLowerCase()]?.color || '#666666';
}
