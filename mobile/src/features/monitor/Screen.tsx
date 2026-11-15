import { useMemo, useState } from 'react';
import { Platform, Pressable, ScrollView, StyleSheet, View } from 'react-native';
import Svg, { Line, Polygon, Polyline } from 'react-native-svg';
import { useOffline, viewState } from '@/api/query';
import { Feedback } from '@/components/feedback';
import { Chip, Label, Progress, Segmented, Stat, Surface } from '@/components/primitives';
import { FlowScreen, go, ScreenScroll } from '@/features/planner/FlowScreen';
import { strings } from '@/i18n/strings';
import { usePlanner } from '@/state/usePlanner';
import { colors, radius, space } from '@/theme/tokens';
import { formatDate, formatNumber } from '@/utils/format';
import { useClimateData, useMonitor3D, useSatelliteData } from './hooks';
import {
  buildGeoBoundary,
  getSoilTextureHex,
  type LiveRotationDto,
  type MonitorRequestDto,
  type MonitorSummary,
  type UncertaintyConePointDto,
} from './model';
import { Slab3DView } from './Slab3DView';

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

function Slab3DTab({ summary }: { summary: MonitorSummary }) {
  const { slab3d, liveMonitor } = summary;
  const fusion = slab3d.sensor_fusion;
  const moisture3Way = fusion.moisture_fusion_3way ?? {};
  const atm = slab3d.atmosphere_layer as Record<string, unknown>;
  const mesh = slab3d.terrain_3d_mesh;
  const canopy = slab3d.canopy_layer;

  const topLive = liveMonitor.plain_rotations[0]?.live_state;
  const ndvi = canopy.ndvi_current;
  const isBareSoil = canopy.is_bare_soil ?? ndvi < 0.2;
  const deltaT = canopy.ecostress_thermal_stress_delta_c;

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
      <Slab3DView slab={slab3d} />

      {/* Crop Health, Growth Stage & Harvest Timing */}
      <Surface kind="card" rounding={radius.card} style={styles.cardPad}>
        <View style={styles.rowBetween}>
          <Label variant="tag" tone="sage">CROP & HARVEST TIMING</Label>
          <Chip
            label={topLive ? formatStageName(topLive.active_stage) : `NDVI ${formatNumber(ndvi, 2)}`}
            accent
          />
        </View>
        <View style={styles.statRow}>
          <Stat
            tile
            label="Growth Lag"
            value={
              topLive
                ? `${topLive.growth_lag_days > 0 ? '+' : ''}${topLive.growth_lag_days}d`
                : '0d'
            }
            style={styles.flexOne}
          />
          <Stat
            tile
            label="Root Depth"
            value={summary.rootDepthLabel}
            accent
            style={styles.flexOne}
          />
          <Stat
            tile
            label="Harvest ±σ"
            value={topLive ? `±${formatNumber(topLive.sigma_at_harvest_days, 1)}d` : strings.noValue}
            style={styles.flexOne}
          />
        </View>
        {topLive?.safe_expiry_date && (
          <Label variant="caption" tone="sage">
            Sow-by {formatDate(topLive.safe_expiry_date)} · Hard expiry {topLive.hard_expiry_date ? formatDate(topLive.hard_expiry_date) : strings.noValue}
          </Label>
        )}
      </Surface>

      {/* Field Moisture & Pooling Zones */}
      <Surface kind="card" rounding={radius.card} style={styles.cardPad}>
        <View style={styles.rowBetween}>
          <Label variant="tag" tone="sage">FIELD MOISTURE & POOLING</Label>
          {fusion.combined_parcel_dt_days != null && (
            <Label variant="caption" tone="accent">
              Revisit {formatNumber(fusion.combined_parcel_dt_days, 2)}d
            </Label>
          )}
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
        </Surface>

        <Surface kind="card" rounding={radius.tile} style={styles.horizonCard}>
          <Label variant="tag" tone="sage">NITROGEN (NDRE)</Label>
          <Stat
            label="Canopy Check"
            value={ndvi >= 0.5 ? 'Red-Edge Active' : 'Early Canopy'}
            accent={ndvi >= 0.5}
          />
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
          {isBareSoil ? 'Bare-soil pH active' : `Root zone ${summary.rootDepthLabel}`}
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
        <View style={styles.statRow}>
          <Stat tile label="Rain" value={rainMm != null ? `${formatNumber(rainMm, 1)} mm/d` : strings.noValue} style={styles.flexOne} />
          <Stat tile label="ET₀ Loss" value={et0Mm != null ? `${formatNumber(et0Mm, 2)} mm/d` : strings.noValue} accent style={styles.flexOne} />
          <Stat tile label="Temp / VPD" value={tempC != null ? `${formatNumber(tempC, 1)}°C · ${vpdKpa != null ? formatNumber(vpdKpa, 2) : '-'}kPa` : strings.noValue} style={styles.flexOne} />
        </View>
      </Surface>
    </View>
  );
}

