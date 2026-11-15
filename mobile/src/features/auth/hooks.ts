import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query';
import { endpoints } from '@/api/endpoints';
import { keys } from '@/api/keys';
import { tokenStore, userStore, type AuthUser } from '@/api/session';
import { usePlanner, type GeoPoint } from '@/state/usePlanner';

export function useAuthMe() {
  return useQuery<AuthUser | null>({
    queryKey: keys.authMe(),
    queryFn: async ({ signal }) => {
      const token = await tokenStore.get();
      if (!token) return null;
      try {
        const res = await endpoints.authMe(signal);
        await userStore.set(res.user);
        return res.user;
      } catch {
        return userStore.get();
      }
    },
    staleTime: 60_000,
  });
}

export function useAuthSubmit(mode: 'login' | 'register') {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async (input: { email: string; password: string; display_name?: string }) => {
      const res = mode === 'login'
        ? await endpoints.authLogin({ email: input.email.trim(), password: input.password })
        : await endpoints.authRegister({
            email: input.email.trim(),
            password: input.password,
            display_name: input.display_name?.trim() || undefined,
          });
      await tokenStore.set(res.token);
      await userStore.set(res.user);
      return res.user;
    },
    onSuccess: (user) => {
      queryClient.setQueryData(keys.authMe(), user);
      queryClient.invalidateQueries({ queryKey: keys.farms() });
    },
  });
}

export function useSignOut() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: async () => {
      await tokenStore.clear();
      await userStore.clear();
    },
    onSuccess: () => {
      queryClient.setQueryData(keys.authMe(), null);
      queryClient.setQueryData(keys.farms(), { farms: [] });
      usePlanner.getState().setSavedFarmMeta(null, '');
    },
  });
}

export function useSavedFarms(enabled: boolean) {
  return useQuery({
    queryKey: keys.farms(),
    queryFn: ({ signal }) => endpoints.farmsList(signal),
    enabled,
  });
}

export function useSaveFarm() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (body: {
      id?: number | null;
      name: string;
      country: string;
      latitude: number;
      longitude: number;
      area_ha?: number | null;
      boundary?: GeoPoint[];
      irrigation?: string;
      crop_id?: string | null;
      start_date?: string;
    }) => endpoints.farmSave(body),
    onSuccess: (res) => {
      usePlanner.getState().setSavedFarmMeta(res.farm.id, res.farm.name);
      queryClient.invalidateQueries({ queryKey: keys.farms() });
    },
  });
}

export function useDeleteFarm() {
  const queryClient = useQueryClient();
  return useMutation({
    mutationFn: (farmId: number) => endpoints.farmDelete(farmId),
    onSuccess: (_res, farmId) => {
      if (usePlanner.getState().farmId === farmId) {
        usePlanner.getState().setSavedFarmMeta(null, '');
      }
      queryClient.invalidateQueries({ queryKey: keys.farms() });
    },
  });
}
