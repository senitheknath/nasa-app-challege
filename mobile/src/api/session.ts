import * as SecureStore from 'expo-secure-store';
import { Platform } from 'react-native';

const tokenKey = 'cresco.access-token';
let webToken: string | null = null;
let pendingWrite = Promise.resolve();
let expiryHandler: (() => void) | undefined;

async function readToken() {
  return Platform.OS === 'web' ? webToken : SecureStore.getItemAsync(tokenKey);
}

async function writeToken(token: string | null) {
  if (Platform.OS === 'web') {
    webToken = token;
  } else if (token) {
    await SecureStore.setItemAsync(tokenKey, token);
  } else {
    await SecureStore.deleteItemAsync(tokenKey);
  }
}

function serializeWrite(work: () => Promise<void>) {
  const operation = pendingWrite.then(work);
  pendingWrite = operation.catch(() => undefined);
  return operation;
}

export const tokenStore = {
  get: () => pendingWrite.then(readToken),
  set: (token: string) => serializeWrite(() => writeToken(token)),
  clear: () => serializeWrite(() => writeToken(null)),
};

export function onSessionExpired(handler: () => void) {
  expiryHandler = handler;
  return () => { if (expiryHandler === handler) expiryHandler = undefined; };
}

export function expireSession(rejectedToken: string | null) {
  return serializeWrite(async () => {
    if (await readToken() !== rejectedToken) return;
    try {
      await writeToken(null);
    } finally {
      expiryHandler?.();
    }
  });
}
