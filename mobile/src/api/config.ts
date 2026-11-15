import * as SecureStore from 'expo-secure-store';
import { Platform } from 'react-native';

export const useMocks = false;

export const defaultBaseUrl = (process.env.EXPO_PUBLIC_API_BASE_URL?.trim() || 'http://localhost:8000').replace(/\/+$/, '');
export let baseUrl = defaultBaseUrl;

const SERVER_KEY = 'cresco.server-url';
let hydrated = false;
let webOverride: string | null = null;

export function normalizeServerAddress(raw: string): string {
  const trimmed = raw.trim().replace(/\/+$/, '');
  if (!trimmed) return '';
  if (/^https?:\/\//i.test(trimmed)) return trimmed;
  return `http://${trimmed}`;
}

function readStoredWeb(): string | null {
  try {
    if (typeof globalThis !== 'undefined' && 'localStorage' in globalThis && globalThis.localStorage) {
      return globalThis.localStorage.getItem(SERVER_KEY);
    }
  } catch {
    // Fallback when localStorage is unavailable (SSR/Jest)
  }
  return webOverride;
}

function writeStoredWeb(value: string | null) {
  webOverride = value;
  try {
    if (typeof globalThis !== 'undefined' && 'localStorage' in globalThis && globalThis.localStorage) {
      if (value === null) globalThis.localStorage.removeItem(SERVER_KEY);
      else globalThis.localStorage.setItem(SERVER_KEY, value);
    }
  } catch {
    // Fallback when localStorage is unavailable (SSR/Jest)
  }
}

export const serverStore = {
  async get(): Promise<string> {
    if (!hydrated) {
      try {
        const stored = Platform.OS === 'web'
          ? readStoredWeb()
          : await SecureStore.getItemAsync(SERVER_KEY);
        const normalized = stored ? normalizeServerAddress(stored) : '';
        baseUrl = normalized && /^https?:\/\/.+/i.test(normalized) ? normalized : defaultBaseUrl;
      } catch {
        baseUrl = defaultBaseUrl;
      }
      hydrated = true;
    }
    return baseUrl;
  },

  async set(raw: string): Promise<string> {
    const normalized = normalizeServerAddress(raw);
    if (!normalized || !/^https?:\/\/[^/\s]+/i.test(normalized)) {
      throw new Error('Enter a valid IP:port or URL (e.g. 10.53.197.13:8000)');
    }
    if (Platform.OS === 'web') {
      writeStoredWeb(normalized);
    } else {
      await SecureStore.setItemAsync(SERVER_KEY, normalized);
    }
    baseUrl = normalized;
    hydrated = true;
    return baseUrl;
  },

  async reset(): Promise<string> {
    if (Platform.OS === 'web') {
      writeStoredWeb(null);
    } else {
      await SecureStore.deleteItemAsync(SERVER_KEY);
    }
    baseUrl = defaultBaseUrl;
    hydrated = true;
    return baseUrl;
  },
};
