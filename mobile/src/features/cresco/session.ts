import { onSessionExpired } from '@/api/session';

/**
 * In-memory only Cresco session token holder.
 * Never persisted to SecureStore, AsyncStorage, localStorage, or URLs.
 */
let crescoSessionToken: string | null = null;

export function getCrescoSessionToken(): string | null {
  return crescoSessionToken;
}

export function setCrescoSessionToken(token: string | null): void {
  crescoSessionToken = token && token.trim() ? token.trim() : null;
}

export function clearCrescoSessionToken(): void {
  crescoSessionToken = null;
}

onSessionExpired(() => {
  clearCrescoSessionToken();
});
