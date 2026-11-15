import { router } from 'expo-router';
import { useMemo, useState } from 'react';
import { RefreshControl, ScrollView, StyleSheet, View, useWindowDimensions } from 'react-native';
import { useOffline, viewState } from '@/api/query';
import { ActionCard, SeasonBadge, TimelineCard } from '@/components/cards';
import { Feedback } from '@/components/feedback';
import { Backdrop, FieldOverlay } from '@/components/FieldMap';
import { PlanSheet } from '@/components/PlanSheet';
import { Chip, Label, Progress, Stat, Surface } from '@/components/primitives';
import { strings } from '@/i18n/strings';
import { usePlanner } from '@/state/usePlanner';
import { colors, radius, size, space } from '@/theme/tokens';
import { formatNumber } from '@/utils/format';
import { tap } from '@/utils/haptics';
import { useFieldMap } from '../area/hooks';
import { useCountryData } from '../country/hooks';
import { FlowScreen, go, ScrollFrame } from '../planner/FlowScreen';
import { useStrategies } from '../strategy/hooks';
import { getSelectedStrategy } from '../strategy/model';
import { usePlan } from './hooks';
import type { Plan, RotationOption } from './model';

const tabs = [
  { id: 'overview', label: strings.overview },
  { id: 'timeline', label: strings.timeline },
];

function Overview({ plan, rotation }: { plan: Plan; rotation?: RotationOption }) {
  const { fontScale, width } = useWindowDimensions();
  const wrap = fontScale > 1.2 || width < 360;
  const firstSlot = rotation?.slots[0];
  const secondSlot = rotation?.slots[1];
  const primaryCropName = firstSlot?.cropName ?? plan.first.crop.name;
  const startLabel = firstSlot?.sowingDate ?? plan.first.label;
  const nextCropName = secondSlot?.cropName ?? plan.nextCrop ?? strings.noValue;
  const cycleCount = rotation ? rotation.slots.length : plan.timeline.length;

  const stats = [
    [strings.type, firstSlot?.family ?? plan.crop.category, false],
    [strings.area, plan.area, false],
    [rotation ? 'Score' : strings.yield, rotation ? `${formatNumber(rotation.totalAgronomicScore)} pts` : plan.crop.cropYield, true],
    [strings.seasons, formatNumber(cycleCount), true],
    [strings.status, rotation?.rating ?? plan.strategy, false],
    [strings.starts, startLabel, false],
    [strings.water, plan.crop.waterLabel, true],
    [strings.nextCrop, nextCropName, false],
  ] as const;

  return (
    <>
      <View style={styles.badgeRow}>
        <SeasonBadge label={`${plan.mode === 'continuous' ? 'Continuous' : plan.strategy} · ${plan.strategy}`} />
        {rotation?.collisionProbabilityPct != null && (
          <View style={[styles.riskPill, rotation.collisionProbabilityPct > 25 && styles.riskPillDanger]}>
            <Label variant="smallBold" tone={rotation.collisionProbabilityPct > 25 ? 'danger' : 'accent'}>
              {strings.risk}: {rotation.collisionProbabilityPct}%
            </Label>
          </View>
        )}
      </View>

      <ActionCard
        label={strings.nextStep}
        prefix={strings.action}
        action={strings.sow(primaryCropName)}
        season={firstSlot ? firstSlot.dateSpan : plan.first.label}
      />

      <View style={styles.grid}>
        {stats.map(([label, value, accent]) => (
          <Stat
            key={label}
            label={label}
            value={value}
            accent={accent}
            compact={!wrap}
            style={wrap ? styles.wideStat : styles.smallStat}
          />
        ))}
      </View>

      {!!rotation?.turnaroundSummary && (
        <Surface kind="card" rounding={radius.tile} style={styles.infoCard}>
          <View style={styles.infoHeader}>
            <Label variant="label" tone="sage">{strings.turnaround}</Label>
            <Label variant="smallBold" tone="accent">
              {rotation.turnaroundSummary.bufferDays}d · {rotation.turnaroundSummary.status}
            </Label>
          </View>
          <Label variant="caption" tone="cream">{rotation.turnaroundSummary.advisory}</Label>
        </Surface>
      )}

      {(rotation?.safeExpiryDate || rotation?.hardExpiryDate) && (
        <Surface kind="glass" rounding={radius.tile} style={styles.infoCard}>
          <Label variant="label" tone="sage">{strings.expiry}</Label>
          <View style={styles.expiryRow}>
            {rotation.safeExpiryDate && (
              <View style={styles.expiryItem}>
                <Label variant="caption" tone="sage">Safe expiry</Label>
                <Label variant="smallBold" tone="accent">
                  {rotation.safeExpiryDate}
                  {rotation.daysUntilSafeExpiry != null ? ` (${rotation.daysUntilSafeExpiry}d)` : ''}
                </Label>
              </View>
            )}
            {rotation.hardExpiryDate && (
              <View style={styles.expiryItem}>
                <Label variant="caption" tone="sage">Hard expiry</Label>
                <Label variant="smallBold" tone="cream">
                  {rotation.hardExpiryDate}
                  {rotation.daysUntilHardExpiry != null ? ` (${rotation.daysUntilHardExpiry}d)` : ''}
                </Label>
              </View>
            )}
          </View>
        </Surface>
      )}

      <View>
        <View style={styles.water}>
          <Label variant="label" tone="sage">{strings.waterNeed}</Label>
          <Label variant="smallBold" tone="accent">{plan.crop.waterLabel}</Label>
        </View>
        <Progress value={plan.crop.water} label={strings.waterNeed} />
      </View>
    </>
  );
}

