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
  return useQuery({
    queryKey: keys.monitor3d(request),
    enabled: request !== null,
    staleTime: cache.draft,
    placeholderData: keepPreviousData,
    queryFn: async ({ signal }) => monitorResponseSchema.parse(await endpoints.monitor3d(request!, signal)),
    select: mapMonitorResponse,
  });
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
