import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { endpoints } from '@/api/endpoints';
import { keys } from '@/api/keys';
import {
  CRESCO_DEFAULT_MODEL,
  CrescoApiError,
  type CrescoInlineFarm,
  type CrescoStatusResponse,
} from './model';
import { clearCrescoSessionToken, setCrescoSessionToken } from './session';

export function useCrescoStatus(farmId: string | number | null) {
  return useQuery({
    queryKey: keys.crescoStatus(farmId),
    queryFn: ({ signal }) => endpoints.crescoStatus(farmId, signal),
    staleTime: 30_000,
    retry: (attempt, error) => {
      if (attempt >= 1) return false;
      return error instanceof CrescoApiError && error.code === 'network';
    },
  });
}

export function useCrescoConnect(farmId: string | number | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (apiKey: string) =>
      endpoints.crescoConnect({ api_key: apiKey, farm_id: farmId }),
    onSuccess: (data) => {
      setCrescoSessionToken(data.session_token);
      queryClient.setQueryData<CrescoStatusResponse>(keys.crescoStatus(farmId), (prev) => ({
        connected: true,
        model: data.model || CRESCO_DEFAULT_MODEL,
        expires_at: data.expires_at ?? null,
        ttl_seconds: data.ttl_seconds,
        history_count: prev?.history_count ?? 0,
        history: prev?.history ?? [],
      }));
      void queryClient.invalidateQueries({ queryKey: ['cresco', 'status'] });
    },
  });
}

export function useCrescoChat(farmId: string | number | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (payload: {
      message: string;
      farm?: CrescoInlineFarm;
      season?: string;
      area_id?: string;
      language?: 'en' | 'si' | 'ta' | 'auto';
      clear_history?: boolean;
    }) =>
      endpoints.crescoChat({
        message: payload.message,
        farm_id: farmId,
        farm: payload.farm,
        season: payload.season,
        area_id: payload.area_id,
        language: payload.language,
        clear_history: payload.clear_history,
      }),
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: keys.crescoStatus(farmId) });
    },
  });
}

export function useCrescoClear(farmId: string | number | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => endpoints.crescoClear(farmId),
    onSuccess: () => {
      queryClient.setQueryData<CrescoStatusResponse>(keys.crescoStatus(farmId), (prev) =>
        prev
          ? { ...prev, history_count: 0, history: [] }
          : { connected: true, model: CRESCO_DEFAULT_MODEL, history_count: 0, history: [] },
      );
    },
  });
}

export function useCrescoDisconnect(farmId: string | number | null) {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: () => endpoints.crescoDisconnect(),
    onSettled: () => {
      clearCrescoSessionToken();
      queryClient.setQueryData<CrescoStatusResponse>(keys.crescoStatus(farmId), {
        connected: false,
        model: CRESCO_DEFAULT_MODEL,
        expires_at: null,
        history_count: 0,
        history: [],
      });
      void queryClient.invalidateQueries({ queryKey: ['cresco', 'status'] });
    },
  });
}
