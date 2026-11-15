import { create } from 'zustand';
import { isValidBoundary, type Point } from '@/features/area/model';
import { calendarDate } from '@/utils/format';

export type GeoPoint = { latitude: number; longitude: number };

export type RotationFilterId = 'default' | 'water' | 'soil' | 'pest' | 'ease';

export type UncertaintyPreset = 'conservative' | 'balanced' | 'flexible' | 'custom';

export type ExpiryThresholds = {
  expirySafetyDays: number;
  collisionThresholdPct: number;
  weatherVolatility: number;
};

export const UNCERTAINTY_PRESETS: Record<Exclude<UncertaintyPreset, 'custom'>, ExpiryThresholds> = {
  conservative: { expirySafetyDays: 14, collisionThresholdPct: 10, weatherVolatility: 0.28 },
  balanced: { expirySafetyDays: 7, collisionThresholdPct: 25, weatherVolatility: 0.18 },
  flexible: { expirySafetyDays: 3, collisionThresholdPct: 40, weatherVolatility: 0.10 },
};

const THRESHOLDS_STORAGE_KEY = 'cresco.expiry-thresholds';

function clampSafetyDays(value: number): number {
  if (!Number.isFinite(value)) return 7;
  return Math.round(Math.max(0, Math.min(35, value)));
}

function clampCollisionPct(value: number): number {
  if (!Number.isFinite(value)) return 25;
  return Math.round(Math.max(5, Math.min(75, value)));
}

function clampVolatility(value: number): number {
  if (!Number.isFinite(value)) return 0.18;
  return Number(Math.max(0.05, Math.min(0.5, value)).toFixed(2));
}

function detectPreset(thresholds: ExpiryThresholds): UncertaintyPreset {
  for (const preset of ['conservative', 'balanced', 'flexible'] as const) {
    const target = UNCERTAINTY_PRESETS[preset];
    if (
      thresholds.expirySafetyDays === target.expirySafetyDays &&
      thresholds.collisionThresholdPct === target.collisionThresholdPct &&
      Math.abs(thresholds.weatherVolatility - target.weatherVolatility) < 0.005
    ) {
      return preset;
    }
  }
  return 'custom';
}

function getWebStorage(): Storage | null {
  try {
    if (typeof window !== 'undefined' && 'localStorage' in window && window.localStorage) {
      return window.localStorage;
    }
  } catch {
    // Ignore storage unavailability (native/SSR/Jest)
  }
  return null;
}

function readStoredThresholds(): Partial<ExpiryThresholds & { uncertaintyPreset: UncertaintyPreset }> {
  try {
    const storage = getWebStorage();
    if (storage) {
      const raw = storage.getItem(THRESHOLDS_STORAGE_KEY);
      if (!raw) return {};
      const parsed = JSON.parse(raw) as Partial<ExpiryThresholds>;
      if (!parsed || typeof parsed !== 'object') return {};
      const merged: ExpiryThresholds = {
        expirySafetyDays: parsed.expirySafetyDays !== undefined ? clampSafetyDays(parsed.expirySafetyDays) : 7,
        collisionThresholdPct: parsed.collisionThresholdPct !== undefined ? clampCollisionPct(parsed.collisionThresholdPct) : 25,
        weatherVolatility: parsed.weatherVolatility !== undefined ? clampVolatility(parsed.weatherVolatility) : 0.18,
      };
      return {
        ...merged,
        uncertaintyPreset: detectPreset(merged),
      };
    }
  } catch {
    // Ignore storage unavailability (native/SSR/Jest)
  }
  return {};
}

function writeStoredThresholds(thresholds: ExpiryThresholds | null): void {
  try {
    const storage = getWebStorage();
    if (storage) {
      if (!thresholds) {
        storage.removeItem(THRESHOLDS_STORAGE_KEY);
      } else {
        storage.setItem(THRESHOLDS_STORAGE_KEY, JSON.stringify(thresholds));
      }
    }
  } catch {
    // Ignore storage unavailability (native/SSR/Jest)
  }
}

