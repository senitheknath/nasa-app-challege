import { useQuery } from '@tanstack/react-query';
import { endpoints } from '@/api/endpoints';
import { keys } from '@/api/keys';
import { cache } from '@/api/query';
import { useMocks } from '@/api/config';
import { pictures } from '@/theme/images';
import { mapFieldMap, mapMeasurement, mapPlace, type FieldDto } from './model';

export function useFieldMap(country: string) {
  return useQuery({
    queryKey: keys.map(country), enabled: !!country, staleTime: cache.map,
    queryFn: ({ signal }) => endpoints.map(country, signal),
    select: (dto) => dto && useMocks ? { image: pictures.aerial } : mapFieldMap(dto),
  });
}

export function usePlaces(country: string, search: string, enabled: boolean) {
  return useQuery({
    queryKey: keys.places(country, search), enabled: !!country && !!search && enabled, staleTime: cache.suggestions,
    queryFn: ({ signal }) => endpoints.places(country, search, signal), select: (dto) => dto.map(mapPlace),
  });
}

export function useMeasurement(field: FieldDto | null) {
  return useQuery({
    queryKey: keys.measure(field), enabled: field !== null, staleTime: cache.draft,
    queryFn: ({ signal }) => endpoints.measure(field!, signal), select: mapMeasurement,
  });
}
