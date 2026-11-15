import { useQuery } from '@tanstack/react-query';
import { endpoints } from '@/api/endpoints';
import { keys } from '@/api/keys';
import { mapStrategy } from './model';

export function useStrategies(country: string) {
  return useQuery({
    queryKey: keys.strategies(country), enabled: !!country,
    queryFn: ({ signal }) => endpoints.strategies(country, signal), select: (dto) => dto.map(mapStrategy),
  });
}