export type SavedFarmInput = {
  id: number;
  name: string;
  country: string;
  latitude: number;
  longitude: number;
  area_ha?: number | null;
  boundary?: GeoPoint[] | null;
  irrigation?: string | null;
  crop_id?: string | null;
  start_date?: string | null;
};

type Draft = {
  farmId: number | null;
  farmName: string;
  countryId: string;
  latitude: number;
  longitude: number;
  zoom: number;
  points: Point[];
  boundary: GeoPoint[];
  areaHa: number | null;
  closed: boolean;
  reached: number;
  strategyId: string | null;
  irrigation: 'rainfed' | 'irrigated';
  cropId: string | null;
  sowingDate: string;
  selectedRotationId: string | null;
  rotationFilter: RotationFilterId;
  customCropIds: string[];
  tNowDay: number;
  observedNdvi: number | null;
  uncertaintyPreset: UncertaintyPreset;
  expirySafetyDays: number;
  collisionThresholdPct: number;
  weatherVolatility: number;
};

const initial = (): Draft => ({
  farmId: null,
  farmName: '',
  countryId: '',
  latitude: 7.8731,
  longitude: 80.7718,
  zoom: 7,
  points: [],
  boundary: [],
  areaHa: null,
  closed: false,
  reached: 1,
  strategyId: null,
  irrigation: 'rainfed',
  cropId: null,
  sowingDate: calendarDate(),
  selectedRotationId: null,
  rotationFilter: 'default',
  customCropIds: [],
  tNowDay: 42,
  observedNdvi: null,
  uncertaintyPreset: 'balanced',
  expirySafetyDays: 7,
  collisionThresholdPct: 25,
  weatherVolatility: 0.18,
});

function pointToGeo(point: Point, latitude: number, longitude: number, zoom: number): GeoPoint {
  const spanLat = 360 / Math.pow(2, Math.max(zoom, 12));
  const cosLat = Math.max(0.2, Math.cos((latitude * Math.PI) / 180));
  const spanLon = spanLat / cosLat;
  return {
    latitude: Number((latitude + ((50 - point.y) / 100) * spanLat).toFixed(6)),
    longitude: Number((longitude + ((point.x - 50) / 100) * spanLon).toFixed(6)),
  };
}

const DEFAULT_POLYGON: Point[] = [
  { x: 20, y: 20 },
  { x: 80, y: 20 },
  { x: 80, y: 80 },
  { x: 20, y: 80 },
];

function boundaryToPoints(boundary?: GeoPoint[] | null): Point[] {
  if (!boundary || boundary.length < 3) return DEFAULT_POLYGON;
  const lats = boundary.map((p) => p.latitude);
  const lons = boundary.map((p) => p.longitude);
  const minLat = Math.min(...lats);
  const maxLat = Math.max(...lats);
  const minLon = Math.min(...lons);
  const maxLon = Math.max(...lons);
  const spanLat = maxLat - minLat;
  const spanLon = maxLon - minLon;
  if (spanLat <= 1e-9 || spanLon <= 1e-9) return DEFAULT_POLYGON;
  const mapped = boundary.map((p) => ({
    x: Number((20 + ((p.longitude - minLon) / spanLon) * 60).toFixed(2)),
    y: Number((20 + ((maxLat - p.latitude) / spanLat) * 60).toFixed(2)),
  }));
  return isValidBoundary(mapped) ? mapped : DEFAULT_POLYGON;
}

