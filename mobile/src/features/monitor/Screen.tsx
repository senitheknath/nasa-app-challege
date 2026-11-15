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
  type LiveRotationDto,
  type MonitorRequestDto,
  type MonitorSummary,
  type UncertaintyConePointDto,
} from './model';
import { Slab3DView } from './Slab3DView';

type TabId = 'slab3d' | 'liveState' | 'rawTelemetry';

const T_NOW_OPTIONS = [14, 42, 75, 105] as const;

const NDVI_OPTIONS: readonly { label: string; value: number | null }[] = [
  { label: 'Auto', value: null },
  { label: 'NDVI 0.35 (Stressed)', value: 0.35 },
  { label: 'NDVI 0.62 (Nominal)', value: 0.62 },
  { label: 'NDVI 0.78 (Vigorous)', value: 0.78 },
];

const VOLATILITY_OPTIONS: readonly { label: string; value: number }[] = [
  { label: 'Low 0.10', value: 0.1 },
  { label: 'Med 0.18', value: 0.18 },
  { label: 'High 0.30', value: 0.3 },
];

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

function SimulationControls() {
  const tNowDay = usePlanner((s) => s.tNowDay);
  const observedNdvi = usePlanner((s) => s.observedNdvi);
  const weatherVolatility = usePlanner((s) => s.weatherVolatility);
  const setMonitorParams = usePlanner((s) => s.setMonitorParams);

  return (
    <Surface kind="glass" rounding={radius.card} style={styles.controlsCard}>
      <View style={styles.controlGroup}>
        <Label variant="tag" tone="sage">SIMULATION DAY (t_now)</Label>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.chipRow}>
          {T_NOW_OPTIONS.map((day) => (
            <SelectChip
              key={day}
              label={`Day ${day}`}
              active={tNowDay === day}
              onPress={() => setMonitorParams({ tNowDay: day })}
            />
          ))}
        </ScrollView>
      </View>

      <View style={styles.controlGroup}>
        <Label variant="tag" tone="sage">SATELLITE NDVI OVERRIDE</Label>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.chipRow}>
          {NDVI_OPTIONS.map((opt) => (
            <SelectChip
              key={opt.label}
              label={opt.label}
              active={observedNdvi === opt.value}
              onPress={() => setMonitorParams({ observedNdvi: opt.value })}
            />
          ))}
        </ScrollView>
      </View>

      <View style={styles.controlGroup}>
        <Label variant="tag" tone="sage">WEATHER VOLATILITY</Label>
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.chipRow}>
          {VOLATILITY_OPTIONS.map((opt) => (
            <SelectChip
              key={opt.label}
              label={opt.label}
              active={Math.abs(weatherVolatility - opt.value) < 0.005}
              onPress={() => setMonitorParams({ weatherVolatility: opt.value })}
            />
          ))}
        </ScrollView>
      </View>
    </Surface>
  );
}

function Slab3DTab({ summary }: { summary: MonitorSummary }) {
  const { slab3d } = summary;
  const fusion = slab3d.sensor_fusion;
  const moisture3Way = fusion.moisture_fusion_3way ?? {};

  return (
    <View style={styles.sectionStack}>
      <Slab3DView slab={slab3d} />

      <View style={styles.sectionHeader}>
        <Label variant="tag" tone="sage">{strings.soilHorizons}</Label>
        <Label variant="caption" tone="muted">
          Root zone {summary.rootDepthLabel}
        </Label>
      </View>

      <View style={styles.horizonGrid}>
        {slab3d.soil_3d_horizons.map((h) => (
          <Surface
            key={h.depth_label}
            kind={h.roots_present ? 'selected' : 'card'}
            rounding={radius.tile}
            style={styles.horizonCard}
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
            {h.usda_texture && (
              <Label variant="caption" tone="sage" numberOfLines={1}>
                {h.usda_texture}
              </Label>
            )}
          </Surface>
        ))}
      </View>

      <Surface kind="card" rounding={radius.card} style={styles.cardPad}>
        <View style={styles.rowBetween}>
          <Label variant="tag" tone="sage">{strings.sensorFusion}</Label>
          {fusion.combined_parcel_dt_days != null && (
            <Label variant="caption" tone="accent">
              Revisit {formatNumber(fusion.combined_parcel_dt_days, 2)}d
            </Label>
          )}
        </View>
        <View style={styles.statRow}>
          {fusion.parcel_mean_moisture_conserved_pct != null && (
            <Stat
              tile
              label="Parcel Moisture"
              value={`${formatNumber(fusion.parcel_mean_moisture_conserved_pct, 1)}%`}
              accent
              style={styles.flexOne}
            />
          )}
          {Object.entries(moisture3Way).slice(0, 3).map(([key, val]) => (
            <Stat
              key={key}
              tile
              compact
              label={key.replace(/_/g, ' ')}
              value={typeof val === 'number' ? formatNumber(val, 1) : String(val ?? strings.noValue)}
              style={styles.flexOne}
            />
          ))}
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

  const request: MonitorRequestDto | null = useMemo(() => {
    if (!countryId) return null;
    return {
      country: countryId,
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
    };
  }, [countryId, latitude, longitude, geoBoundary, areaHa, sowingDate, irrigation, tNowDay, observedNdvi, weatherVolatility]);

  const monitor = useMonitor3D(request);
  const offline = useOffline();
  const state = viewState(monitor, offline, monitor.data != null);

  const tabs = [
    { id: 'slab3d', label: strings.slab3d },
    { id: 'liveState', label: strings.liveState },
    { id: 'rawTelemetry', label: strings.rawTelemetry },
  ] as const;

  return (
    <FlowScreen step={6} action={strings.restart} onNext={() => { reset(); go(1); }}>
      {(inset) => (
        <ScreenScroll inset={inset} contentContainerStyle={styles.scrollContent}>
          <SimulationControls />

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
