import { router } from 'expo-router';
import { useMemo, useState } from 'react';
import { Platform, Pressable, ScrollView, StyleSheet, View } from 'react-native';
import { useOffline, viewState } from '@/api/query';
import { Feedback } from '@/components/feedback';
import { Chip, Label, Progress, Segmented, Stat, Surface } from '@/components/primitives';
import {
  explainLiveExpiryShift,
  formatExpiryCountdown,
  type ExpiryThresholds,
  type ExpiryUrgency,
} from '@/features/plan/expiryExplain';
import { FlowScreen, go, ScreenScroll } from '@/features/planner/FlowScreen';
import { strings } from '@/i18n/strings';
import { usePlanner } from '@/state/usePlanner';
import { colors, radius, size, space } from '@/theme/tokens';
import { formatDate, formatNumber } from '@/utils/format';
import { tap } from '@/utils/haptics';
import { useClimateData, useMonitor3D, useSatelliteData } from './hooks';
import {
  buildGeoBoundary,
  getSoilTextureHex,
  type ConvergenceStepDto,
  type LiveRotationDto,
  type MoistureFusionDto,
  type MonitorRequestDto,
  type MonitorSummary,
  type Slab3DDto,
} from './model';
import { ChlorophyllTerrainMap } from './ChlorophyllTerrainMap';
import { Slab3DView } from './Slab3DView';

const AMBER = '#F5C451';
const AMBER_FILL = 'rgba(245, 196, 81, 0.14)';
const AMBER_BORDER = 'rgba(245, 196, 81, 0.45)';

function monitorUrgencyDot(urgency: ExpiryUrgency): string {
  if (urgency === 'critical') return colors.danger;
  if (urgency === 'tight') return AMBER;
  return colors.accent;
}

function monitorUrgencyLabel(urgency: ExpiryUrgency): string {
  if (urgency === 'critical') return 'Critical';
  if (urgency === 'tight') return 'Tight';
  return 'Safe';
}

type TabId = 'slab3d' | 'liveState' | 'rawTelemetry';

function SelectChip({
  label,
  active,
  onPress,
}: {
  label: string;
  active: boolean;
  onPress: () => void;
}) {
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ selected: active }}
      onPress={onPress}
      style={({ pressed }) => [
        styles.selectChip,
        active && styles.selectChipActive,
        pressed && styles.pressed,
      ]}
    >
      <Label variant="chip" tone={active ? 'forest950' : 'cream'}>
        {label}
      </Label>
    </Pressable>
  );
}

function compassDirection(dx: number, dy: number): string {
  if (Math.hypot(dx, dy) < 1e-4) return 'Flat';
  const deg = (Math.atan2(dx, -dy) * 180) / Math.PI;
  const dirs = ['N', 'NE', 'E', 'SE', 'S', 'SW', 'W', 'NW'];
  const idx = Math.round(((deg % 360) + 360) % 360 / 45) % 8;
  return dirs[idx];
}