function RotationTimeline({ plan, rotation }: { plan: Plan; rotation?: RotationOption }) {
  if (!rotation) {
    return (
      <>
        {plan.timeline.map((item, index) => (
          <TimelineCard
            key={item.id}
            season={item.label}
            crop={item.crop.name}
            summary={item.summary}
            note={item.note}
            first={index === 0}
            dateSpan={item.dateSpan}
            harvestWindow={item.harvestWindow}
            family={item.family}
            growthDays={item.growthDays}
            stages={item.stages}
            collisionPct={item.collisionProbabilityPct}
          />
        ))}
      </>
    );
  }

  return (
    <>
      {rotation.slots.map((slot, index) => {
        const expiryText = slot.safeExpiryDate
          ? `Safe: ${slot.safeExpiryDate}${slot.hardExpiryDate ? ` / Hard: ${slot.hardExpiryDate}` : ''}`
          : undefined;
        const turnaroundText = slot.turnaroundBufferDays != null
          ? `${slot.turnaroundBufferDays}d buffer`
          : undefined;

        return (
          <View key={`${rotation.id}-${slot.cropId}-${index}`} style={styles.slotGroup}>
            <TimelineCard
              season={slot.window || `Cycle ${index + 1}`}
              crop={slot.cropName}
              summary={slot.kcMax != null ? `Kc max ${slot.kcMax.toFixed(2)}` : rotation.rating}
              note={index === 0 ? `#${rotation.rank} Start` : `Cycle ${index + 1}`}
              first={index === 0}
              dateSpan={slot.dateSpan}
              harvestWindow={slot.harvestWindow}
              family={slot.family}
              growthDays={slot.growthDays}
              stages={slot.stages}
              turnaround={turnaroundText}
              expiry={expiryText}
              collisionPct={slot.collisionProbabilityPct}
            />

            {index === 0 && rotation.slots.length > 1 && rotation.turnaroundSummary && (
              <Surface kind="highlight" rounding={radius.tile} style={styles.connectorCard}>
                <View style={styles.infoHeader}>
                  <Label variant="smallBold" tone="accent">
                    {strings.turnaround}: {rotation.turnaroundSummary.bufferDays}d ({rotation.turnaroundSummary.status})
                  </Label>
                  {rotation.uncertaintyCone?.collisionProbabilityPct != null && (
                    <Label variant="caption" tone="cream">
                      {rotation.uncertaintyCone.collisionProbabilityPct}% collision risk
                    </Label>
                  )}
                </View>
                <Label variant="caption" tone="sage">{rotation.turnaroundSummary.advisory}</Label>
              </Surface>
            )}
          </View>
        );
      })}
    </>
  );
}

