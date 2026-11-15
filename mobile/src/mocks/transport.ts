import type { Request } from '@/api/client';
import { ApiError } from '@/api/errors';
import { fieldSchema } from '@/features/area/model';
import { planRequestSchema } from '@/features/plan/model';
import { buildMockPlan, measureField, seasonOf } from './agronomy';
import { aerialUrl, categories, countries, crops, places, strategies } from './catalog';

function latency(ms: number, signal?: AbortSignal) {
  return new Promise<void>((resolve, reject) => {
    if (signal?.aborted) {
      reject(signal.reason);
      return;
    }
    const abort = () => {
      clearTimeout(timer);
      reject(signal?.reason);
    };
    const timer = setTimeout(() => {
      signal?.removeEventListener('abort', abort);
      resolve();
    }, ms);
    signal?.addEventListener('abort', abort, { once: true });
  });
}

function matches(value: string, query: unknown) {
  return value.toLocaleLowerCase().includes(String(query ?? '').toLocaleLowerCase());
}

export async function mockRequest(request: Request): Promise<unknown> {
  const { path, query, body, signal, method = 'GET' } = request;
  await latency(path === '/v1/plans/preview' ? 800 : 280, signal);

  const failure = process.env.EXPO_PUBLIC_MOCK_ERRORS;
  if (failure === 'always' || (failure !== 'off' && Math.random() < .06)) throw new ApiError('http', 503, 'MOCK_UNAVAILABLE');

  if (method === 'POST') {
    if (path === '/v1/fields/measure') {
      const field = fieldSchema.safeParse(body);
      if (!field.success) throw new ApiError('http', 422, 'INVALID_FIELD');
      return measureField(field.data);
    }
    if (path === '/v1/plans/preview') {
      const draft = planRequestSchema.safeParse(body);
      if (!draft.success) throw new ApiError('http', 422, 'INVALID_PLAN');
      return buildMockPlan(draft.data);
    }
    throw new ApiError('http', 404, 'NOT_FOUND');
  }

  switch (path) {
    case '/v1/countries':
      return {
        defaultCountryId: 'LK', currentSeason: seasonOf(new Date()), cropCount: crops.length, seasonCount: 2,
        defaultStrategyId: 'standing', defaultCropId: 'rice', countries,
      };
    case '/v1/map':
      return query?.country === 'LK' ? { imageUrl: aerialUrl } : null;
    case '/v1/places':
      return query?.country === 'LK' ? places.filter((place) => matches(place.name, query.q)) : [];
    case '/v1/strategies':
      return query?.country === 'LK' ? strategies : [];
    case '/v1/crop-categories':
      return query?.country === 'LK' ? categories : [];
    case '/v1/crops': {
      const filtered = query?.country === 'LK'
        ? crops.filter((crop) => (!query.category || crop.category.id === query.category) && matches(crop.name, query.q)) : [];
      const from = Math.max(0, Number(query?.cursor) || 0);
      const end = from + 6;
      return { items: filtered.slice(from, end), nextCursor: end < filtered.length ? String(end) : null };
    }
    default:
      throw new ApiError('http', 404, 'NOT_FOUND');
  }
}