function formatStageName(stage?: string): string {
  if (!stage) return 'Active Canopy';
  return stage.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

type OverpassAcquisition = {
  acquisition_date?: string;
  datetime?: string;
  mission?: string;
  sensor?: string;
};

function formatTimestamp(iso?: string | null): string | null {
  if (!iso || typeof iso !== 'string') return null;
  const parsed = new Date(iso);
  if (Number.isNaN(parsed.getTime())) return null;
  const datePart = formatDate(iso);
  if (iso.includes('T')) {
    const hh = String(parsed.getUTCHours()).padStart(2, '0');
    const mm = String(parsed.getUTCMinutes()).padStart(2, '0');
    return `${datePart} ${hh}:${mm}Z`;
  }
  return datePart;
}

function latestOverpassDate(
  acquisitions?: OverpassAcquisition[] | null,
  missionMatch?: string,
): string | null {
  if (!Array.isArray(acquisitions) || acquisitions.length === 0) return null;
  const needle = missionMatch?.toLowerCase();
  const candidates = acquisitions
    .filter((a) => {
      if (!needle) return true;
      const hay = `${a.mission ?? ''} ${a.sensor ?? ''}`.toLowerCase();
      return hay.includes(needle);
    })
    .map((a) => a.acquisition_date ?? a.datetime ?? '')
    .filter((d) => Boolean(d) && !Number.isNaN(new Date(d).getTime()))
    .sort((a, b) => new Date(b).getTime() - new Date(a).getTime());

  return candidates.length > 0 ? formatTimestamp(candidates[0]) : null;
}

function layerDtLabel(
  layers: Record<string, { dt_clean_days?: number }> | undefined,
  key: string,
): string | null {
  const dt = layers?.[key]?.dt_clean_days;
  return typeof dt === 'number' ? `~${formatNumber(dt, 1)}d cadence` : null;
}

function formatFusionSource(source: string, index: number): string {
  const key = source.trim().toLowerCase();
  if (key === 'fao56_smap_prior' || key.includes('smap') || key.includes('prior')) {
    return 'FAO/SMAP Prior';
  }
  if (key === 'sentinel1_sar' || key.includes('sentinel-1') || key.includes('sentinel1')) {
    return '+Sentinel-1 SAR';
  }
  if (key === 'sentinel2_ndmi' || key.includes('sentinel-2') || key.includes('sentinel2')) {
    return '+Sentinel-2 NDMI';
  }
  const clean = source.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
  return index > 0 && !clean.startsWith('+') ? `+${clean}` : clean;
}

function formatConvergenceChain(steps: readonly ConvergenceStepDto[]): string {
  return steps
    .map((s, idx) => {
      const decimals = Math.abs(s.fused_sigma * 10 - Math.round(s.fused_sigma * 10)) < 0.01 ? 1 : 2;
      return `${s.step}. ${formatFusionSource(s.source, idx)} (±${formatNumber(s.fused_sigma, decimals)}%)`;
    })
    .join(' → ');
}

function Slab3DTab({ summary, isUpgradingFusion = false }: { summary: MonitorSummary; isUpgradingFusion?: boolean }) {
  const { slab3d } = summary;
  const fusion = slab3d.sensor_fusion;
  const moisture3Way: Partial<MoistureFusionDto> = fusion.moisture_fusion_3way ?? {};
  const convergenceSteps =
    fusion.convergence_steps && fusion.convergence_steps.length > 0
      ? fusion.convergence_steps
      : (moisture3Way.convergence_steps ?? []);
  const fusionStage = fusion.fusion_stage ?? moisture3Way.fusion_stage;
  const atm = slab3d.atmosphere_layer as Record<string, unknown>;
  const mesh = slab3d.terrain_3d_mesh;
  const canopy = slab3d.canopy_layer;
  const freqs = slab3d.update_frequencies as Record<string, unknown>;
  const overpasses = (canopy.overpasses ?? {}) as {
    retrieved_at?: string;
    acquisitions?: OverpassAcquisition[];
  };
  const layerFreqs = (freqs.layers ?? {}) as Record<string, { dt_clean_days?: number }>;

  const retrievedLabel =
    formatTimestamp(overpasses.retrieved_at) ??
    formatTimestamp(summary.liveMonitor.plain_rotations[0]?.live_state?.current_date);
  const latestAnyPass = latestOverpassDate(overpasses.acquisitions);
  const moisturePass =
    latestOverpassDate(overpasses.acquisitions, 'smap') ??
    latestOverpassDate(overpasses.acquisitions, 'sentinel-1') ??
    latestAnyPass ??
    retrievedLabel;
  const ecostressPass = latestOverpassDate(overpasses.acquisitions, 'ecostress');
  const s2Pass =
    latestOverpassDate(overpasses.acquisitions, 'sentinel-2') ??
    latestOverpassDate(overpasses.acquisitions, 'hls');
  const ecostressDt = layerDtLabel(layerFreqs, 'ecostress');
  const s2Dt = layerDtLabel(layerFreqs, 'hlsl30') ?? layerDtLabel(layerFreqs, 'sentinel2');
  const atmDate = formatTimestamp(
    typeof atm.observed_at === 'string'
      ? atm.observed_at
      : typeof atm.date === 'string'
        ? atm.date
        : overpasses.retrieved_at,
  );

  const ndvi = canopy.ndvi_current;
  const isBareSoil = canopy.is_bare_soil ?? ndvi < 0.2;
  const deltaT = canopy.ecostress_thermal_stress_delta_c;
  const cloudPct = typeof freqs.cloud_cover_pct === 'number' ? freqs.cloud_cover_pct : null;
  const areaLabel =
    slab3d.location.area_ha != null
      ? `${formatNumber(slab3d.location.area_ha, 1)} ha`
      : mesh.area_km2 != null
        ? `${formatNumber(mesh.area_km2, 2)} km²`
        : strings.noValue;

  // Compute 10m field moisture & pooling breakdown from vertices
  const verts = mesh.vertices;
  const highPool = verts.filter((v) => v.pooling_risk === 'high').length;
  const modPool = verts.filter((v) => v.pooling_risk === 'moderate').length;
  const moistVals = verts
    .map((v) => v.downscaled_moisture_pct)
    .filter((m): m is number => typeof m === 'number');
  const minMoist = moistVals.length > 0 ? Math.min(...moistVals) : null;
  const maxMoist = moistVals.length > 0 ? Math.max(...moistVals) : null;
  const fusedSigma = typeof moisture3Way.fused_sigma === 'number' ? moisture3Way.fused_sigma : null;

  // Runoff direction
  const rdx = mesh.runoff_vector?.dx ?? 0;
  const rdy = mesh.runoff_vector?.dy ?? 0;
  const runoffDir = compassDirection(rdx, rdy);

  // Daily water balance (Rain - ET0)
  const rainMm = typeof atm.rainfall_mm_day === 'number' ? atm.rainfall_mm_day : null;
  const et0Mm = typeof atm.et0_mm_day === 'number' ? atm.et0_mm_day : null;
  const tempC = typeof atm.temperature_c === 'number' ? atm.temperature_c : null;
  const vpdKpa = typeof atm.vpd_kpa === 'number' ? atm.vpd_kpa : null;
  const netWaterMm = rainMm != null && et0Mm != null ? rainMm - et0Mm : null;

  // Thermal stress classification
  const stressLevel =
    deltaT == null ? 'Unknown' : deltaT >= 3.0 ? 'High' : deltaT >= 1.5 ? 'Moderate' : 'Low';

  return (
    <View style={styles.sectionStack}>
      {isUpgradingFusion && (
        <Surface kind="highlight" rounding={radius.tile} style={styles.cardPad}>
          <View style={styles.rowBetween}>
            <Label variant="caption" tone="accent">LIVE PROGRESSIVE FUSION</Label>
            <Chip label="Stage 0 Prior · Syncing Satellites…" accent />
          </View>
        </Surface>
      )}

      <Slab3DView slab={slab3d} />

      {/* Parcel Footprint & Satellite Revisit */}
      <Surface kind="card" rounding={radius.card} style={styles.cardPad}>
        <View style={styles.rowBetween}>
          <Label variant="tag" tone="sage">PARCEL & SATELLITE CADENCE</Label>
          <Chip label={`NDVI ${formatNumber(ndvi, 2)}`} accent />
        </View>
        <Label variant="caption" tone="muted">
          {retrievedLabel ? `Updated ${retrievedLabel}` : 'Updated Live'}
        </Label>
        <View style={styles.statRow}>
          <Stat tile label="Field Area" value={areaLabel} style={styles.flexOne} />
          <Stat
            tile
            label="Cloud Cover"
            value={cloudPct != null ? `${formatNumber(cloudPct, 0)}%` : strings.noValue}
            style={styles.flexOne}
          />
          <Stat
            tile
            label="Revisit"
            value={
              fusion.combined_parcel_dt_days != null
                ? `${formatNumber(fusion.combined_parcel_dt_days, 2)}d`
                : strings.noValue
            }
            accent
            style={styles.flexOne}
          />
        </View>
      </Surface>

      {/* Field Moisture & Pooling Zones */}
      <Surface kind="card" rounding={radius.card} style={styles.cardPad}>
        <View style={styles.rowBetween}>
          <Label variant="tag" tone="sage">FIELD MOISTURE & POOLING</Label>
          <Label variant="caption" tone="accent">
            {moisturePass ? `Pass ${moisturePass}` : ''}
            {moisturePass && fusion.combined_parcel_dt_days != null ? ' · ' : ''}
            {fusion.combined_parcel_dt_days != null
              ? `Revisit ${formatNumber(fusion.combined_parcel_dt_days, 2)}d`
              : ''}
          </Label>
        </View>
        <View style={styles.statRow}>
          <Stat
            tile
            label="Soil Moisture"
            value={
              fusion.parcel_mean_moisture_conserved_pct != null
                ? `${formatNumber(fusion.parcel_mean_moisture_conserved_pct, 1)}%`
                : strings.noValue
            }
            accent
            style={styles.flexOne}
          />
          <Stat
            tile
            label="Accuracy"
            value={fusedSigma != null ? `±${formatNumber(fusedSigma, 2)}%` : '±2.92%'}
            style={styles.flexOne}
          />
          <Stat
            tile
            label="Pooling Risk"
            value={`${highPool} High · ${modPool} Mod`}
            style={styles.flexOne}
          />
        </View>
        {minMoist != null && maxMoist != null && (
          <Label variant="caption" tone="sage">
            Ridges {formatNumber(minMoist, 1)}% → Valleys {formatNumber(maxMoist, 1)}% vol
          </Label>
        )}
        {(convergenceSteps.length > 0 || isUpgradingFusion || fusionStage) && (
          <Surface kind="strong" rounding={radius.tile} style={styles.fusionBox}>
            <View style={styles.rowBetween}>
              <Label variant="caption" tone="sage">FUSION CONVERGENCE</Label>
              <Chip
                label={
                  isUpgradingFusion
                    ? 'Upgrading to Full Fusion'
                    : formatStageName(fusionStage ?? 'stage_2_full_fusion')
                }
                accent={isUpgradingFusion}
              />
            </View>
            {convergenceSteps.length > 0 && (
              <Label variant="caption" tone="cream">
                {formatConvergenceChain(convergenceSteps)}
              </Label>
            )}
          </Surface>
        )}
      </Surface>

      {/* Heat Stress & Nitrogen */}
      <View style={styles.horizonGrid}>
        <Surface kind="card" rounding={radius.tile} style={styles.horizonCard}>
          <Label variant="tag" tone="sage">HEAT STRESS (ΔT)</Label>
          <Stat
            label={`${stressLevel} Stress`}
            value={deltaT != null ? `+${formatNumber(deltaT, 1)} °C` : strings.noValue}
            accent={stressLevel === 'High'}
          />
          <Label variant="caption" tone="muted" numberOfLines={1}>
            ECOSTRESS · {ecostressPass ?? ecostressDt ?? 'Cached'}
          </Label>
        </Surface>

        <Surface kind="card" rounding={radius.tile} style={styles.horizonCard}>
          <Label variant="tag" tone="sage">NITROGEN (NDRE)</Label>
          <Stat
            label="Canopy Check"
            value={ndvi >= 0.5 ? 'Red-Edge Active' : 'Early Canopy'}
            accent={ndvi >= 0.5}
          />
          <Label variant="caption" tone="muted" numberOfLines={1}>
            Sentinel-2 · {s2Pass ?? s2Dt ?? 'Cached'}
          </Label>
        </Surface>
      </View>

      {/* Slope, Runoff & Bunding */}
      <Surface kind="card" rounding={radius.card} style={styles.cardPad}>
        <View style={styles.rowBetween}>
          <Label variant="tag" tone="sage">SLOPE & RUNOFF</Label>
          <Label variant="caption" tone="accent">
            Drains {runoffDir}
          </Label>
        </View>
        <Label variant="caption" tone="muted">
          GLO-30 DEM · Static terrain
        </Label>
        <View style={styles.statRow}>
          <Stat
            tile
            label="Elevation"
            value={
              mesh.elevation_min_m != null && mesh.elevation_max_m != null
                ? `${formatNumber(mesh.elevation_min_m, 0)}–${formatNumber(mesh.elevation_max_m, 0)} m`
                : summary.elevationLabel
            }
            style={styles.flexOne}
          />
          <Stat tile label="Slope" value={summary.slopeLabel} style={styles.flexOne} />
          <Stat
            tile
            label="Drainage"
            value={formatStageName(mesh.suggested_drainage_prior)}
            accent
            style={styles.flexOne}
          />
        </View>
      </Surface>

      {/* Root-Zone Soil Depths (0-100 cm) */}
      <View style={styles.sectionHeader}>
        <Label variant="tag" tone="sage">{strings.soilHorizons}</Label>
        <Label variant="caption" tone="muted">
          {isBareSoil ? 'SWIR pH · Active' : `Root zone ${summary.rootDepthLabel}`} · SoilGrids 250m Static
        </Label>
      </View>

      <View style={styles.horizonGrid}>
        {slab3d.soil_3d_horizons.map((h) => {
          const soilHex = getSoilTextureHex(h.usda_texture);
          return (
            <Surface
              key={h.depth_label}
              kind={h.roots_present ? 'selected' : 'card'}
              rounding={radius.tile}
              style={[styles.horizonCard, { borderLeftWidth: 4, borderLeftColor: soilHex }]}
            >
              <View style={styles.rowBetween}>
                <Label variant="button" tone="cream">{h.depth_label}</Label>
                <Chip
                  label={h.roots_present ? 'Roots' : 'Subsoil'}
                  accent={h.roots_present}
                />
              </View>
              <View style={styles.horizonStats}>
                <Stat label="pH" value={formatNumber(h.ph, 2)} />
                <Stat label="Moisture" value={`${formatNumber(h.volumetric_moisture_pct, 1)}%`} accent={h.roots_present} />
              </View>
              {h.hydraulics?.field_capacity_vol_pct != null && h.hydraulics?.wilting_point_vol_pct != null && (
                <Label variant="caption" tone="muted" numberOfLines={1}>
                  FC {formatNumber(h.hydraulics.field_capacity_vol_pct, 1)}% · WP {formatNumber(h.hydraulics.wilting_point_vol_pct, 1)}%
                </Label>
              )}
              {h.usda_texture && (
                <View style={styles.textureRow}>
                  <View style={[styles.textureSwatch, { backgroundColor: soilHex }]} />
                  <Label variant="caption" tone="sage" numberOfLines={1}>
                    {h.usda_texture}
                  </Label>
                </View>
              )}
            </Surface>
          );
        })}
      </View>

      {/* Daily Weather & Water Demand */}
      <Surface kind="card" rounding={radius.card} style={styles.cardPad}>
        <View style={styles.rowBetween}>
          <Label variant="tag" tone="sage">WATER BALANCE</Label>
          {netWaterMm != null && (
            <Label variant="caption" tone={netWaterMm >= 0 ? 'accent' : 'cream'}>
              Net {netWaterMm >= 0 ? '+' : ''}{formatNumber(netWaterMm, 2)} mm/d
            </Label>
          )}
        </View>
        <Label variant="caption" tone="muted">
          Daily · {atmDate ?? 'Latest synoptic'}
        </Label>
        <View style={styles.statRow}>
          <Stat tile label="Rain" value={rainMm != null ? `${formatNumber(rainMm, 1)} mm/d` : strings.noValue} style={styles.flexOne} />
          <Stat tile label="ET₀ Loss" value={et0Mm != null ? `${formatNumber(et0Mm, 2)} mm/d` : strings.noValue} accent style={styles.flexOne} />
          <Stat tile label="Temp / VPD" value={tempC != null ? `${formatNumber(tempC, 1)}°C · ${vpdKpa != null ? formatNumber(vpdKpa, 2) : '-'}kPa` : strings.noValue} style={styles.flexOne} />
        </View>
      </Surface>
    </View>
  );
}

function LiveGrowthTab({
  slab,
  rotations,
  selectedId,
  thresholds,
  onSelect,
  onOpenThresholds,
}: {
  slab: Slab3DDto;
  rotations: LiveRotationDto[];
  selectedId: string | null;
  thresholds: ExpiryThresholds;
  onSelect: (id: string) => void;
  onOpenThresholds: () => void;
}) {
  if (!rotations.length) {
    return (
      <Surface kind="card" rounding={radius.card} style={styles.cardPad}>
        <Label variant="body" tone="sage">
          No live rotation timelines available for this location and date.
        </Label>
      </Surface>
    );
  }

  const active = rotations.find((r) => r.id === selectedId) ?? rotations[0];
  const ls = active.live_state;
  const lag = ls.growth_lag_days;
  const lagLabel = lag === 0 ? 'On schedule' : lag > 0 ? `${lag}d behind` : `${Math.abs(lag)}d ahead`;
  const shiftEval = explainLiveExpiryShift(ls, thresholds);
  const safeCountdown = formatExpiryCountdown(ls.days_until_safe_expiry, 'safe');
  const hardCountdown = formatExpiryCountdown(ls.days_until_hard_expiry, 'hard');

  return (
    <View style={styles.sectionStack}>
      {rotations.length > 1 && (
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.chipRow}>
          {rotations.map((rot) => (
            <SelectChip
              key={rot.id}
              label={rot.name}
              active={rot.id === active.id}
              onPress={() => onSelect(rot.id)}
            />
          ))}
        </ScrollView>
      )}

      <Surface kind="highlight" rounding={radius.card} style={styles.cardPad}>
        <View style={styles.rowBetween}>
          <View style={styles.flexOne}>
            <Label variant="cardTitle" tone="cream">{active.name}</Label>
            <Label variant="caption" tone="sage">
              {formatDate(ls.current_date)} · Day {ls.t_now_day}
            </Label>
          </View>
          <Chip label={ls.active_stage} accent />
        </View>

        <View style={styles.statRow}>
          <Stat tile label="Growth Lag" value={lagLabel} accent={lag <= 0} style={styles.flexOne} />
          <Stat tile label="Expected NDVI" value={formatNumber(ls.expected_ndvi, 2)} style={styles.flexOne} />
          <Stat
            tile
            label="Observed NDVI"
            value={ls.observed_ndvi != null ? formatNumber(ls.observed_ndvi, 2) : 'Auto'}
            accent={ls.observed_ndvi != null}
            style={styles.flexOne}
          />
        </View>

        <View style={styles.statRow}>
          <Stat
            tile
            label="Safe Expiry"
            value={ls.safe_expiry_date ? `${formatDate(ls.safe_expiry_date)} (${safeCountdown})` : strings.noValue}
            style={styles.flexOne}
          />
          <Stat
            tile
            label="Hard Expiry"
            value={ls.hard_expiry_date ? `${formatDate(ls.hard_expiry_date)} (${hardCountdown})` : strings.noValue}
            style={styles.flexOne}
          />
        </View>

        <View style={styles.rowBetween}>
          <Label variant="caption" tone="sage">Harvest Window Uncertainty (σ)</Label>
          <Label variant="button" tone="accent">±{formatNumber(ls.sigma_at_harvest_days, 1)} days</Label>
        </View>
      </Surface>

      {/* Live Expiry Shift Explained */}
      <Surface
        kind={shiftEval.urgency === 'critical' ? 'danger' : 'card'}
        rounding={radius.card}
        style={[
          styles.cardPad,
          shiftEval.urgency === 'tight' && styles.shiftBoxTight,
          shiftEval.urgency === 'safe' && styles.shiftBoxSafe,
        ]}
      >
        <View style={styles.rowBetween}>
          <View style={styles.shiftTitleRow}>
            <View style={[styles.shiftDot, { backgroundColor: monitorUrgencyDot(shiftEval.urgency) }]} />
            <Label variant="tag" tone="sage">{strings.liveExpiryShiftTitle.toUpperCase()}</Label>
          </View>
          <View
            style={[
              styles.shiftUrgencyPill,
              shiftEval.urgency === 'critical'
                ? styles.shiftUrgencyCritical
                : shiftEval.urgency === 'tight'
                  ? styles.shiftUrgencyTight
                  : styles.shiftUrgencySafe,
            ]}
          >
            <Label
              variant="smallBold"
              tone={shiftEval.urgency === 'critical' ? 'danger' : shiftEval.urgency === 'safe' ? 'accent' : 'cream'}
            >
              {monitorUrgencyLabel(shiftEval.urgency)}
            </Label>
          </View>
        </View>

        <Label variant="button" tone="cream">{shiftEval.headline}</Label>

        <View style={styles.chipRowWrap}>
          <View style={styles.shiftMetaPill}>
            <Label variant="label" tone="cream">{shiftEval.lagSummary}</Label>
          </View>
          <View style={styles.shiftMetaPill}>
            <Label variant="label" tone="accent">{shiftEval.volatilitySummary}</Label>
          </View>
        </View>

        <Label variant="caption" tone="cream">{shiftEval.explanation}</Label>

        <View style={styles.shiftThresholdFooter}>
          <Label variant="label" tone="sage" style={styles.flexOne}>
            Active Account & Farms thresholds: {thresholds.expirySafetyDays}d safety buffer · {thresholds.collisionThresholdPct}% collision alert · σ={thresholds.weatherVolatility.toFixed(2)}
          </Label>
          <Pressable
            accessibilityRole="button"
            accessibilityLabel={`${strings.adjustThresholds} in Account and Farms`}
            onPress={onOpenThresholds}
            style={styles.tuneThresholdBtn}
          >
            <Label variant="smallBold" tone="accent">{strings.adjustThresholds} →</Label>
          </Pressable>
        </View>
      </Surface>

      <ChlorophyllTerrainMap slab={slab} liveState={ls} />
    </View>
  );
}

