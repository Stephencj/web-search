/**
 * Svelte store for collections state management.
 */

import { writable, derived } from 'svelte/store';
import { api, type Collection, type CollectionWithItems, type CollectionItem, type CollectionItemCreate } from '$lib/api/client';
import { precacheVideoStream } from '$lib/stores/streamCache.svelte';

// State
export const collections = writable<Collection[]>([]);
export const currentCollection = writable<CollectionWithItems | null>(null);
export const loading = writable(false);
export const error = writable<string | null>(null);

// Derived
export const collectionCount = derived(collections, ($collections) => $collections.length);

export const favoritesCollection = derived(collections, ($collections) =>
  $collections.find((c) => c.name === 'Favorites')
);

// Actions
export async function loadCollections(): Promise<void> {
  loading.set(true);
  error.set(null);

  try {
    const response = await api.listCollections();
    collections.set(response.items);
  } catch (e) {
    error.set(e instanceof Error ? e.message : 'Failed to load collections');
  } finally {
    loading.set(false);
  }
}

export async function loadCollection(id: number): Promise<CollectionWithItems | null> {
  loading.set(true);
  error.set(null);

  try {
    const collection = await api.getCollection(id);
    currentCollection.set(collection);
    return collection;
  } catch (e) {
    error.set(e instanceof Error ? e.message : 'Failed to load collection');
    return null;
  } finally {
    loading.set(false);
  }
}

export async function createCollection(
  name: string,
  description?: string
): Promise<Collection | null> {
  try {
    const newCollection = await api.createCollection({ name, description });
    collections.update((list) => [...list, newCollection]);
    return newCollection;
  } catch (e) {
    error.set(e instanceof Error ? e.message : 'Failed to create collection');
    return null;
  }
}

export async function updateCollection(
  id: number,
  data: Partial<{ name: string; description: string; sort_order: number }>
): Promise<Collection | null> {
  try {
    const updated = await api.updateCollection(id, data);
    collections.update((list) =>
      list.map((c) => (c.id === id ? updated : c))
    );
    return updated;
  } catch (e) {
    error.set(e instanceof Error ? e.message : 'Failed to update collection');
    return null;
  }
}

export async function deleteCollection(id: number): Promise<boolean> {
  try {
    await api.deleteCollection(id);
    collections.update((list) => list.filter((c) => c.id !== id));
    return true;
  } catch (e) {
    error.set(e instanceof Error ? e.message : 'Failed to delete collection');
    return false;
  }
}

export async function addItemToCollection(
  collectionId: number,
  item: CollectionItemCreate
): Promise<CollectionItem | null> {
  try {
    const newItem = await api.addItemToCollection(collectionId, item);
    // Update collection item count in the list
    collections.update((list) =>
      list.map((c) =>
        c.id === collectionId ? { ...c, item_count: c.item_count + 1 } : c
      )
    );
    // Update current collection if it's the one we added to
    currentCollection.update((col) => {
      if (col && col.id === collectionId) {
        return {
          ...col,
          items: [...col.items, newItem],
          item_count: col.item_count + 1,
        };
      }
      return col;
    });

    // Pre-cache video stream in the background for instant playback
    // (skip podcasts - they use direct audio URLs from RSS feeds)
    if (item.item_type === 'video' && item.embed_type && item.video_id) {
      // Don't await - let it run in background
      precacheVideoStream(item.embed_type, item.video_id).catch(() => {});
    }

    return newItem;
  } catch (e) {
    error.set(e instanceof Error ? e.message : 'Failed to add item to collection');
    return null;
  }
}

export async function removeItemFromCollection(
  collectionId: number,
  itemId: number
): Promise<boolean> {
  try {
    await api.removeItemFromCollection(collectionId, itemId);
    // Update collection item count in the list
    collections.update((list) =>
      list.map((c) =>
        c.id === collectionId ? { ...c, item_count: Math.max(0, c.item_count - 1) } : c
      )
    );
    // Update current collection if it's the one we removed from
    currentCollection.update((col) => {
      if (col && col.id === collectionId) {
        return {
          ...col,
          items: col.items.filter((item) => item.id !== itemId),
          item_count: Math.max(0, col.item_count - 1),
        };
      }
      return col;
    });
    return true;
  } catch (e) {
    error.set(e instanceof Error ? e.message : 'Failed to remove item from collection');
    return false;
  }
}

export async function quickAddToFavorites(
  item: CollectionItemCreate
): Promise<CollectionItem | null> {
  try {
    const newItem = await api.quickAddToFavorites(item);
    // Reload collections to get the Favorites collection (may have been created)
    await loadCollections();
    return newItem;
  } catch (e) {
    error.set(e instanceof Error ? e.message : 'Failed to add to favorites');
    return null;
  }
}

export async function reorderItems(
  collectionId: number,
  itemIds: number[]
): Promise<boolean> {
  try {
    await api.reorderCollectionItems(collectionId, itemIds);
    // Update current collection's item order
    currentCollection.update((col) => {
      if (col && col.id === collectionId) {
        const itemMap = new Map(col.items.map((item) => [item.id, item]));
        const reorderedItems = itemIds
          .map((id, index) => {
            const item = itemMap.get(id);
            return item ? { ...item, sort_order: index } : null;
          })
          .filter((item): item is CollectionItem => item !== null);
        return { ...col, items: reorderedItems };
      }
      return col;
    });
    return true;
  } catch (e) {
    error.set(e instanceof Error ? e.message : 'Failed to reorder items');
    return false;
  }
}

export function clearError(): void {
  error.set(null);
}
