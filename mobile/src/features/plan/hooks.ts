import { useQuery } from '@tanstack/react-query';
import { endpoints } from '@/api/endpoints';
import { keys } from '@/api/keys';
import { cache } from '@/api/query';
import { mapPlan, type PlanRequestDto } from './model';

export function usePlan(draft: PlanRequestDto | null) {
  return useQuery({
    queryKey: keys.plan(draft), enabled: draft !== null, staleTime: cache.draft,
    queryFn: ({ signal }) => endpoints.plan(draft!, signal), select: mapPlan,
  });
}
