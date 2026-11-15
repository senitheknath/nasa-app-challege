import { measurementSchema, mapSchema, placesSchema, type FieldDto } from '@/features/area/model';
import { countryDataSchema } from '@/features/country/model';
import { categoriesSchema, cropPageSchema } from '@/features/crop/model';
import { climateResponseSchema, monitorResponseSchema, satelliteResponseSchema } from '@/features/monitor/model';
import { planSchema, type PlanRequestDto } from '@/features/plan/model';
import { strategiesSchema } from '@/features/strategy/model';
import type { GeoPoint } from '@/state/usePlanner';
import { rawRequest } from './client';

type RawPresets = {
  countries?: { code: string; name: string }[];
  stations?: { id: string; country: string; latitude: number; longitude: number }[];
  location_presets?: { id: string; country?: string; latitude?: number; longitude?: number; zoom?: number }[];
  categories?: string[];
};

type RawKnowledgeStatus = {
  total_crops?: number;
};

type RawPlacesResponse = {
  map_view?: { lat?: number; lon?: number; zoom?: number; country_name?: string };
  regions?: { id?: string | number; name?: string; lat?: number; latitude?: number; lon?: number; longitude?: number }[];
  results?: { id?: string | number; name?: string; latitude?: number; longitude?: number; admin1?: string; country?: string }[];
};

type RawLayersResponse = {
  layers?: { id?: string; title?: string }[];
};

type RawAutofillResponse = {
  location?: { country?: string; latitude?: number; longitude?: number };
  autofill?: {
    area_ha?: { value?: number | null };
    ph?: { value?: number | null };
    drainage?: { value?: string | null };
    annual_rainfall_mm?: { value?: number | null };
    rainfall_mm?: { value?: number | null };
    mean_temperature_c?: { value?: number | null };
    temperature_c?: { value?: number | null };
    wetness?: { value?: string | null };
  };
};

type RawCropsResponse = {
  total?: number;
  limit?: number;
  offset?: number;
  items?: {
    crop_id?: string;
    id?: string;
    crop_name?: string;
    common_name?: string;
    name?: string;
    category?: string;
    family?: string;
    yield_tonnes_per_ha?: number;
    yieldTonnesPerHectare?: number;
    water_percent?: number;
    waterPercent?: number;
    growth_days?: string | number;
    cycle_days_min?: number;
    cycle_days_max?: number;
    suitability?: string;
  }[];
};

type RawRotationsResponse = {
  status?: string;
  mode?: string;
  total?: number;
  rotations?: {
    id: string;
    name: string;
    rank: number;
    ease_rank?: number;
    score: number;
    rating: string;
    overall_status?: string;
    summary?: string;
    ease_adjusted_score?: number;
    timeline?: {
      overall_status?: string;
      feasible?: boolean;
      total_agronomic_score?: number;
      safe_expiry_date?: string | null;
      hard_expiry_date?: string | null;
      days_until_safe_expiry?: number | null;
      days_until_hard_expiry?: number | null;
      collision_probability_pct?: number | null;
      turnaround_summary?: { buffer_days: number; status: string; advisory: string } | null;
      uncertainty_cone?: { slot_1_span_days?: number; slot_2_span_days?: number; collision_probability_pct?: number } | null;
      slots?: {
        crop_id: string;
        crop_name: string;
        family?: string;
        window?: string;
        sowing_date: string;
        harvest_nominal_date: string;
        harvest_window?: string;
        growth_cycle_days?: { minimum: number; nominal: number; maximum: number };
        stages?: { stage: string; description?: string; start_date: string; end_date: string; duration_days: number }[];
        kc_max?: number;
        delay_slack_days?: number;
        turnaround_buffer_after_days?: number | null;
        safe_expiry_date?: string | null;
        hard_expiry_date?: string | null;
        days_until_safe_expiry?: number | null;
        days_until_hard_expiry?: number | null;
        collision_probability_pct?: number | null;
      }[];
    };
  }[];
};

function toGeoJsonPolygon(boundary?: readonly GeoPoint[]) {
  if (!boundary || boundary.length < 3) return undefined;
  const ring = boundary.map((p) => [p.longitude, p.latitude]);
  const first = ring[0];
  const last = ring[ring.length - 1];
  if (first[0] !== last[0] || first[1] !== last[1]) {
    ring.push([first[0], first[1]]);
  }
  return { type: 'Polygon', coordinates: [ring] };
}