function UncertaintyConeChart({ series, tNowDay }: { series: UncertaintyConePointDto[]; tNowDay: number }) {
  const [width, setWidth] = useState(320);
  const height = 170;
  const padL = 28;
  const padR = 14;
  const padT = 14;
  const padB = 26;

  if (series.length < 2) {
    return (
      <Surface kind="card" rounding={radius.tile} style={styles.cardPad}>
        <Label variant="caption" tone="muted">No uncertainty cone series available for this rotation.</Label>
      </Surface>
    );
  }

  const maxDay = Math.max(1, ...series.map((p) => p.day));
  const plotW = Math.max(40, width - padL - padR);
  const plotH = height - padT - padB;

  const toX = (day: number) => padL + (day / maxDay) * plotW;
  const toY = (pct: number) => padT + (1 - Math.max(0, Math.min(100, pct)) / 100) * plotH;

  const optPoints = series.map((p) => `${toX(p.day).toFixed(1)},${toY(p.optimistic_bound_pct).toFixed(1)}`);
  const pessReversed = [...series]
    .reverse()
    .map((p) => `${toX(p.day).toFixed(1)},${toY(p.pessimistic_bound_pct).toFixed(1)}`);
  const conePolygon = [...optPoints, ...pessReversed].join(' ');
  const nominalLine = series
    .map((p) => `${toX(p.day).toFixed(1)},${toY(p.nominal_progress_pct).toFixed(1)}`)
    .join(' ');
  const nowX = toX(Math.min(maxDay, tNowDay));

  return (
    <Surface kind="card" rounding={radius.card} style={styles.cardPad}>
      <View style={styles.rowBetween}>
        <Label variant="tag" tone="sage">GROWTH UNCERTAINTY CONE</Label>
        <Label variant="caption" tone="accent">Day {tNowDay} / {maxDay}</Label>
      </View>
      <View
        style={styles.chartBox}
        onLayout={(e) => {
          if (e.nativeEvent.layout.width > 0) setWidth(e.nativeEvent.layout.width);
        }}
      >
        <Svg width={width} height={height}>
          {[0, 50, 100].map((pct) => (
            <Line
              key={pct}
              x1={padL}
              y1={toY(pct)}
              x2={width - padR}
              y2={toY(pct)}
              stroke={colors.grid}
              strokeWidth={1}
            />
          ))}
          <Line
            x1={nowX}
            y1={padT}
            x2={nowX}
            y2={height - padB}
            stroke={colors.cream}
            strokeOpacity={0.45}
            strokeDasharray="4 4"
            strokeWidth={1.2}
          />
          <Polygon
            points={conePolygon}
            fill={colors.accent}
            fillOpacity={0.18}
            stroke={colors.accentBorder}
            strokeWidth={0.8}
          />
          <Polyline
            points={nominalLine}
            fill="none"
            stroke={colors.accent}
            strokeWidth={2.2}
          />
        </Svg>
      </View>
      <View style={styles.rowBetween}>
        <Label variant="caption" tone="muted">Day 0 (0%)</Label>
        <Label variant="caption" tone="sage">Shaded: Optimistic–Pessimistic</Label>
        <Label variant="caption" tone="muted">Day {maxDay} (100%)</Label>
      </View>
    </Surface>
  );
}

function LiveGrowthTab({
  rotations,
  selectedId,
  onSelect,
}: {
  rotations: LiveRotationDto[];
  selectedId: string | null;
  onSelect: (id: string) => void;
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
  const lagLabel = lag === 0 ? 'On schedule' : lag > 0 ? `+${lag}d ahead` : `${lag}d behind`;

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
          <Stat tile label="Growth Lag" value={lagLabel} accent={lag >= 0} style={styles.flexOne} />
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
            value={ls.safe_expiry_date ? `${formatDate(ls.safe_expiry_date)} (${ls.days_until_safe_expiry ?? 0}d)` : strings.noValue}
            style={styles.flexOne}
          />
          <Stat
            tile
            label="Hard Expiry"
            value={ls.hard_expiry_date ? `${formatDate(ls.hard_expiry_date)} (${ls.days_until_hard_expiry ?? 0}d)` : strings.noValue}
            style={styles.flexOne}
          />
        </View>

        <View style={styles.rowBetween}>
          <Label variant="caption" tone="sage">Harvest Window Uncertainty (σ)</Label>
          <Label variant="button" tone="accent">±{formatNumber(ls.sigma_at_harvest_days, 1)} days</Label>
        </View>
      </Surface>

      <UncertaintyConeChart series={ls.uncertainty_cone_series} tNowDay={ls.t_now_day} />
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
  const selectedRotationId = usePlanner((s) => s.selectedRotationId);
  const selectRotation = usePlanner((s) => s.selectRotation);
  const reset = usePlanner((s) => s.reset);

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
                {tab === 'slab3d' && <Slab3DTab summary={monitor.data} />}
                {tab === 'liveState' && (
                  <LiveGrowthTab
                    rotations={monitor.data.liveMonitor.plain_rotations}
                    selectedId={selectedRotationId}
                    onSelect={(id) => selectRotation(id)}
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
  rowBetween: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: space.sm },
  statRow: { flexDirection: 'row', flexWrap: 'wrap', gap: space.sm },
  flexOne: { flex: 1, minWidth: 92 },
  chartBox: { width: '100%', height: 170 },
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
});
