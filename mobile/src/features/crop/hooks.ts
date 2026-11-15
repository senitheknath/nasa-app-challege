import { useInfiniteQuery, useQuery } from '@tanstack/react-query';
import { endpoints } from '@/api/endpoints';
import { keys, type CropRegionFilter } from '@/api/keys';
import { mapCategory, mapCropPage } from './model';

export function useCategories(country: string, region?: CropRegionFilter) {
  return useQuery({
    queryKey: keys.categories(country, region),
    enabled: !!country,
    queryFn: ({ signal }) => (region ? endpoints.categories(country, signal, region) : endpoints.categories(country, signal)),
    select: (dto) => dto.map(mapCategory),
  });
}

export function useCrops(country: string, search: string, category: string, region?: CropRegionFilter) {
  return useInfiniteQuery({
    queryKey: keys.crops(country, search, category, region),
    enabled: !!country,
    initialPageParam: undefined as string | undefined,
    queryFn: ({ pageParam, signal }) =>
      region
        ? endpoints.crops(country, search, category, pageParam, signal, region)
        : endpoints.crops(country, search, category, pageParam, signal),
    getNextPageParam: (last) => last.nextCursor ?? undefined,
    select: (data) => ({ ...data, pages: data.pages.map(mapCropPage) }),
  });
}
