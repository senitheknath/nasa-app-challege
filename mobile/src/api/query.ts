import NetInfo, { useNetInfo } from '@react-native-community/netinfo';
import { focusManager, onlineManager, QueryClient } from '@tanstack/react-query';
import { AppState, Platform } from 'react-native';
import type { LoadState } from '@/components/feedback';
import { shouldRetry } from './errors';

export const cache = { catalog: 300_000, map: 600_000, suggestions: 60_000, draft: 120_000 } as const;

export function createQueryClient() {
  return new QueryClient({ defaultOptions: { queries: { retry: shouldRetry, staleTime: cache.catalog } } });
}

export function connectQueryLifecycle() {
  const network = NetInfo.addEventListener((state) => onlineManager.setOnline(state.isConnected !== false && state.isInternetReachable !== false));
  const app = Platform.OS !== 'web' ? AppState.addEventListener('change', (state) => focusManager.setFocused(state === 'active')) : null;
  return () => {
    network();
    app?.remove();
  };
}

export function useOffline() {
  const { isConnected, isInternetReachable } = useNetInfo();
  return isConnected === false || isInternetReachable === false;
}

export function viewState(
  query: { isPending: boolean; isError: boolean; isPaused: boolean },
  offline: boolean,
  hasData: boolean,
): LoadState {
  if (offline || query.isPaused) return 'offline';
  if (query.isError && !hasData) return 'error';
  if (query.isPending) return 'loading';
  return hasData ? 'ready' : 'empty';
}
