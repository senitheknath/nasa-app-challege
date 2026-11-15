import { create } from 'zustand';
import { polygonArea, type Point } from '@/features/area/model';
import { calendarDate } from '@/utils/format';

type Draft = {
  countryId: string;
  points: Point[];
  closed: boolean;
  reached: number;
  strategyId: string | null;
  cropId: string | null;
  sowingDate: string;
};

const initial = (): Draft => ({
  countryId: '', points: [], closed: false, reached: 1, strategyId: null, cropId: null, sowingDate: calendarDate(),
});

type Planner = Draft & {
  chooseCountry: (id: string) => void;
  addPoint: (point: Point) => void;
  close: () => void;
  clearField: () => void;
  chooseStrategy: (id: string) => void;
  chooseCrop: (id: string) => void;
  setDate: (value: string) => void;
  unlock: (step: number) => void;
  reset: () => void;
};

export const usePlanner = create<Planner>()((set) => ({
  ...initial(),
  chooseCountry: (countryId) => set((state) => state.countryId === countryId ? state : { ...initial(), countryId, reached: 2 }),
  addPoint: (point) => set((state) => state.closed ? state : { points: [...state.points, point] }),
  close: () => set((state) => polygonArea(state.points) > 0 ? { closed: true } : state),
  clearField: () => set({ points: [], closed: false, reached: 2 }),
  chooseStrategy: (strategyId) => set({ strategyId }),
  chooseCrop: (cropId) => set({ cropId }),
  setDate: (sowingDate) => set({ sowingDate }),
  unlock: (step) => set((state) => ({ reached: Math.max(state.reached, step) })),
  reset: () => set(initial()),
}));
