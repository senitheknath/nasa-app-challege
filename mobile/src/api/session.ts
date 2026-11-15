import * as SecureStore from 'expo-secure-store';
import { Platform } from 'react-native';

export type AuthUser = {
  id: number;
  email: string;
  display_name?: string | null;
};

const tokenKey = 'cresco.access-token';
const userKey = 'cresco.auth-user';

let webToken: string | null = null;
let webUser: string | null = null;
let pendingWrite = Promise.resolve();
let expiryHandler: (() => void) | undefined;

function readWebItem(key: string): string | null {
  try {
    if (typeof globalThis !== 'undefined' && 'localStorage' in globalThis && globalThis.localStorage) {
      return globalThis.localStorage.getItem(key);
    }
  } catch {
    // Fallback to in-memory store when localStorage is unavailable (SSR/Jest)
  }
  return key === tokenKey ? webToken : webUser;
}

function writeWebItem(key: string, value: string | null) {
  if (key === tokenKey) webToken = value;
  else webUser = value;
  try {
    if (typeof globalThis !== 'undefined' && 'localStorage' in globalThis && globalThis.localStorage) {
      if (value === null) globalThis.localStorage.removeItem(key);
      else globalThis.localStorage.setItem(key, value);
    }
  } catch {
    // Fallback to in-memory store when localStorage is unavailable (SSR/Jest)
  }
}

async function readItem(key: string): Promise<string | null> {
  if (Platform.OS === 'web') return readWebItem(key);
  return SecureStore.getItemAsync(key);
}

async function writeItem(key: string, value: string | null): Promise<void> {
  if (Platform.OS === 'web') {
    writeWebItem(key, value);
  } else if (value !== null) {
    await SecureStore.setItemAsync(key, value);
  } else {
    await SecureStore.deleteItemAsync(key);
  }
}

function serializeWrite(work: () => Promise<void>) {
  const operation = pendingWrite.then(work);
  pendingWrite = operation.catch(() => undefined);
  return operation;
}

export const tokenStore = {
  get: () => pendingWrite.then(() => readItem(tokenKey)),
  set: (token: string) => serializeWrite(() => writeItem(tokenKey, token)),
  clear: () => serializeWrite(() => writeItem(tokenKey, null)),
};

export const userStore = {
  get: async (): Promise<AuthUser | null> => {
    const raw = await pendingWrite.then(() => readItem(userKey));
    if (!raw) return null;
    try {
      const parsed = JSON.parse(raw) as AuthUser;
      if (parsed && typeof parsed.id === 'number' && typeof parsed.email === 'string') {
        return parsed;
      }
      return null;
    } catch {
      return null;
    }
  },
  set: (user: AuthUser) => serializeWrite(() => writeItem(userKey, JSON.stringify(user))),
  clear: () => serializeWrite(() => writeItem(userKey, null)),
};

export function onSessionExpired(handler: () => void) {
  expiryHandler = handler;
  return () => { if (expiryHandler === handler) expiryHandler = undefined; };
}

export function expireSession(rejectedToken: string | null) {
  return serializeWrite(async () => {
    if (await readItem(tokenKey) !== rejectedToken) return;
    try {
      await writeItem(tokenKey, null);
      await writeItem(userKey, null);
    } finally {
      expiryHandler?.();
    }
  });
}
