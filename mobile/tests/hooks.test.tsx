import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { act, renderHook, waitFor } from '@testing-library/react-native';
import type { ReactNode } from 'react';
import { endpoints } from '@/api/endpoints';
import { keys } from '@/api/keys';
import { ApiError } from '@/api/errors';
import { useCrops } from '@/features/crop/hooks';
import { usePlan } from '@/features/plan/hooks';
import { useStrategies } from '@/features/strategy/hooks';
import { getSelectedStrategy } from '@/features/strategy/model';
import { crops, strategies } from '@/mocks/catalog';
import { buildMockPlan } from '@/mocks/agronomy';
import type { PlanRequestDto } from '@/features/plan/model';

jest.mock('expo-secure-store', () => ({}));
jest.mock('@/api/endpoints', () => ({ endpoints: { crops: jest.fn(), plan: jest.fn(), strategies: jest.fn() } }));

const mockCrops = jest.mocked(endpoints.crops);
const mockPlan = jest.mocked(endpoints.plan);

function setup() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: Infinity } } });
  function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
  }
  return { client, wrapper: Wrapper };
}

beforeEach(() => jest.resetAllMocks());

test('paginates by cursor and keeps filtered queries separate', async () => {
  mockCrops.mockResolvedValueOnce({ items: [crops[0]], nextCursor: 'next' })
    .mockResolvedValueOnce({ items: [crops[1]], nextCursor: null })
    .mockResolvedValueOnce({ items: [], nextCursor: null });
  const { client, wrapper } = setup();
  const { result, rerender } = await renderHook(({ search }: { search: string }) => useCrops('LK', search, 'cereals'), { wrapper, initialProps: { search: '' } });

  await waitFor(() => expect(result.current.data?.pages[0].items[0].name).toBe('Paddy Rice'));
  await act(async () => { await result.current.fetchNextPage(); });
  expect(mockCrops).toHaveBeenNthCalledWith(2, 'LK', '', 'cereals', 'next', expect.anything());
  await waitFor(() => expect(result.current.hasNextPage).toBe(false));

  await rerender({ search: 'missing' });
  await waitFor(() => expect(result.current.data?.pages[0].items).toEqual([]));
  expect(client.getQueryData(keys.crops('LK', '', 'cereals'))).toBeDefined();
});

test('ignores a retired Rotation cycle option and falls back to Current crop', async () => {
  jest.mocked(endpoints.strategies).mockResolvedValueOnce([
    ...strategies,
    { id: 'rotation', tag: 'Rotation', title: 'Rotation cycle', description: 'Maha and Yala seasons', requiresCrop: true },
  ]);
  const { wrapper } = setup();
  const { result } = await renderHook(() => useStrategies('LK'), { wrapper });
  await waitFor(() => expect(result.current.data?.map((strategy) => strategy.id)).toEqual(['fallow', 'standing']));
  expect(getSelectedStrategy(result.current.data, 'rotation', 'rotation')?.id).toBe('standing');
  expect(getSelectedStrategy(result.current.data, 'fallow', 'standing')?.requiresCrop).toBe(false);
});

test('waits for a valid draft and refetches a failed plan', async () => {
  const draft: PlanRequestDto = {
    countryId: 'LK', strategyId: 'standing', cropId: 'rice', sowingDate: '2026-11-15',
    points: [{ x: 10, y: 10 }, { x: 60, y: 10 }, { x: 60, y: 70 }],
  };
  mockPlan.mockRejectedValueOnce(new ApiError('http', 503)).mockResolvedValueOnce(buildMockPlan(draft));
  const { wrapper } = setup();
  const { result, rerender } = await renderHook(({ request }: { request: PlanRequestDto | null }) => usePlan(request),
    { wrapper, initialProps: { request: null } });
  expect(mockPlan).not.toHaveBeenCalled();

  await rerender({ request: draft });
  await waitFor(() => expect(result.current.isError).toBe(true));
  await act(async () => { await result.current.refetch(); });
  await waitFor(() => expect(result.current.data?.timeline).toHaveLength(4));
  expect(result.current.data?.first.crop.name).toBe('Paddy Rice');
});
