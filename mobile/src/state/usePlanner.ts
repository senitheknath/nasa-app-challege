import { create } from 'zustand';
import { isValidBoundary, type Point } from '@/features/area/model';
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
  close: () => set((state) => isValidBoundary(state.points) ? { closed: true } : state),
  clearField: () => set({ points: [], closed: false, reached: 2 }),
  chooseStrategy: (strategyId) => set((state) => state.strategyId === strategyId ? state
    : { strategyId, reached: Math.min(state.reached, 3) }),
  chooseCrop: (cropId) => set((state) => state.cropId === cropId ? state
    : { cropId, reached: Math.min(state.reached, 4) }),
  setDate: (sowingDate) => set((state) => state.sowingDate === sowingDate ? state
    : { sowingDate, reached: Math.min(state.reached, 4) }),
  unlock: (step) => set((state) => ({ reached: Math.max(state.reached, step) })),
  reset: () => set(initial()),
}));