export default function PlanScreen() {
  const countryId = usePlanner((draft) => draft.countryId);
  const points = usePlanner((draft) => draft.points);
  const latitude = usePlanner((draft) => draft.latitude);
  const longitude = usePlanner((draft) => draft.longitude);
  const boundary = usePlanner((draft) => draft.boundary);
  const areaHa = usePlanner((draft) => draft.areaHa);
  const irrigation = usePlanner((draft) => draft.irrigation);
  const closed = usePlanner((draft) => draft.closed);
  const reached = usePlanner((draft) => draft.reached);
  const strategyId = usePlanner((draft) => draft.strategyId);
  const cropId = usePlanner((draft) => draft.cropId);
  const sowingDate = usePlanner((draft) => draft.sowingDate);
  const selectedRotationId = usePlanner((draft) => draft.selectedRotationId);
  const selectRotation = usePlanner((draft) => draft.selectRotation);
  const reset = usePlanner((draft) => draft.reset);

  const bootstrap = useCountryData();
  const strategies = useStrategies(countryId);
  const selected = getSelectedStrategy(strategies.data, strategyId, bootstrap.data?.defaultStrategyId);
  const map = useFieldMap(countryId);

  const draft = useMemo(
    () => (reached >= 5 && countryId && closed && selected
      ? {
          countryId,
          points,
          latitude,
          longitude,
          boundary: boundary.length >= 3 ? boundary : undefined,
          areaHa,
          strategyId: selected.id,
          irrigation,
          cropId: selected.requiresCrop ? cropId ?? bootstrap.data?.defaultCropId : undefined,
          sowingDate,
        }
      : null),
    [reached, countryId, closed, selected, points, latitude, longitude, boundary, areaHa, irrigation, cropId, bootstrap.data?.defaultCropId, sowingDate],
  );

  const query = usePlan(draft);
  const offline = useOffline();
  const state = viewState({
    isPaused: query.isPaused || strategies.isPaused || bootstrap.isPaused,
    isPending: strategies.isPending || bootstrap.isPending || (!!draft && (query.isPending || (query.isFetching && !query.data))),
    isError: query.isError || strategies.isError || bootstrap.isError,
  }, offline, !!query.data);

  const [active, setActive] = useState(tabs[0].id);
  const refresh = () => {
    void strategies.refetch();
    void bootstrap.refetch();
    void map.refetch();
    if (draft) void query.refetch();
  };

  const plan = query.data;
  const activeRotation = useMemo(() => {
    if (!plan?.rotations.length) return undefined;
    return plan.rotations.find((rot) => rot.id === selectedRotationId) ?? plan.rotations[0];
  }, [plan, selectedRotationId]);

  const headerActions = (
    <View style={styles.headerActions}>
      <View style={styles.actionRow}>
        <Chip label={strings.openMonitor} accent onPress={() => { tap(); router.push('/monitor'); }} />
        <Chip label={strings.saveFarm} onPress={() => { tap(); router.push('/login'); }} />
        <Chip label={strings.restart} onPress={() => { tap(); reset(); go(1); }} />
      </View>
      {!!plan && plan.rotations.length > 1 && (
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={styles.rotationStrip}>
          {plan.rotations.map((rot) => {
            const isSelected = activeRotation?.id === rot.id;
            return (
              <View key={rot.id} style={isSelected ? styles.selectedRotationChip : undefined}>
                <Chip
                  label={`#${rot.rank} ${rot.name} (${formatNumber(rot.score)} pts)`}
                  accent={isSelected}
                  onPress={() => { tap(); selectRotation(rot.id); }}
                />
              </View>
            );
          })}
        </ScrollView>
      )}
    </View>
  );

  return (
    <FlowScreen step={5} action={strings.restart} onNext={() => { reset(); go(1); }}>
      {(inset) => (
        <>
          <View style={styles.planBase} />
          {map.data && <Backdrop image={map.data.image} kind="parcel" />}
          <View pointerEvents="none" style={styles.parcel}><FieldOverlay points={points} closed fit /></View>
          <PlanSheet
            subtitle={plan ? strings.planSubtitle(plan.area, activeRotation ? activeRotation.slots.length : plan.timeline.length) : undefined}
            tabs={tabs}
            active={active}
            bottom={inset.bottom}
            headerActions={headerActions}
            onTab={(id) => { tap(); setActive(id); }}
          >
            <ScrollFrame bottom={inset.bottom}>
              <ScrollView
                showsVerticalScrollIndicator={false}
                refreshControl={
                  <RefreshControl
                    refreshing={query.isRefetching || strategies.isRefetching}
                    onRefresh={refresh}
                    colors={[colors.accent]}
                    tintColor={colors.accent}
                  />
                }
                contentContainerStyle={styles.content}
              >
                <Feedback state={state} layout="plan" onRetry={refresh}>
                  {plan && (active === 'overview'
                    ? <Overview plan={plan} rotation={activeRotation} />
                    : <RotationTimeline plan={plan} rotation={activeRotation} />)}
                </Feedback>
              </ScrollView>
            </ScrollFrame>
          </PlanSheet>
        </>
      )}
    </FlowScreen>
  );
}

const styles = StyleSheet.create({
  planBase: { ...StyleSheet.absoluteFill, backgroundColor: colors.forest900 },
  parcel: { position: 'absolute', start: 0, end: 0, top: size.parcelTop, height: size.parcelHeight },
  content: { paddingHorizontal: space.gutter, paddingVertical: space.lg, gap: space.md },
  headerActions: { gap: space.sm },
  actionRow: { flexDirection: 'row', flexWrap: 'wrap', gap: space.sm },
  rotationStrip: { gap: space.sm, paddingVertical: space.xxs },
  selectedRotationChip: { backgroundColor: colors.accent, borderRadius: radius.pill },
  badgeRow: { flexDirection: 'row', flexWrap: 'wrap', alignItems: 'center', gap: space.sm },
  riskPill: {
    paddingHorizontal: space.md,
    paddingVertical: space.xs,
    borderRadius: radius.pill,
    backgroundColor: colors.highlight,
    borderWidth: size.hairline,
    borderColor: colors.accentBorder,
  },
  riskPillDanger: { backgroundColor: colors.dangerFill, borderColor: colors.dangerBorder },
  grid: { flexDirection: 'row', flexWrap: 'wrap', rowGap: space.lg, marginTop: space.xs },
  smallStat: { flexBasis: '25%', paddingEnd: space.sm },
  wideStat: { flexBasis: '50%', paddingEnd: space.sm },
  infoCard: { padding: space.lg, gap: space.xs },
  infoHeader: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', gap: space.sm },
  expiryRow: { flexDirection: 'row', flexWrap: 'wrap', gap: space.lg, marginTop: space.xxs },
  expiryItem: { gap: space.xxs },
  slotGroup: { gap: space.sm },
  connectorCard: { paddingHorizontal: space.lg, paddingVertical: space.md, gap: space.xxs },
  water: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: space.tight },
});
