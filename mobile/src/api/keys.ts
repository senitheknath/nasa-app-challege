import type { FieldDto } from '@/features/area/model';
import type { PlanRequestDto } from '@/features/plan/model';

export const keys = {
  country: () => ['country'] as const,
  map: (country: string) => ['map', country] as const,
  places: (country: string, search: string) => ['places', country, search] as const,
  measure: (field: FieldDto | null) => ['measurement', field] as const,
  strategies: (country: string) => ['strategies', country] as const,
  categories: (country: string) => ['categories', country] as const,
  crops: (country: string, search: string, category: string) => ['crops', country, search, category] as const,
  plan: (draft: PlanRequestDto | null) => ['plan', draft] as const,
};
