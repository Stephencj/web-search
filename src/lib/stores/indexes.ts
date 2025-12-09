/**
 * Svelte store for indexes state management.
 */

import { writable, derived } from 'svelte/store';
import { api, type Index } from '$lib/api/client';

// State
export const indexes = writable<Index[]>([]);
export const loading = writable(false);
export const error = writable<string | null>(null);

// Derived
export const activeIndexes = derived(indexes, ($indexes) =>
  $indexes.filter((idx) => idx.is_active)
);

export const indexCount = derived(indexes, ($indexes) => $indexes.length);

// Actions
export async function loadIndexes(): Promise<void> {
  loading.set(true);
  error.set(null);

  try {
    const response = await api.listIndexes();
    indexes.set(response.items);
  } catch (e) {
    error.set(e instanceof Error ? e.message : 'Failed to load indexes');
  } finally {
    loading.set(false);
  }
}

export async function createIndex(
  name: string,
  description?: string
): Promise<Index | null> {
  try {
    const newIndex = await api.createIndex({ name, description });
    indexes.update((list) => [...list, newIndex]);
    return newIndex;
  } catch (e) {
    error.set(e instanceof Error ? e.message : 'Failed to create index');
    return null;
  }
}

export async function deleteIndex(id: number): Promise<boolean> {
  try {
    await api.deleteIndex(id);
    indexes.update((list) => list.filter((idx) => idx.id !== id));
    return true;
  } catch (e) {
    error.set(e instanceof Error ? e.message : 'Failed to delete index');
    return false;
  }
}