function RawTelemetryTab({
  summary,
  latitude,
  longitude,
  country,
  boundary,
  areaHa,
}: {
  summary: MonitorSummary;
  latitude: number;
  longitude: number;
  country: string;
  boundary?: Record<string, unknown>;
  areaHa: number | null;
}) {
  const [showJson, setShowJson] = useState(false);

  const climateCtx = useMemo(
    () => ({ country, latitude, longitude }),
    [country, latitude, longitude],
  );
  const satCtx = useMemo(
    () => ({ country, latitude, longitude, boundary, area_ha: areaHa }),
    [country, latitude, longitude, boundary, areaHa],
  );

  const climate = useClimateData(climateCtx);
  const satellite = useSatelliteData(satCtx);

  const atm = summary.slab3d.atmosphere_layer;
  const canopy = summary.slab3d.canopy_layer;
  const freq = summary.slab3d.update_frequencies;
  const stack = summary.slab3d.sensor_fusion.stack;

  return (
    <View style={styles.sectionStack}>
      <Surface kind="card" rounding={radius.card} style={styles.cardPad}>
        <Label variant="tag" tone="sage">ATMOSPHERE & CANOPY LAYER</Label>
        <View style={styles.statRow}>
          {Object.entries(atm).slice(0, 4).map(([k, v]) => (
            <Stat
              key={k}
              tile
              compact
              label={k.replace(/_/g, ' ')}
              value={typeof v === 'number' ? formatNumber(v, 1) : String(v ?? strings.noValue)}
              style={styles.flexOne}
            />
          ))}
        </View>
        <View style={styles.statRow}>
          <Stat tile label="Canopy NDVI" value={formatNumber(canopy.ndvi_current, 3)} accent style={styles.flexOne} />
          <Stat
            tile
            label="Thermal Stress Δ"
            value={
              canopy.ecostress_thermal_stress_delta_c != null
                ? `${formatNumber(canopy.ecostress_thermal_stress_delta_c, 2)} °C`
                : strings.noValue
            }
            style={styles.flexOne}
          />
          <Stat tile label="Bare Soil" value={canopy.is_bare_soil ? 'Yes' : 'No'} style={styles.flexOne} />
        </View>
      </Surface>

      <Surface kind="card" rounding={radius.card} style={styles.cardPad}>
        <Label variant="tag" tone="sage">SENSOR FUSION STACK</Label>
        <View style={styles.chipRowWrap}>
          {stack.map((item) => (
            <Chip key={item} label={item} />
          ))}
        </View>
        <Label variant="tag" tone="sage" style={styles.topGap}>UPDATE FREQUENCIES</Label>
        <View style={styles.kvList}>
          {Object.entries(freq).map(([k, v]) => (
            <View key={k} style={styles.rowBetween}>
              <Label variant="caption" tone="sage">{k.replace(/_/g, ' ')}</Label>
              <Label variant="caption" tone="cream">
                {typeof v === 'number' ? formatNumber(v, 2) : String(v ?? strings.noValue)}
              </Label>
            </View>
          ))}
        </View>
      </Surface>

      <Surface kind="card" rounding={radius.card} style={styles.cardPad}>
        <Label variant="tag" tone="sage">{strings.climatology} (NASA POWER)</Label>
        {climate.isPending ? (
          <Label variant="caption" tone="muted">{strings.loading}...</Label>
        ) : climate.data?.climatology.length ? (
          <View style={styles.climList}>
            {climate.data.climatology.map((m) => (
              <View key={m.month} style={styles.climRow}>
                <Label variant="caption" tone="cream" style={styles.climMonth}>{m.label}</Label>
                <View style={styles.climBarWrap}>
                  <Progress value={m.rainPct} label={`${m.label} rainfall`} />
                </View>
                <Label variant="caption" tone="sage" style={styles.climVal}>
                  {formatNumber(m.rainfall_mm, 0)}mm · {formatNumber(m.temperature_c, 0)}°C
                </Label>
              </View>
            ))}
          </View>
        ) : (
          <Label variant="caption" tone="muted">Climatology unavailable.</Label>
        )}
      </Surface>

      <Surface kind="card" rounding={radius.card} style={styles.cardPad}>
        <Label variant="tag" tone="sage">{strings.overpasses}</Label>
        {satellite.isPending ? (
          <Label variant="caption" tone="muted">{strings.loading}...</Label>
        ) : satellite.data?.overpasses.length ? (
          <View style={styles.kvList}>
            {satellite.data.overpasses.map((op) => (
              <View key={op.id} style={styles.overpassRow}>
                <View style={styles.flexOne}>
                  <Label variant="button" tone="cream">{op.sensor}</Label>
                  <Label variant="caption" tone="sage">{op.detail}</Label>
                </View>
                <Chip label={op.timing} />
              </View>
            ))}
          </View>
        ) : (
          <Label variant="caption" tone="muted">No upcoming overpass data.</Label>
        )}
      </Surface>

      <Surface kind="card" rounding={radius.card} style={styles.cardPad}>
        <View style={styles.rowBetween}>
          <Label variant="tag" tone="sage">RAW JSON PAYLOAD</Label>
          <SelectChip
            label={showJson ? 'Hide JSON' : 'Show JSON'}
            active={showJson}
            onPress={() => setShowJson((v) => !v)}
          />
        </View>
        {showJson && (
          <Surface kind="strong" rounding={radius.tile} style={styles.codeBox}>
            <ScrollView horizontal showsHorizontalScrollIndicator>
              <Label style={styles.codeText} tone="cream">
                {summary.rawPayloadJson}
              </Label>
            </ScrollView>
          </Surface>
        )}
      </Surface>
    </View>
  );
}

