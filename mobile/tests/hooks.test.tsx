import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { act, renderHook, waitFor } from '@testing-library/react-native';
import type { ReactNode } from 'react';
import { endpoints } from '@/api/endpoints';
import { ApiError } from '@/api/errors';
import { keys } from '@/api/keys';
import { useCrops } from '@/features/crop/hooks';
import type { CropDto } from '@/features/crop/model';
import { usePlan } from '@/features/plan/hooks';
import type { PlanDto, PlanRequestDto } from '@/features/plan/model';
import { useStrategies } from '@/features/strategy/hooks';
import { getSelectedStrategy, type StrategyDto } from '@/features/strategy/model';

jest.mock('expo-secure-store', () => ({}));
jest.mock('@/api/endpoints', () => ({
  endpoints: {
    crops: jest.fn(),
    plan: jest.fn(),
    strategies: jest.fn(),
  },
}));

const mockCrops = jest.mocked(endpoints.crops);
const mockPlan = jest.mocked(endpoints.plan);
const mockStrategies = jest.mocked(endpoints.strategies);

const sampleCrops: CropDto[] = [
  { id: 'rice', name: 'Paddy Rice', category: { id: 'Cereals', label: 'Cereals' }, yieldTonnesPerHectare: 5.2, waterPercent: 85 },
  { id: 'mungbean', name: 'Mungbean', category: { id: 'Pulses', label: 'Pulses' }, yieldTonnesPerHectare: 1.4, waterPercent: 40 },
];

const sampleStrategies: StrategyDto[] = [
  { id: 'continuous_rainfed', tag: 'Rainfed', title: 'Continuous Rotation (Rainfed)', description: 'Season-free chaining', requiresCrop: true },
  { id: 'continuous_irrigated', tag: 'Irrigated', title: 'Continuous Rotation (Irrigated)', description: 'Irrigated chaining', requiresCrop: true },
  { id: 'standing_rainfed', tag: 'Standing · Rainfed', title: 'Standing Crop (Rainfed)', description: 'Active crop', requiresCrop: true },
  { id: 'fallow_rainfed', tag: 'Fallow', title: 'Bare / Fallow Field', description: 'Resting field', requiresCrop: false },
];

const samplePlanDto: NonNullable<PlanDto> = {
  hectares: 5.0,
  strategyTag: 'Rainfed',
  mode: 'continuous',
  crop: sampleCrops[0],
  timeline: [
    {
      id: 'rot-1-0',
      season: 'Slot 1',
      year: 2026,
      crop: sampleCrops[0],
      note: '2026-11-15 → 2027-03-15',
      sowingDate: '2026-11-15',
      harvestDate: '2027-03-15',
    },
    {
      id: 'rot-1-1',
      season: 'Slot 2',
      year: 2027,
      crop: sampleCrops[1],
      note: '2027-03-29 → 2027-06-02',
      sowingDate: '2027-03-29',
      harvestDate: '2027-06-02',
    },
  ],
  rotations: [
    {
      id: 'rice__mungbean',
      name: 'Paddy Rice → Mungbean',
      rank: 1,
      score: 86,
      rating: 'Optimal',
      timeline: {
        feasible: true,
        total_agronomic_score: 86,
        slots: [
          {
            crop_id: 'rice',
            crop_name: 'Paddy Rice',
            family: 'Poaceae',
            sowing_date: '2026-11-15',
            harvest_nominal_date: '2027-03-15',
          },
          {
            crop_id: 'mungbean',
            crop_name: 'Mungbean',
            family: 'Fabaceae',
            sowing_date: '2027-03-29',
            harvest_nominal_date: '2027-06-02',
          },
        ],
      },
    },
  ],
};

function setup() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: Infinity } } });
  function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
  }
  return { client, wrapper: Wrapper };
}

beforeEach(() => jest.resetAllMocks());

test('paginates by cursor and keeps filtered queries separate', async () => {
  mockCrops
    .mockResolvedValueOnce({ items: [sampleCrops[0]], nextCursor: '20' })
    .mockResolvedValueOnce({ items: [sampleCrops[1]], nextCursor: null })
    .mockResolvedValueOnce({ items: [], nextCursor: null });

  const { client, wrapper } = setup();
  const { result, rerender } = await renderHook(
    ({ search }: { search: string }) => useCrops('LK', search, 'Cereals'),
    { wrapper, initialProps: { search: '' } },
  );

  await waitFor(() => expect(result.current.data?.pages[0].items[0].name).toBe('Paddy Rice'));
  await act(async () => { await result.current.fetchNextPage(); });
  expect(mockCrops).toHaveBeenNthCalledWith(2, 'LK', '', 'Cereals', '20', expect.anything());
  await waitFor(() => expect(result.current.hasNextPage).toBe(false));

  await rerender({ search: 'missing' });
  await waitFor(() => expect(result.current.data?.pages[0].items).toEqual([]));
  expect(client.getQueryData(keys.crops('LK', '', 'Cereals'))).toBeDefined();
});

test('returns all continuous and standing strategies without filtering out rotation', async () => {
  mockStrategies.mockResolvedValueOnce(sampleStrategies);
  const { wrapper } = setup();
  const { result } = await renderHook(() => useStrategies('LK'), { wrapper });

  await waitFor(() =>
    expect(result.current.data?.map((s) => s.id)).toEqual([
      'continuous_rainfed',
      'continuous_irrigated',
      'standing_rainfed',
      'fallow_rainfed',
    ]),
  );
  expect(getSelectedStrategy(result.current.data, null, 'continuous_rainfed')?.id).toBe('continuous_rainfed');
  expect(getSelectedStrategy(result.current.data, 'fallow_rainfed', 'continuous_rainfed')?.requiresCrop).toBe(false);
});

test('waits for a valid draft and refetches a failed plan', async () => {
  const draft: PlanRequestDto = {
    countryId: 'LK',
    strategyId: 'continuous_rainfed',
    cropId: 'rice',
    sowingDate: '2026-11-15',
    irrigation: 'rainfed',
    points: [{ x: 10, y: 10 }, { x: 60, y: 10 }, { x: 60, y: 70 }],
  };
  mockPlan.mockRejectedValueOnce(new ApiError('http', 503)).mockResolvedValueOnce(samplePlanDto);

  const { wrapper } = setup();
  const { result, rerender } = await renderHook(
    ({ request }: { request: PlanRequestDto | null }) => usePlan(request),
    { wrapper, initialProps: { request: null as PlanRequestDto | null } },
  );
  expect(mockPlan).not.toHaveBeenCalled();

  await rerender({ request: draft });
  await waitFor(() => expect(result.current.isError).toBe(true));
  await act(async () => { await result.current.refetch(); });
  await waitFor(() => expect(result.current.data?.timeline).toHaveLength(2));
  expect(result.current.data?.first.crop.name).toBe('Paddy Rice');
  expect(result.current.data?.rotations[0].id).toBe('rice__mungbean');
});
