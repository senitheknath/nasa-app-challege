import { z } from 'zod';
import { formatDate, formatNumber } from '@/utils/format';

export const monitorRequestSchema = z.object({
  country: z.string().min(1),
  latitude: z.number(),
  longitude: z.number(),
  boundary: z.unknown().optional(),
  area_ha: z.number().nullable().optional(),
  start_date: z.string().optional(),
  irrigation: z.string().optional(),
  t_now_day: z.number().int().nonnegative(),
  observed_ndvi: z.number().nullable().optional(),
  weather_volatility: z.number().optional(),
  max_sequences: z.number().optional(),
});

export const terrainVertexSchema = z.object({
  row: z.number(),
  col: z.number(),
  x_norm: z.number().optional(),
  y_norm: z.number().optional(),
  latitude: z.number().optional(),
  longitude: z.number().optional(),
  elevation_m: z.number(),
  relative_height_m: z.number().optional(),
  slope_pct: z.number().optional(),
  flow_dx: z.number().optional(),
  flow_dy: z.number().optional(),
  pooling_risk: z.string().optional(),
  twi: z.number().optional(),
  s1_s2_wetness_idx: z.number().optional(),
  downscaled_moisture_pct: z.number().optional(),
});

export const boundaryUvPointSchema = z.object({
  u: z.number(),
  v: z.number(),
  latitude: z.number().optional(),
  longitude: z.number().optional(),
});

export const terrainMeshSchema = z.object({
  grid_size: z.number(),
  span_km_x: z.number(),
  span_km_y: z.number(),
  area_km2: z.number(),
  elevation_m: z.number(),
  elevation_min_m: z.number().optional(),
  elevation_max_m: z.number().optional(),
  regional_slope_pct: z.number(),
  concavity_m: z.number().optional(),
  suggested_drainage_prior: z.string().optional(),
  boundary_uv: z.array(boundaryUvPointSchema).default([]),
  vertices: z.array(terrainVertexSchema),
  dem_tier: z.string().optional(),
  source: z.string().optional(),
});

export const soilHorizonSchema = z.object({
  depth_label: z.string(),
  depth_top_m: z.number().optional(),
  depth_bottom_m: z.number().optional(),
  ph: z.number(),
  sand_pct: z.number().optional(),
  clay_pct: z.number().optional(),
  silt_pct: z.number().optional(),
  soc_g_kg: z.number().optional(),
  usda_texture: z.string().optional(),
  volumetric_moisture_pct: z.number(),
  roots_present: z.boolean(),
});

export const uncertaintyConePointSchema = z.object({
  day: z.number(),
  nominal_progress_pct: z.number(),
  optimistic_bound_pct: z.number(),
  pessimistic_bound_pct: z.number(),
  is_observed_past: z.boolean().optional(),
});

export const liveStateSchema = z.object({
  t_now_day: z.number(),
  current_date: z.string(),
  growth_lag_days: z.number(),
  active_stage: z.string(),
  active_root_depth_m: z.number(),
  expected_ndvi: z.number(),
  observed_ndvi: z.number().nullable().optional(),
  safe_expiry_date: z.string().nullable().optional(),
  hard_expiry_date: z.string().nullable().optional(),
  days_until_safe_expiry: z.number().nullable().optional(),
  days_until_hard_expiry: z.number().nullable().optional(),
  sigma_at_harvest_days: z.number(),
  uncertainty_cone_series: z.array(uncertaintyConePointSchema).default([]),
});

export const liveRotationSchema = z.object({
  id: z.string(),
  name: z.string(),
  rank: z.number().optional(),
  ease_rank: z.number().optional(),
  score: z.number().optional(),
  rating: z.string().optional(),
  summary: z.string().optional(),
  live_state: liveStateSchema,
}).passthrough();

export const slab3dSchema = z.object({
  location: z.object({
    country: z.string(),
    latitude: z.number(),
    longitude: z.number(),
    area_ha: z.number().nullable().optional(),
    bounding_box: z.unknown().optional(),
  }).passthrough(),
  active_root_depth_m: z.number(),
  offline: z.boolean().optional(),
  atmosphere_layer: z.record(z.string(), z.unknown()),
  canopy_layer: z.object({
    ndvi_current: z.number(),
    is_bare_soil: z.boolean().optional(),
    ecostress_thermal_stress_delta_c: z.number().optional(),
    overpasses: z.array(z.unknown()).optional(),
  }).passthrough(),
  terrain_3d_mesh: terrainMeshSchema,
  soil_3d_horizons: z.array(soilHorizonSchema),
  update_frequencies: z.record(z.string(), z.unknown()),
  sensor_fusion: z.object({
    stack: z.array(z.string()).default([]),
    moisture_fusion_3way: z.record(z.string(), z.unknown()).optional(),
    combined_parcel_dt_days: z.number().nullable().optional(),
    parcel_mean_moisture_conserved_pct: z.number().optional(),
  }).passthrough(),
});

export const monitorResponseSchema = z.object({
  location: z.object({
    country: z.string(),
    latitude: z.number(),
    longitude: z.number(),
    area_ha: z.number().nullable().optional(),
  }).passthrough(),
  slab_3d: slab3dSchema,
  live_rotation_monitor: z.object({
    t_now_day: z.number(),
    observed_ndvi: z.number().nullable().optional(),
    weather_volatility: z.number(),
    plain_rotations: z.array(liveRotationSchema).default([]),
    easiness_rotations: z.array(liveRotationSchema).default([]),
  }),
});

