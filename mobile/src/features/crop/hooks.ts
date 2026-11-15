import { useInfiniteQuery, useQuery } from '@tanstack/react-query';
import { endpoints } from '@/api/endpoints';
import { keys } from '@/api/keys';
import { mapCategory, mapCropPage } from './model';

export function useCategories(country: string) {
  return useQuery({
    queryKey: keys.categories(country), enabled: !!country,
    queryFn: ({ signal }) => endpoints.categories(country, signal), select: (dto) => dto.map(mapCategory),
  });
}

export function useCrops(country: string, search: string, category: string) {
  return useInfiniteQuery({
    queryKey: keys.crops(country, search, category), enabled: !!country,
    initialPageParam: undefined as string | undefined,
    queryFn: ({ pageParam, signal }) => endpoints.crops(country, search, category, pageParam, signal),
    getNextPageParam: (last) => last.nextCursor ?? undefined,
    select: (data) => ({ ...data, pages: data.pages.map(mapCropPage) }),
  });
}