function haversineKm(a: GeoPoint, b: GeoPoint): number {
  const R = 6371;
  const dLat = ((b.latitude - a.latitude) * Math.PI) / 180;
  const dLon = ((b.longitude - a.longitude) * Math.PI) / 180;
  const lat1 = (a.latitude * Math.PI) / 180;
  const lat2 = (b.latitude * Math.PI) / 180;
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLon / 2) ** 2;
  return 2 * R * Math.asin(Math.sqrt(h));
}

function computeGeodesicMetrics(boundary?: readonly GeoPoint[]): { hectares: number; perimeterKm: number } {
  if (!boundary || boundary.length < 3) {
    return { hectares: 0, perimeterKm: 0 };
  }
  let perimeterKm = 0;
  for (let i = 0; i < boundary.length; i++) {
    perimeterKm += haversineKm(boundary[i], boundary[(i + 1) % boundary.length]);
  }
  const refLat = boundary.reduce((sum, p) => sum + p.latitude, 0) / boundary.length;
  const metersPerDegLat = 111132.92;
  const metersPerDegLon = 111412.84 * Math.cos((refLat * Math.PI) / 180);
  let twiceAreaSqM = 0;
  for (let i = 0; i < boundary.length; i++) {
    const curr = boundary[i];
    const next = boundary[(i + 1) % boundary.length];
    const x1 = curr.longitude * metersPerDegLon;
    const y1 = curr.latitude * metersPerDegLat;
    const x2 = next.longitude * metersPerDegLon;
    const y2 = next.latitude * metersPerDegLat;
    twiceAreaSqM += x1 * y2 - x2 * y1;
  }
  const hectares = Math.abs(twiceAreaSqM) / 2 / 10000;
  return { hectares: Number(hectares.toFixed(2)), perimeterKm: Number(perimeterKm.toFixed(2)) };
}