export const satelliteResponseSchema = z.object({
  location: z.object({
    latitude: z.number(),
    longitude: z.number(),
  }).passthrough(),
  layers: z.array(z.object({
    id: z.string().optional(),
    title: z.string().optional(),
    category: z.string().optional(),
    description: z.string().optional(),
    source: z.string().optional(),
  }).passthrough()).default([]),
  overpass_schedule: z.array(z.object({
    sensor: z.string().optional(),
    platform: z.string().optional(),
    mission: z.string().optional(),
    next_overpass_utc: z.string().optional(),
    revisit_days: z.number().optional(),
    cloud_cover_pct: z.number().nullable().optional(),
    status: z.string().optional(),
  }).passthrough()).default([]),
});

export const climatologyPointSchema = z.object({
  month: z.number(),
  label: z.string(),
  rainfall_mm: z.number(),
  temperature_c: z.number(),
  t_min: z.number(),
  t_max: z.number(),
}).passthrough();

export const climateResponseSchema = z.object({
  location: z.object({
    country: z.string().optional(),
    latitude: z.number(),
    longitude: z.number(),
  }).passthrough(),
  provenance: z.unknown(),
  summary: z.object({
    climatology: z.array(climatologyPointSchema).default([]),
  }).passthrough(),
  suggested_window: z.unknown().optional(),
});

export type MonitorRequestDto = z.infer<typeof monitorRequestSchema>;
export type MonitorResponseDto = z.infer<typeof monitorResponseSchema>;
export type SatelliteResponseDto = z.infer<typeof satelliteResponseSchema>;
export type ClimateResponseDto = z.infer<typeof climateResponseSchema>;
export type Slab3DDto = z.infer<typeof slab3dSchema>;
export type TerrainVertexDto = z.infer<typeof terrainVertexSchema>;
export type SoilHorizonDto = z.infer<typeof soilHorizonSchema>;
export type LiveRotationDto = z.infer<typeof liveRotationSchema>;
export type LiveStateDto = z.infer<typeof liveStateSchema>;
export type UncertaintyConePointDto = z.infer<typeof uncertaintyConePointSchema>;
export type ClimatologyPointDto = z.infer<typeof climatologyPointSchema>;

export type MonitorSummary = {
  locationLabel: string;
  elevationLabel: string;
  slopeLabel: string;
  rootDepthLabel: string;
  ndviLabel: string;
  rawPayloadJson: string;
  slab3d: Slab3DDto;
  liveMonitor: MonitorResponseDto['live_rotation_monitor'];
};

export function mapMonitorResponse(dto: MonitorResponseDto): MonitorSummary {
  const { slab_3d, live_rotation_monitor, location } = dto;
  return {
    locationLabel: `${location.country} · ${formatNumber(location.latitude, 3)}, ${formatNumber(location.longitude, 3)}`,
    elevationLabel: `${formatNumber(slab_3d.terrain_3d_mesh.elevation_m, 0)} m`,
    slopeLabel: `${formatNumber(slab_3d.terrain_3d_mesh.regional_slope_pct, 1)}%`,
    rootDepthLabel: `${formatNumber(slab_3d.active_root_depth_m, 2)} m`,
    ndviLabel: formatNumber(slab_3d.canopy_layer.ndvi_current, 2),
    rawPayloadJson: JSON.stringify({ slab_3d, live_rotation_monitor }, null, 2),
    slab3d: slab_3d,
    liveMonitor: live_rotation_monitor,
  };
}

export type SatelliteOverpassItem = {
  id: string;
  sensor: string;
  timing: string;
  detail: string;
};

export function mapSatelliteResponse(dto: SatelliteResponseDto) {
  const overpasses: SatelliteOverpassItem[] = dto.overpass_schedule.map((item, idx) => {
    const sensor = String(item.sensor ?? item.mission ?? item.platform ?? `Satellite ${idx + 1}`);
    const nextUtc = item.next_overpass_utc ? formatDate(item.next_overpass_utc.slice(0, 10)) : 'Scheduled';
    const parts: string[] = [];
    if (item.revisit_days != null) parts.push(`${item.revisit_days}d revisit`);
    if (item.cloud_cover_pct != null) parts.push(`${formatNumber(item.cloud_cover_pct, 0)}% cloud`);
    if (item.status) parts.push(String(item.status));
    return {
      id: `${sensor}-${idx}`,
      sensor,
      timing: nextUtc,
      detail: parts.join(' · ') || 'Active pass',
    };
  });
  return { layers: dto.layers, overpasses };
}

export function mapClimateResponse(dto: ClimateResponseDto) {
  const climatology = dto.summary.climatology;
  const maxRain = Math.max(1, ...climatology.map((c) => c.rainfall_mm));
  return {
    climatology: climatology.map((c) => ({
      ...c,
      rainPct: Math.round((c.rainfall_mm / maxRain) * 100),
    })),
    suggestedWindow: dto.suggested_window,
  };
}

export function buildGeoBoundary(
  boundary: readonly { latitude: number; longitude: number }[] | undefined,
): Record<string, unknown> | undefined {
  if (!boundary || boundary.length < 3) return undefined;
  const ring = boundary.map((p) => [p.longitude, p.latitude]);
  const first = ring[0];
  const last = ring[ring.length - 1];
  if (first[0] !== last[0] || first[1] !== last[1]) {
    ring.push([first[0], first[1]]);
  }
  return { type: 'Polygon', coordinates: [ring] };
}