type Planner = Draft & {
  chooseCountry: (countryId: string, center?: { latitude: number; longitude: number; zoom?: number }) => void;
  setCenter: (latitude: number, longitude: number, zoom?: number) => void;
  addPoint: (point: Point) => void;
  addGeoCorner: (point: Point, geo: GeoPoint) => void;
  close: () => void;
  clearField: () => void;
  setAreaHa: (areaHa: number | null) => void;
  chooseStrategy: (strategyId: string) => void;
  setIrrigation: (irrigation: 'rainfed' | 'irrigated') => void;
  chooseCrop: (cropId: string) => void;
  setDate: (sowingDate: string) => void;
  selectRotation: (id: string | null) => void;
  setRotationFilter: (filter: RotationFilterId) => void;
  setCustomCropIds: (cropIds: string[]) => void;
  toggleCustomCropId: (cropId: string) => void;
  setMonitorParams: (params: { tNowDay?: number; observedNdvi?: number | null; weatherVolatility?: number }) => void;
  setUncertaintyPreset: (preset: UncertaintyPreset) => void;
  setExpiryThresholds: (params: { expirySafetyDays?: number; collisionThresholdPct?: number; weatherVolatility?: number }) => void;
  setSavedFarmMeta: (farmId: number | null, farmName?: string) => void;
  loadSavedFarm: (farm: SavedFarmInput) => void;
  unlock: (step: number) => void;
  reset: () => void;
};

