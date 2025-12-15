/// <reference types="@sveltejs/kit" />
/// <reference no-default-lib="true"/>
/// <reference lib="esnext" />
/// <reference lib="webworker" />

import { build, files, version } from '$service-worker';

const sw = self as unknown as ServiceWorkerGlobalScope;

// Create unique cache names
const CACHE_NAME = `websearch-cache-${version}`;
const ASSETS_CACHE = `websearch-assets-${version}`;
const API_CACHE = `websearch-api-${version}`;
const IMAGE_CACHE = `websearch-images-${version}`;

// Assets to cache immediately on install
const PRECACHE_ASSETS = [
  ...build, // the app itself
  ...files, // everything in static
];

// API endpoints that can be cached (with network-first strategy)
const CACHEABLE_API_PATTERNS = [
  /\/api\/feed(\?|$)/,
  /\/api\/subscriptions/,
  /\/api\/saved-videos/,
  /\/api\/collections/,
];

// Image hosts to cache
const IMAGE_HOSTS = [
  'i.ytimg.com',
  'img.youtube.com',
  'yt3.ggpht.com',
  'sp.rmbl.ws',
];

// Install event - precache assets
sw.addEventListener('install', (event) => {
  event.waitUntil(
    (async () => {
      const cache = await caches.open(CACHE_NAME);
      // Cache all build assets
      await cache.addAll(PRECACHE_ASSETS);
      // Activate immediately
      await sw.skipWaiting();
    })()
  );
});

// Activate event - clean up old caches
sw.addEventListener('activate', (event) => {
  event.waitUntil(
    (async () => {
      // Get all cache names
      const keys = await caches.keys();
      // Delete old caches
      await Promise.all(
        keys
          .filter((key) => key.startsWith('websearch-') && key !== CACHE_NAME && key !== ASSETS_CACHE && key !== API_CACHE && key !== IMAGE_CACHE)
          .map((key) => caches.delete(key))
      );
      // Take control of all clients
      await sw.clients.claim();
    })()
  );
});

// Fetch event - serve from cache with appropriate strategies
sw.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Skip non-GET requests
  if (request.method !== 'GET') return;

  // Skip chrome-extension and other protocols
  if (!url.protocol.startsWith('http')) return;

  // Strategy 1: Cache-first for static assets
  if (PRECACHE_ASSETS.includes(url.pathname)) {
    event.respondWith(cacheFirst(request, CACHE_NAME));
    return;
  }

  // Strategy 2: Cache-first for images from known hosts
  if (IMAGE_HOSTS.some(host => url.hostname.includes(host))) {
    event.respondWith(cacheFirst(request, IMAGE_CACHE, 60 * 60 * 24 * 7)); // 7 days
    return;
  }

  // Strategy 3: Network-first for API requests (with cache fallback)
  if (url.pathname.startsWith('/api/') && CACHEABLE_API_PATTERNS.some(pattern => pattern.test(url.pathname))) {
    event.respondWith(networkFirst(request, API_CACHE, 60 * 5)); // 5 minutes
    return;
  }

  // Strategy 4: Network-first for page navigations
  if (request.mode === 'navigate') {
    event.respondWith(networkFirst(request, CACHE_NAME));
    return;
  }

  // Default: Network only (for video streams, auth endpoints, etc.)
});

/**
 * Cache-first strategy
 * Returns cached response if available, otherwise fetches from network
 */
async function cacheFirst(request: Request, cacheName: string, maxAge?: number): Promise<Response> {
  const cache = await caches.open(cacheName);
  const cached = await cache.match(request);

  if (cached) {
    // Check if cache is still valid
    if (maxAge) {
      const dateHeader = cached.headers.get('sw-cached-at');
      if (dateHeader) {
        const cachedAt = parseInt(dateHeader, 10);
        if (Date.now() - cachedAt > maxAge * 1000) {
          // Cache expired, fetch new
          return fetchAndCache(request, cache, maxAge);
        }
      }
    }
    return cached;
  }

  return fetchAndCache(request, cache, maxAge);
}

/**
 * Network-first strategy
 * Tries network first, falls back to cache if offline
 */
async function networkFirst(request: Request, cacheName: string, maxAge?: number): Promise<Response> {
  const cache = await caches.open(cacheName);

  try {
    const response = await fetchAndCache(request, cache, maxAge);
    return response;
  } catch {
    // Network failed, try cache
    const cached = await cache.match(request);
    if (cached) {
      return cached;
    }
    // No cache available, return offline page or error
    return new Response('Offline', { status: 503, statusText: 'Service Unavailable' });
  }
}

/**
 * Fetch from network and cache the response
 */
async function fetchAndCache(request: Request, cache: Cache, maxAge?: number): Promise<Response> {
  const response = await fetch(request);

  // Only cache successful responses
  if (response.ok) {
    // Clone the response since we need to read it twice
    const responseToCache = response.clone();

    // Add timestamp header for cache expiration
    if (maxAge) {
      const headers = new Headers(responseToCache.headers);
      headers.set('sw-cached-at', Date.now().toString());
      const body = await responseToCache.blob();
      const cachedResponse = new Response(body, {
        status: responseToCache.status,
        statusText: responseToCache.statusText,
        headers,
      });
      cache.put(request, cachedResponse);
    } else {
      cache.put(request, responseToCache);
    }
  }

  return response;
}

// Listen for messages from the main app
sw.addEventListener('message', (event) => {
  if (event.data?.type === 'SKIP_WAITING') {
    sw.skipWaiting();
  }

  if (event.data?.type === 'CLEAR_CACHE') {
    caches.keys().then(keys => {
      keys.forEach(key => {
        if (key.startsWith('websearch-')) {
          caches.delete(key);
        }
      });
    });
  }
});