export default function MonitorScreen() {
  const [tab, setTab] = useState<TabId>('slab3d');

  const countryId = usePlanner((s) => s.countryId);
  const latitude = usePlanner((s) => s.latitude);
  const longitude = usePlanner((s) => s.longitude);
  const boundary = usePlanner((s) => s.boundary);
  const areaHa = usePlanner((s) => s.areaHa);
  const sowingDate = usePlanner((s) => s.sowingDate);
  const irrigation = usePlanner((s) => s.irrigation);
  const tNowDay = usePlanner((s) => s.tNowDay);
  const observedNdvi = usePlanner((s) => s.observedNdvi);
  const weatherVolatility = usePlanner((s) => s.weatherVolatility);
  const expirySafetyDays = usePlanner((s) => s.expirySafetyDays);
  const collisionThresholdPct = usePlanner((s) => s.collisionThresholdPct);
  const selectedRotationId = usePlanner((s) => s.selectedRotationId);
  const selectRotation = usePlanner((s) => s.selectRotation);
  const reset = usePlanner((s) => s.reset);

  const thresholds = useMemo<ExpiryThresholds>(
    () => ({ expirySafetyDays, collisionThresholdPct, weatherVolatility }),
    [expirySafetyDays, collisionThresholdPct, weatherVolatility],
  );

  const geoBoundary = useMemo(() => buildGeoBoundary(boundary), [boundary]);

  const effectiveCountry = countryId || 'LK';
  const request: MonitorRequestDto = useMemo(() => ({
    country: effectiveCountry,
    latitude,
    longitude,
    boundary: geoBoundary,
    area_ha: areaHa,
    start_date: sowingDate,
    irrigation,
    t_now_day: tNowDay,
    observed_ndvi: observedNdvi,
    weather_volatility: weatherVolatility,
    max_sequences: 6,
  }), [effectiveCountry, latitude, longitude, geoBoundary, areaHa, sowingDate, irrigation, tNowDay, observedNdvi, weatherVolatility]);

  const monitor = useMonitor3D(request);
  const offline = useOffline();
  const state = viewState(monitor, offline, monitor.data != null);

  const tabs = [
    { id: 'slab3d', label: strings.slab3d },
    { id: 'liveState', label: strings.liveState },
    { id: 'rawTelemetry', label: strings.rawTelemetry },
  ] as const;

  return (
    <FlowScreen
      step={2}
      standaloneTitle={strings.monitorTitle}
      standaloneActive
      action={strings.restart}
      onNext={() => { reset(); go(1); }}
    >
      {(inset) => (
        <ScreenScroll inset={inset} contentContainerStyle={styles.scrollContent}>
          <Segmented
            items={tabs}
            value={tab}
            onChange={(next) => setTab(next as TabId)}
          />

          <Feedback
            state={state}
            layout="plan"
            onRetry={() => { void monitor.refetch(); }}
          >
            {monitor.data && (
              <>
                {tab === 'slab3d' && <Slab3DTab summary={monitor.data} isUpgradingFusion={monitor.isUpgradingFusion} />}
                {tab === 'liveState' && (
                  <LiveGrowthTab
                    slab={monitor.data.slab3d}
                    rotations={monitor.data.liveMonitor.plain_rotations}
                    selectedId={selectedRotationId}
                    thresholds={thresholds}
                    onSelect={(id) => {
                      tap();
                      selectRotation(id);
                    }}
                    onOpenThresholds={() => {
                      tap();
                      router.push('/login');
                    }}
                  />
                )}
                {tab === 'rawTelemetry' && (
                  <RawTelemetryTab
                    summary={monitor.data}
                    latitude={latitude}
                    longitude={longitude}
                    country={countryId}
                    boundary={geoBoundary}
                    areaHa={areaHa}
                  />
                )}
              </>
            )}
          </Feedback>
        </ScreenScroll>
      )}
    </FlowScreen>
  );
}