export const usePlanner = create<Planner>()((set) => ({
  ...initial(),
  ...readStoredThresholds(),
  chooseCountry: (countryId, center) => set((state) => {
    if (state.countryId === countryId && !center) return state;
    return {
      ...initial(),
      uncertaintyPreset: state.uncertaintyPreset,
      expirySafetyDays: state.expirySafetyDays,
      collisionThresholdPct: state.collisionThresholdPct,
      weatherVolatility: state.weatherVolatility,
      countryId,
      latitude: center?.latitude ?? state.latitude,
      longitude: center?.longitude ?? state.longitude,
      zoom: center?.zoom ?? state.zoom,
      reached: 2,
    };
  }),
  setCenter: (latitude, longitude, zoom) => set((state) => ({
    latitude,
    longitude,
    zoom: zoom ?? state.zoom,
  })),
  addPoint: (point) => set((state) => {
    if (state.closed) return state;
    const geo = pointToGeo(point, state.latitude, state.longitude, state.zoom);
    return {
      points: [...state.points, point],
      boundary: [...state.boundary, geo],
    };
  }),
  addGeoCorner: (point, geo) => set((state) => {
    if (state.closed) return state;
    return {
      points: [...state.points, point],
      boundary: [...state.boundary, geo],
    };
  }),
  close: () => set((state) => {
    if (!isValidBoundary(state.points)) return state;
    if (state.boundary.length >= 3) {
      const lat = state.boundary.reduce((s, p) => s + p.latitude, 0) / state.boundary.length;
      const lon = state.boundary.reduce((s, p) => s + p.longitude, 0) / state.boundary.length;
      return {
        closed: true,
        latitude: Number(lat.toFixed(6)),
        longitude: Number(lon.toFixed(6)),
      };
    }
    return { closed: true };
  }),
  clearField: () => set({ points: [], boundary: [], areaHa: null, closed: false, reached: 2 }),
  setAreaHa: (areaHa) => set({ areaHa }),
  chooseStrategy: (strategyId) => set((state) => {
    const irrigation = strategyId.includes('irrigated') ? 'irrigated' : 'rainfed';
    if (state.strategyId === strategyId && state.irrigation === irrigation) return state;
    return {
      strategyId,
      irrigation,
      cropId: strategyId === 'fallow' ? null : state.cropId,
      reached: Math.min(state.reached, 3),
    };
  }),
  setIrrigation: (irrigation) => set({ irrigation }),
  chooseCrop: (cropId) => set((state) => (state.cropId === cropId ? state : { cropId, reached: Math.min(state.reached, 4) })),
  setDate: (sowingDate) => set((state) => (state.sowingDate === sowingDate ? state : { sowingDate, reached: Math.min(state.reached, 4) })),
  selectRotation: (selectedRotationId) => set({ selectedRotationId }),
  setRotationFilter: (rotationFilter) => set({ rotationFilter }),
  setCustomCropIds: (cropIds) => set({ customCropIds: Array.from(new Set(cropIds)).slice(0, 4) }),
  toggleCustomCropId: (cropId) => set((state) => {
    if (state.customCropIds.includes(cropId)) {
      return { customCropIds: state.customCropIds.filter((id) => id !== cropId) };
    }
    if (state.customCropIds.length >= 4) {
      return state;
    }
    return { customCropIds: [...state.customCropIds, cropId] };
  }),
  setMonitorParams: (params) => set((state) => {
    if (params.weatherVolatility === undefined) {
      return {
        tNowDay: params.tNowDay !== undefined ? params.tNowDay : state.tNowDay,
        observedNdvi: params.observedNdvi !== undefined ? params.observedNdvi : state.observedNdvi,
      };
    }
    const nextVol = clampVolatility(params.weatherVolatility);
    const nextThresholds: ExpiryThresholds = {
      expirySafetyDays: state.expirySafetyDays,
      collisionThresholdPct: state.collisionThresholdPct,
      weatherVolatility: nextVol,
    };
    writeStoredThresholds(nextThresholds);
    return {
      tNowDay: params.tNowDay !== undefined ? params.tNowDay : state.tNowDay,
      observedNdvi: params.observedNdvi !== undefined ? params.observedNdvi : state.observedNdvi,
      weatherVolatility: nextVol,
      uncertaintyPreset: detectPreset(nextThresholds),
    };
  }),
  setUncertaintyPreset: (preset) => set((state) => {
    if (preset === 'custom') {
      return { uncertaintyPreset: 'custom' };
    }
    const values = UNCERTAINTY_PRESETS[preset];
    writeStoredThresholds(values);
    return {
      uncertaintyPreset: preset,
      expirySafetyDays: values.expirySafetyDays,
      collisionThresholdPct: values.collisionThresholdPct,
      weatherVolatility: values.weatherVolatility,
    };
  }),
  setExpiryThresholds: (params) => set((state) => {
    const nextThresholds: ExpiryThresholds = {
      expirySafetyDays:
        params.expirySafetyDays !== undefined ? clampSafetyDays(params.expirySafetyDays) : state.expirySafetyDays,
      collisionThresholdPct:
        params.collisionThresholdPct !== undefined
          ? clampCollisionPct(params.collisionThresholdPct)
          : state.collisionThresholdPct,
      weatherVolatility:
        params.weatherVolatility !== undefined ? clampVolatility(params.weatherVolatility) : state.weatherVolatility,
    };
    writeStoredThresholds(nextThresholds);
    return {
      ...nextThresholds,
      uncertaintyPreset: detectPreset(nextThresholds),
    };
  }),
  setSavedFarmMeta: (farmId, farmName) => set((state) => ({
    farmId,
    farmName: farmName !== undefined ? farmName : state.farmName,
  })),
  loadSavedFarm: (farm) => set((state) => {
    const irrigation = farm.irrigation === 'irrigated' ? 'irrigated' : 'rainfed';
    const boundary = farm.boundary && farm.boundary.length >= 3 ? farm.boundary : [];
    return {
      farmId: farm.id,
      farmName: farm.name,
      countryId: farm.country,
      latitude: farm.latitude,
      longitude: farm.longitude,
      zoom: 13,
      points: boundaryToPoints(farm.boundary),
      boundary,
      areaHa: farm.area_ha ?? null,
      closed: true,
      reached: 6,
      strategyId: farm.crop_id ? 'standing' : 'fallow',
      irrigation,
      cropId: farm.crop_id ?? state.cropId,
      sowingDate: farm.start_date ?? state.sowingDate,
    };
  }),
  unlock: (step) => set((state) => ({ reached: Math.max(state.reached, step) })),
  reset: () => {
    writeStoredThresholds(null);
    set(initial());
  },
}));
