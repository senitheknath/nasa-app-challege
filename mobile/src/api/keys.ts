import type { FieldDto } from '@/features/area/model';
import type { PlanRequestDto } from '@/features/plan/model';

export type CropRegionFilter = {
  latitude?: number;
  longitude?: number;
  sowingDate?: string;
};

export const keys = {
  country: () => ['country'] as const,
  map: (country: string) => ['map', country] as const,
  places: (country: string, search: string) => ['places', country, search] as const,
  measure: (field: FieldDto | null) => ['measurement', field] as const,
  strategies: (country: string) => ['strategies', country] as const,
  categories: (country: string, region?: CropRegionFilter) =>
    region ? (['categories', country, region] as const) : (['categories', country] as const),
  crops: (country: string, search: string, category: string, region?: CropRegionFilter) =>
    region ? (['crops', country, search, category, region] as const) : (['crops', country, search, category] as const),
  plan: (draft: PlanRequestDto | null) => ['plan', draft] as const,
  monitor3d: (request: unknown, stage?: 'fast' | 'full') =>
    stage ? (['monitor3d', stage, request] as const) : (['monitor3d', request] as const),
  satellite: (context: unknown) => ['satellite', context] as const,
  climate: (context: unknown) => ['climate', context] as const,
  authMe: () => ['auth', 'me'] as const,
  farms: () => ['farms'] as const,
  crescoStatus: (farmId?: string | number | null) => ['cresco', 'status', farmId ?? 'none'] as const,
};