const styles = StyleSheet.create({
  scrollContent: { gap: space.md },
  controlsCard: { padding: space.md, gap: space.sm },
  controlGroup: { gap: space.xs },
  chipRow: { flexDirection: 'row', gap: space.xs, paddingRight: space.sm },
  chipRowWrap: { flexDirection: 'row', flexWrap: 'wrap', gap: space.xs },
  selectChip: {
    paddingHorizontal: space.md,
    paddingVertical: space.xs + 2,
    borderRadius: radius.pill,
    backgroundColor: colors.chip,
    borderWidth: 1,
    borderColor: colors.border,
  },
  selectChipActive: {
    backgroundColor: colors.accent,
    borderColor: colors.accent,
  },
  pressed: { opacity: 0.72 },
  sectionStack: { gap: space.md },
  sectionHeader: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', paddingHorizontal: space.xs },
  horizonGrid: { flexDirection: 'row', flexWrap: 'wrap', gap: space.sm },
  horizonCard: { width: '48%', flexGrow: 1, padding: space.md, gap: space.sm },
  horizonStats: { flexDirection: 'row', justifyContent: 'space-between', gap: space.sm },
  textureRow: { flexDirection: 'row', alignItems: 'center', gap: space.xs },
  textureSwatch: { width: 10, height: 10, borderRadius: 3 },
  cardPad: { padding: space.md, gap: space.sm },
  fusionBox: { padding: space.sm, gap: space.xs },
  rowBetween: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: space.sm },
  statRow: { flexDirection: 'row', flexWrap: 'wrap', gap: space.sm },
  flexOne: { flex: 1, minWidth: 92 },
  topGap: { marginTop: space.xs },
  kvList: { gap: space.xs },
  climList: { gap: space.xs },
  climRow: { flexDirection: 'row', alignItems: 'center', gap: space.sm },
  climMonth: { width: 32 },
  climBarWrap: { flex: 1 },
  climVal: { width: 92, textAlign: 'right' },
  overpassRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: space.sm,
    paddingVertical: space.xs,
    borderBottomWidth: 1,
    borderBottomColor: colors.border,
  },
  codeBox: {
    padding: space.md,
    backgroundColor: colors.forest950,
    maxHeight: 320,
  },
  codeText: {
    fontFamily: Platform.OS === 'ios' ? 'Menlo' : 'monospace',
    fontSize: 11,
    lineHeight: 16,
  },
  shiftBoxSafe: { borderColor: colors.accentBorder },
  shiftBoxTight: { backgroundColor: AMBER_FILL, borderColor: AMBER_BORDER },
  shiftTitleRow: { flexDirection: 'row', alignItems: 'center', gap: space.xs },
  shiftDot: { width: 8, height: 8, borderRadius: 4 },
  shiftUrgencyPill: {
    paddingHorizontal: space.sm,
    paddingVertical: space.xxs + 1,
    borderRadius: radius.pill,
    borderWidth: size.hairline,
  },
  shiftUrgencySafe: { backgroundColor: colors.highlight, borderColor: colors.accentBorder },
  shiftUrgencyTight: { backgroundColor: AMBER_FILL, borderColor: AMBER_BORDER },
  shiftUrgencyCritical: { backgroundColor: colors.dangerFill, borderColor: colors.dangerBorder },
  shiftMetaPill: {
    paddingHorizontal: space.sm,
    paddingVertical: space.xs,
    borderRadius: radius.pill,
    backgroundColor: colors.innerDark,
    borderWidth: size.hairline,
    borderColor: colors.border,
  },
  shiftThresholdFooter: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    flexWrap: 'wrap',
    gap: space.sm,
    paddingTop: space.xs,
    borderTopWidth: size.hairline,
    borderTopColor: colors.border,
  },
  tuneThresholdBtn: {
    paddingHorizontal: space.md,
    paddingVertical: space.xs,
    borderRadius: radius.pill,
    backgroundColor: colors.highlight,
    borderWidth: size.hairline,
    borderColor: colors.accentBorder,
  },
});
