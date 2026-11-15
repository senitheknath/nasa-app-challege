import { measurementSchema, mapSchema, placesSchema, type FieldDto } from '@/features/area/model';
import { countryDataSchema } from '@/features/country/model';
import { categoriesSchema, cropPageSchema } from '@/features/crop/model';
import { planSchema, type PlanRequestDto } from '@/features/plan/model';
import { strategiesSchema } from '@/features/strategy/model';
import { requestJson } from './client';

export const endpoints = {
  countries: (signal: AbortSignal) => requestJson({ path: '/v1/countries', signal }, countryDataSchema),
  map: (country: string, signal: AbortSignal) => requestJson({ path: '/v1/map', query: { country }, signal }, mapSchema),
  places: (country: string, q: string, signal: AbortSignal) => requestJson({ path: '/v1/places', query: { country, q }, signal }, placesSchema),
  measure: (body: FieldDto, signal: AbortSignal) => requestJson({ method: 'POST', path: '/v1/fields/measure', body, signal }, measurementSchema),
  strategies: (country: string, signal: AbortSignal) => requestJson({ path: '/v1/strategies', query: { country }, signal }, strategiesSchema),
  categories: (country: string, signal: AbortSignal) => requestJson({ path: '/v1/crop-categories', query: { country }, signal }, categoriesSchema),
  crops: (country: string, q: string, category: string, cursor: string | undefined, signal: AbortSignal) =>
    requestJson({ path: '/v1/crops', query: { country, q: q || undefined, category: category || undefined, cursor }, signal }, cropPageSchema),
  plan: (body: PlanRequestDto, signal: AbortSignal) => requestJson({ method: 'POST', path: '/v1/plans/preview', body, signal }, planSchema),
};