export const endpoints = {
  countries: async (signal: AbortSignal) => {
    const [presets, status] = await Promise.all([
      rawRequest({ path: '/api/system/presets', signal }) as Promise<RawPresets>,
      rawRequest({ path: '/api/knowledge/status', signal }) as Promise<RawKnowledgeStatus>,
    ]);

    const coordByCountry = new Map<string, { latitude: number; longitude: number; zoom?: number }>();
    for (const s of presets.stations ?? []) {
      if (s.country && !coordByCountry.has(s.country.toUpperCase())) {
        coordByCountry.set(s.country.toUpperCase(), { latitude: s.latitude, longitude: s.longitude, zoom: 7 });
      }
    }
    for (const p of presets.location_presets ?? []) {
      if (p.country && p.latitude !== undefined && p.longitude !== undefined && !coordByCountry.has(p.country.toUpperCase())) {
        coordByCountry.set(p.country.toUpperCase(), { latitude: p.latitude, longitude: p.longitude, zoom: p.zoom ?? 7 });
      }
    }

    const defaultCountryId = presets.stations?.[0]?.country?.toUpperCase() || 'LK';
    const rawCountries = (presets.countries ?? []).map((c) => {
      const code = c.code.toUpperCase();
      const coords = coordByCountry.get(code);
      return {
        id: code,
        name: c.name,
        supported: true,
        ...(coords ? { latitude: coords.latitude, longitude: coords.longitude, zoom: coords.zoom } : {}),
      };
    });

    return countryDataSchema.parse({
      defaultCountryId,
      currentSeason: 'Continuous',
      cropCount: Number(status.total_crops ?? 107),
      seasonCount: presets.categories?.length || 1,
      defaultStrategyId: 'continuous_rainfed',
      defaultCropId: 'rice',
      countries: rawCountries,
    });
  },

  map: async (country: string, signal: AbortSignal) => {
    const [placesRes, layersRes] = await Promise.all([
      rawRequest({ path: '/api/earth-data/places', query: { country }, signal }) as Promise<RawPlacesResponse>,
      rawRequest({ path: '/api/earth-data/layers', signal }) as Promise<RawLayersResponse>,
    ]);
    const mv = placesRes.map_view;
    const regions = (placesRes.regions ?? [])
      .map((r) => ({
        id: String(r.id ?? r.name ?? ''),
        name: String(r.name ?? ''),
        latitude: Number(r.lat ?? r.latitude ?? mv?.lat ?? 7.8731),
        longitude: Number(r.lon ?? r.longitude ?? mv?.lon ?? 80.7718),
      }))
      .filter((r) => r.id && r.name);

    return mapSchema.parse({
      imageUrl: undefined,
      latitude: mv?.lat ?? 7.8731,
      longitude: mv?.lon ?? 80.7718,
      zoom: mv?.zoom ?? 7,
      countryName: mv?.country_name,
      layerTitle: layersRes.layers?.[0]?.title,
      regions,
    });
  },

  places: async (country: string, q: string, signal: AbortSignal) => {
    const res = (await rawRequest({
      path: '/api/earth-data/places',
      query: { country, q: q.trim() || undefined },
      signal,
    })) as RawPlacesResponse;

    if (q.trim().length < 2) {
      const regions = (res.regions ?? []).map((r) => ({
        id: String(r.id ?? r.name ?? ''),
        name: String(r.name ?? ''),
        latitude: Number(r.lat ?? r.latitude),
        longitude: Number(r.lon ?? r.longitude),
        detail: res.map_view?.country_name,
      })).filter((r) => r.id && r.name);
      return placesSchema.parse(regions);
    }

    const results = (res.results ?? []).map((r) => ({
      id: String(r.id ?? r.name ?? ''),
      name: String(r.name ?? ''),
      latitude: r.latitude,
      longitude: r.longitude,
      detail: [r.admin1, r.country].filter(Boolean).join(', ') || undefined,
    })).filter((r) => r.id && r.name);
    return placesSchema.parse(results);
  },

  measure: async (
    body: FieldDto & { latitude?: number; longitude?: number; boundary?: GeoPoint[] },
    signal: AbortSignal,
  ) => {
    const boundary = body.boundary;
    const res = (await rawRequest({
      method: 'POST',
      path: '/api/earth-data/autofill',
      body: {
        country: body.countryId,
        latitude: body.latitude,
        longitude: body.longitude,
        boundary: toGeoJsonPolygon(boundary),
      },
      signal,
    })) as RawAutofillResponse;

    const geo = computeGeodesicMetrics(boundary);
    const hectares = Number(res.autofill?.area_ha?.value ?? geo.hectares ?? 0);
    const acres = Number((hectares * 2.47105).toFixed(2));
    const perimeterKm = geo.perimeterKm > 0
      ? geo.perimeterKm
      : Number((Math.sqrt(Math.max(hectares, 0.01) * 10000) * 4 / 1000).toFixed(2));

    return measurementSchema.parse({
      hectares,
      acres,
      perimeterKm,
      ph: res.autofill?.ph?.value ?? null,
      drainage: res.autofill?.drainage?.value ?? null,
      annualRainfallMm: res.autofill?.annual_rainfall_mm?.value ?? res.autofill?.rainfall_mm?.value ?? null,
      meanTemperatureC: res.autofill?.mean_temperature_c?.value ?? res.autofill?.temperature_c?.value ?? null,
      wetness: res.autofill?.wetness?.value ?? null,
      latitude: res.location?.latitude ?? body.latitude,
      longitude: res.location?.longitude ?? body.longitude,
    });
  },

  strategies: async (_country: string, signal: AbortSignal) => {
    await rawRequest({ path: '/api/system/presets', signal });
    return strategiesSchema.parse([
      {
        id: 'continuous_rainfed',
        tag: 'Rainfed',
        title: 'Continuous Rotation (Rainfed)',
        description: 'Season-free continuous multi-crop chaining driven by local rainfall and turnaround buffers.',
        requiresCrop: true,
      },
      {
        id: 'continuous_irrigated',
        tag: 'Irrigated',
        title: 'Continuous Rotation (Irrigated)',
        description: 'Year-round irrigated crop sequence optimization with dynamic harvest-to-sowing transitions.',
        requiresCrop: true,
      },
      {
        id: 'standing_rainfed',
        tag: 'Standing · Rainfed',
        title: 'Standing Crop (Rainfed)',
        description: 'Start from an active rainfed crop and plan the optimal follow-up transition.',
        requiresCrop: true,
      },
      {
        id: 'standing_irrigated',
        tag: 'Standing · Irrigated',
        title: 'Standing Crop (Irrigated)',
        description: 'Start from an active irrigated crop and schedule the next high-compatibility rotation.',
        requiresCrop: true,
      },
      {
        id: 'fallow_rainfed',
        tag: 'Fallow',
        title: 'Bare / Fallow Field',
        description: 'Field is currently resting; recommend the best opening crop and follow-up sequence.',
        requiresCrop: false,
      },
    ]);
  },

  categories: async (_country: string, signal: AbortSignal) => {
    const res = (await rawRequest({ path: '/api/knowledge/categories', signal })) as { categories?: string[] };
    return categoriesSchema.parse(
      (res.categories ?? []).map((cat) => ({ id: cat, label: cat })),
    );
  },

  crops: async (_country: string, q: string, category: string, cursor: string | undefined, signal: AbortSignal) => {
    const offset = Number(cursor) || 0;
    const limit = 20;
    const res = (await rawRequest({
      path: '/api/knowledge/crops',
      query: {
        q: q.trim() || undefined,
        category: category || undefined,
        limit,
        offset,
      },
      signal,
    })) as RawCropsResponse;

    const rawItems = res.items ?? [];
    const total = Number(res.total ?? rawItems.length);
    const items = rawItems.map((item) => {
      const cat = item.category || 'General';
      const growthDays = item.growth_days
        ? String(item.growth_days)
        : (item.cycle_days_min && item.cycle_days_max ? `${item.cycle_days_min}-${item.cycle_days_max}d` : undefined);
      return {
        id: String(item.crop_id ?? item.id ?? ''),
        name: String(item.crop_name ?? item.common_name ?? item.name ?? ''),
        category: { id: cat, label: cat },
        yieldTonnesPerHectare: Number(item.yield_tonnes_per_ha ?? item.yieldTonnesPerHectare ?? 4.5),
        waterPercent: Number(item.water_percent ?? item.waterPercent ?? 55),
        family: item.family,
        growthDays,
        suitability: item.suitability,
      };
    });

    return cropPageSchema.parse({
      items,
      nextCursor: offset + items.length < total ? String(offset + items.length) : null,
    });
  },

  plan: async (
    body: PlanRequestDto & {
      latitude?: number;
      longitude?: number;
      boundary?: GeoPoint[];
      areaHa?: number | null;
      irrigation?: 'rainfed' | 'irrigated';
    },
    signal: AbortSignal,
  ) => {
    const irrigation = body.irrigation ?? (body.strategyId.includes('irrigated') ? 'irrigated' : 'rainfed');
    const res = (await rawRequest({
      method: 'POST',
      path: '/api/agronomy/rotations',
      body: {
        country: body.countryId,
        latitude: body.latitude,
        longitude: body.longitude,
        boundary: toGeoJsonPolygon(body.boundary),
        area_ha: body.areaHa ?? undefined,
        start_date: body.sowingDate,
        irrigation,
        candidate_crop_ids: body.cropId ? [body.cropId] : undefined,
        max_sequences: 12,
      },
      signal,
    })) as RawRotationsResponse;

    const rotations = res.rotations ?? [];
    const top = rotations[0];
    const topSlots = top?.timeline?.slots ?? [];
    const fallbackCrop = {
      id: topSlots[0]?.crop_id ?? body.cropId ?? 'rice',
      name: topSlots[0]?.crop_name ?? body.cropId ?? 'Rice',
      category: { id: topSlots[0]?.family ?? 'Cereal', label: topSlots[0]?.family ?? 'Cereal' },
      yieldTonnesPerHectare: 4.5,
      waterPercent: irrigation === 'irrigated' ? 70 : 50,
    };

    const timeline = topSlots.map((slot, idx) => ({
      id: `${top?.id ?? 'rot'}-${idx}`,
      season: slot.window || `Slot ${idx + 1}`,
      year: Number(slot.sowing_date?.slice(0, 4)) || new Date().getFullYear(),
      crop: {
        id: slot.crop_id,
        name: slot.crop_name,
        category: { id: slot.family ?? 'Crop', label: slot.family ?? 'Crop' },
        yieldTonnesPerHectare: 4.5,
        waterPercent: irrigation === 'irrigated' ? 70 : 50,
      },
      note: `${slot.sowing_date} → ${slot.harvest_nominal_date}`,
      sowingDate: slot.sowing_date,
      harvestDate: slot.harvest_nominal_date,
      harvestWindow: slot.harvest_window,
      family: slot.family,
      growthDays: slot.growth_cycle_days
        ? `${slot.growth_cycle_days.minimum}-${slot.growth_cycle_days.maximum}d (nom ${slot.growth_cycle_days.nominal}d)`
        : undefined,
      stages: slot.stages,
      turnaroundBufferDays: slot.turnaround_buffer_after_days ?? undefined,
      delaySlackDays: slot.delay_slack_days,
      safeExpiryDate: slot.safe_expiry_date ?? undefined,
      hardExpiryDate: slot.hard_expiry_date ?? undefined,
      collisionProbabilityPct: slot.collision_probability_pct ?? undefined,
      kcMax: slot.kc_max,
    }));

    return planSchema.parse({
      hectares: body.areaHa ?? 1.0,
      strategyTag: irrigation === 'irrigated' ? 'Irrigated' : 'Rainfed',
      crop: fallbackCrop,
      timeline,
      mode: res.mode ?? 'continuous',
      total: res.total ?? rotations.length,
      rotations,
    });
  },

  monitor3d: async (body: unknown, signal: AbortSignal) =>
    monitorResponseSchema.parse(await rawRequest({ method: 'POST', path: '/api/earth-data/monitor-3d', body, signal })),

  satellite: async (body: unknown, signal: AbortSignal) =>
    satelliteResponseSchema.parse(await rawRequest({ method: 'POST', path: '/api/earth-data/satellite', body, signal })),

  climate: async (body: unknown, signal: AbortSignal) =>
    climateResponseSchema.parse(await rawRequest({ method: 'POST', path: '/api/earth-data/climate', body, signal })),

  authLogin: (body: { email: string; password: string }, signal?: AbortSignal) =>
    rawRequest({ method: 'POST', path: '/api/auth/login', body, signal }) as Promise<{
      token: string;
      user: { id: number; email: string; display_name?: string | null };
    }>,

  authRegister: (body: { email: string; password: string; display_name?: string }, signal?: AbortSignal) =>
    rawRequest({ method: 'POST', path: '/api/auth/register', body, signal }) as Promise<{
      token: string;
      user: { id: number; email: string; display_name?: string | null };
    }>,

  authMe: (signal?: AbortSignal) =>
    rawRequest({ method: 'GET', path: '/api/auth/me', signal }) as Promise<{
      user: { id: number; email: string; display_name?: string | null };
    }>,

  farmsList: (signal?: AbortSignal) =>
    rawRequest({ method: 'GET', path: '/api/farms', signal }) as Promise<{
      farms: {
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
        updated_at?: string;
      }[];
    }>,

  farmSave: (
    body: {
      id?: number | null;
      name: string;
      country: string;
      latitude: number;
      longitude: number;
      area_ha?: number | null;
      boundary?: GeoPoint[];
      irrigation?: string;
      crop_id?: string | null;
      start_date?: string;
    },
    signal?: AbortSignal,
  ) => {
    const payload = {
      name: body.name,
      country: body.country,
      latitude: body.latitude,
      longitude: body.longitude,
      area_ha: body.area_ha ?? undefined,
      boundary: toGeoJsonPolygon(body.boundary),
      irrigation: body.irrigation,
      crop_id: body.crop_id ?? undefined,
      start_date: body.start_date,
    };
    if (body.id) {
      return rawRequest({ method: 'PUT', path: `/api/farms/${body.id}`, body: payload, signal }) as Promise<{
        farm: { id: number; name: string };
        status: string;
      }>;
    }
    return rawRequest({ method: 'POST', path: '/api/farms', body: payload, signal }) as Promise<{
      farm: { id: number; name: string };
      status: string;
    }>;
  },

  farmDelete: (farmId: number, signal?: AbortSignal) =>
    rawRequest({ method: 'DELETE', path: `/api/farms/${farmId}`, signal }) as Promise<{
      status: string;
      id: number;
    }>,
};
