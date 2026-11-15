import { keepPreviousData, useQuery } from '@tanstack/react-query';
import { endpoints } from '@/api/endpoints';
import { keys } from '@/api/keys';
import { cache } from '@/api/query';
import {
  climateResponseSchema,
  mapClimateResponse,
  mapMonitorResponse,
  mapSatelliteResponse,
  monitorResponseSchema,
  satelliteResponseSchema,
  type MonitorRequestDto,
} from './model';

export type SatelliteContext = {
  country?: string;
  latitude: number;
  longitude: number;
  boundary?: unknown;
  area_ha?: number | null;
};

export type ClimateContext = {
  country?: string;
  latitude: number;
  longitude: number;
};

export function useMonitor3D(request: MonitorRequestDto | null) {
  const fastRequest = request ? { ...request, stage: 'fast' as const } : null;
  const fullRequest = request ? { ...request, stage: 'full' as const } : null;

  const fastQuery = useQuery({
    queryKey: keys.monitor3d(request, 'fast'),
    enabled: request !== null,
    staleTime: cache.draft,
    placeholderData: keepPreviousData,
    queryFn: async ({ signal }) => monitorResponseSchema.parse(await endpoints.monitor3d(fastRequest!, signal)),
    select: mapMonitorResponse,
  });

  const fullQuery = useQuery({
    queryKey: keys.monitor3d(request, 'full'),
    enabled: request !== null,
    staleTime: cache.draft,
    placeholderData: keepPreviousData,
    queryFn: async ({ signal }) => monitorResponseSchema.parse(await endpoints.monitor3d(fullRequest!, signal)),
    select: mapMonitorResponse,
  });

  const hasRealFull = fullQuery.data != null && !fullQuery.isPlaceholderData;
  const hasRealFast = fastQuery.data != null && !fastQuery.isPlaceholderData;
  const hasFull = fullQuery.data != null;
  const hasFast = fastQuery.data != null;
  const data = hasRealFull
    ? fullQuery.data
    : hasRealFast
      ? fastQuery.data
      : fullQuery.data ?? fastQuery.data;
  const isUpgradingFusion =
    !hasRealFull &&
    (hasRealFast || hasFast) &&
    (fullQuery.isPending || fullQuery.isFetching) &&
    !fullQuery.isError;
  const activeQuery = hasRealFull ? fullQuery : hasRealFast ? fastQuery : hasFull ? fullQuery : fastQuery;

  return {
    ...activeQuery,
    data,
    isPending: !hasFull && !hasFast && (fastQuery.isPending || fullQuery.isPending),
    isError: !hasFull && !hasFast && fullQuery.isError && fastQuery.isError,
    isPaused: !hasFull && !hasFast && fastQuery.isPaused && fullQuery.isPaused,
    isFetching: fastQuery.isFetching || fullQuery.isFetching,
    isUpgradingFusion,
    fastQuery,
    fullQuery,
    refetch: async () => {
      const [, fullResult] = await Promise.all([fastQuery.refetch(), fullQuery.refetch()]);
      return fullResult;
    },
  };
}

export function useSatelliteData(context: SatelliteContext | null) {
  return useQuery({
    queryKey: keys.satellite(context),
    enabled: context !== null,
    staleTime: cache.draft,
    queryFn: async ({ signal }) => satelliteResponseSchema.parse(await endpoints.satellite(context!, signal)),
    select: mapSatelliteResponse,
  });
}

export function useClimateData(context: ClimateContext | null) {
  return useQuery({
    queryKey: keys.climate(context),
    enabled: context !== null,
    staleTime: cache.draft,
    queryFn: async ({ signal }) => climateResponseSchema.parse(await endpoints.climate(context!, signal)),
    select: mapClimateResponse,
  });
}
