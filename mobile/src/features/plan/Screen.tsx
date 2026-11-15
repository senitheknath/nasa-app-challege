import { useMemo, useState } from 'react';
import { Pressable, RefreshControl, ScrollView, StyleSheet, View, useWindowDimensions } from 'react-native';
import { useOffline, viewState } from '@/api/query';
import { TimelineCard } from '@/components/cards';
import { Feedback } from '@/components/feedback';
import { Icon } from '@/components/Icon';
import { PlanSheet } from '@/components/PlanSheet';
import {
  AlternativesList,
  FocusedCropBanner,
  RotationCarousel,
  type CarouselSlotItem,
} from '@/components/RotationCarousel';
import { Label, Stat, Surface } from '@/components/primitives';
import { strings } from '@/i18n/strings';
import { usePlanner } from '@/state/usePlanner';
import { colors, icons, radius, size, space } from '@/theme/tokens';
import { formatNumber } from '@/utils/format';
import { tap } from '@/utils/haptics';
import { useCountryData } from '../country/hooks';
import { FlowScreen, ScrollFrame } from '../planner/FlowScreen';
import { useStrategies } from '../strategy/hooks';
import { getSelectedStrategy } from '../strategy/model';
import { usePlan } from './hooks';
import type { Plan, RotationOption } from './model';

const tabs = [
  { id: 'overview', label: strings.overview },
  { id: 'timeline', label: strings.timeline },
  { id: 'alternatives', label: 'Alternatives' },
] as const;

function compactDays(growthDays?: string): string {
  if (!growthDays) return '95d';
  const match = growthDays.match(/\d+d/);
  return match ? match[0] : growthDays;
}

function buildFallbackSlots(plan: Plan): CarouselSlotItem[] {
  return plan.timeline.map((item, index) => ({
    cropId: item.crop.id,
    cropName: item.crop.name,
    order: index + 1,
    status: index === 0 ? 'Current' : index === 1 ? 'Upcoming' : 'Planned',
    shortSeason: item.season,
    fullSeason: item.dateSpan
      ? `${item.dateSpan}${item.growthDays ? ` · ${compactDays(item.growthDays)}` : ''}`
      : item.label,
    actionPrefix: '',
    actionHighlight: item.crop.name,
    yieldLabel: item.crop.cropYield,
    waterPercent: Math.round(item.crop.water * 100),
    soilBenefit: item.family ? `${item.family} cycle` : 'Balanced soil nutrients',
    family: item.family ?? item.crop.category,
    dateSpan: item.dateSpan,
    growthDays: item.growthDays,
  }));
}

function Overview({
  plan,
  rotation,
  slots,
  focusedIndex,
  hasInteracted,
  onFocusSlot,
  onReset,
  onOpenAlternatives,
}: {
  plan: Plan;
  rotation?: RotationOption;
  slots: readonly CarouselSlotItem[];
  focusedIndex: number;
  hasInteracted: boolean;
  onFocusSlot: (index: number, markInteracted?: boolean) => void;
  onReset: () => void;
  onOpenAlternatives: () => void;
}) {
  const { fontScale, width } = useWindowDimensions();
  const wrap = fontScale > 1.15 || width < 440;
  const focusedSlot = slots[Math.max(0, Math.min(focusedIndex, Math.max(0, slots.length - 1)))];

  const isBest = Boolean(rotation?.isBest || rotation?.rank === 1);
  const rankBadge = isBest
    ? '★ Best Rotation'
    : `Alternative #${rotation?.rank ?? 1}`;
  const sequenceTitle = rotation?.name || slots.map((slot) => slot.cropName).join(' → ');

  const summaryStats = [
    ['Field Area', plan.area, false],
    ['Crop Stages', `${slots.length} crops`, true],
    ['Agronomic Fit', `${formatNumber(rotation?.totalAgronomicScore ?? 0)} pts`, true],
    ['Turnaround', `${rotation?.turnaroundSummary?.bufferDays ?? 14}d buffer`, false],
  ] as const;

  return (
    <>
      <Pressable
        accessibilityRole="button"
        accessibilityLabel={`${rankBadge}: ${sequenceTitle}. Tap to compare all rotations`}
        onPress={onOpenAlternatives}
      >
        <Surface kind="highlight" rounding={radius.tile} style={styles.highlightStrip}>
          <View style={styles.highlightLeft}>
            <Label variant="smallBold" tone="accent">{rankBadge}</Label>
            <Label variant="chip" tone="cream" numberOfLines={1}>{sequenceTitle}</Label>
          </View>
          <View style={styles.scorePill}>
            <Label variant="smallBold" tone="forest950">
              {formatNumber(rotation?.score ?? 0)} pts
            </Label>
          </View>
        </Surface>
      </Pressable>

      {slots.length > 0 && (
        <RotationCarousel
          slots={slots}
          focusedIndex={focusedIndex}
          hasInteracted={hasInteracted}
          onFocusSlot={onFocusSlot}
          onReset={onReset}
        />
      )}

      {focusedSlot && (
        <FocusedCropBanner slot={focusedSlot} totalSlots={slots.length} />
      )}

      <Surface kind="card" rounding={radius.tile} style={styles.statsCard}>
        <View style={styles.statsGrid}>
          {summaryStats.map(([label, value, accent]) => (
            <Stat
              key={label}
              label={label}
              value={value}
              accent={accent}
              compact={!wrap}
              style={wrap ? styles.halfStat : styles.quarterStat}
            />
          ))}
        </View>
      </Surface>
    </>
  );
}

function TurnaroundConnector({ bufferDays, nextCropName }: { bufferDays: number; nextCropName: string }) {
  return (
    <View style={styles.connectorWrap}>
      <View style={styles.connectorLine} />
      <View style={styles.connectorPill}>
        <Icon name="calendar" size={icons.badge} color={colors.accent} />
        <Label variant="caption" tone="sage" numberOfLines={1} style={styles.connectorText}>
          {bufferDays}d field prep & turnaround → Next:{' '}
          <Label variant="smallBold" tone="accent">{nextCropName}</Label>
        </Label>
      </View>
      <View style={styles.connectorLine} />
    </View>
  );
}

function RotationTimeline({ plan, rotation }: { plan: Plan; rotation?: RotationOption }) {
  if (!rotation) {
    return (
      <View style={styles.timelineList}>
        {plan.timeline.map((item, index) => {
          const nextItem = plan.timeline[index + 1];
          return (
            <View key={item.id}>
              <TimelineCard
                season={item.label || `Season ${index + 1}`}
                crop={item.crop.name}
                summary={`${compactDays(item.growthDays)} · ${item.crop.cropYield}`}
                note={`Stage ${index + 1}`}
                first={index === 0}
                dateSpan={item.dateSpan}
                harvestWindow={item.harvestWindow}
                family={item.family ?? item.crop.category}
                growthDays={item.growthDays}
                stages={item.stages}
              />
              {nextItem && (
                <TurnaroundConnector
                  bufferDays={item.turnaroundBufferDays ?? 14}
                  nextCropName={nextItem.crop.name}
                />
              )}
            </View>
          );
        })}
      </View>
    );
  }

  return (
    <View style={styles.timelineList}>
      {rotation.slots.map((slot, index) => {
        const nextSlot = rotation.slots[index + 1];
        const bufferDays = slot.turnaroundBufferDays ?? rotation.turnaroundSummary?.bufferDays ?? 14;

        return (
          <View key={`${rotation.id}-${slot.cropId}-${index}`}>
            <TimelineCard
              season={slot.window || `Season ${index + 1}`}
              crop={slot.cropName}
              summary={`${compactDays(slot.growthDays)} · ${slot.yieldLabel}`}
              note={`Stage ${index + 1}`}
              first={index === 0}
              dateSpan={slot.dateSpan}
              harvestWindow={slot.harvestWindow}
              family={slot.family}
              growthDays={slot.growthDays}
              stages={slot.stages}
            />
            {nextSlot && (
              <TurnaroundConnector
                bufferDays={bufferDays}
                nextCropName={nextSlot.cropName}
              />
            )}
          </View>
        );
      })}
    </View>
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

  const bootstrap = useCountryData();
  const strategies = useStrategies(countryId);
  const selected = getSelectedStrategy(strategies.data, strategyId, bootstrap.data?.defaultStrategyId);

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

  const [active, setActive] = useState<string>(tabs[0].id);
  const [focusedIndex, setFocusedIndex] = useState(0);
  const [hasInteracted, setHasInteracted] = useState(false);

  const refresh = () => {
    void strategies.refetch();
    void bootstrap.refetch();
    if (draft) void query.refetch();
  };

  const plan = query.data;
  const activeRotation = useMemo(() => {
    if (!plan?.rotations.length) return undefined;
    return plan.rotations.find((rot) => rot.id === selectedRotationId) ?? plan.rotations[0];
  }, [plan, selectedRotationId]);

  const slots = useMemo<CarouselSlotItem[]>(() => {
    if (activeRotation?.slots.length) return activeRotation.slots;
    if (plan) return buildFallbackSlots(plan);
    return [];
  }, [activeRotation, plan]);

  const safeFocusedIndex = Math.max(0, Math.min(focusedIndex, Math.max(0, slots.length - 1)));

  const ctaAction = active === 'alternatives'
    ? 'View selected rotation'
    : 'Compare all rotations';

  const onCtaNext = () => {
    tap();
    setActive(active === 'alternatives' ? 'overview' : 'alternatives');
  };

  return (
    <FlowScreen step={5} action={ctaAction} onNext={onCtaNext}>
      {(inset) => (
        <View style={styles.screenBase}>
          <PlanSheet
            subtitle={plan ? `${plan.area} · ${slots.length} crops` : undefined}
            tabs={tabs}
            active={active}
            top={inset.top}
            bottom={inset.bottom}
            onTab={(id) => {
              tap();
              setActive(id);
            }}
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
                    ? (
                      <Overview
                        plan={plan}
                        rotation={activeRotation}
                        slots={slots}
                        focusedIndex={safeFocusedIndex}
                        hasInteracted={hasInteracted}
                        onFocusSlot={(idx, mark = true) => {
                          if (mark) setHasInteracted(true);
                          setFocusedIndex(idx);
                        }}
                        onReset={() => {
                          setHasInteracted(false);
                          setFocusedIndex(0);
                        }}
                        onOpenAlternatives={() => {
                          tap();
                          setActive('alternatives');
                        }}
                      />
                    )
                    : active === 'timeline'
                      ? <RotationTimeline plan={plan} rotation={activeRotation} />
                      : plan.rotations.length > 0
                        ? (
                          <AlternativesList
                            rotations={plan.rotations}
                            selectedId={activeRotation?.id}
                            onSelect={(id) => {
                              tap();
                              selectRotation(id);
                              setFocusedIndex(0);
                              setHasInteracted(false);
                              setActive('overview');
                            }}
                          />
                        )
                        : (
                          <Surface kind="card" rounding={radius.tile} style={styles.emptyCard}>
                            <Label variant="button" tone="cream">Single rotation active</Label>
                            <Label variant="caption" tone="sage">
                              Additional crop rotation alternatives appear when multiple seasonal combinations fit this field.
                            </Label>
                          </Surface>
                        ))}
                </Feedback>
              </ScrollView>
            </ScrollFrame>
          </PlanSheet>
        </View>
      )}
    </FlowScreen>
  );
}

const styles = StyleSheet.create({
  screenBase: { flex: 1, backgroundColor: colors.forest900 },
  content: { paddingHorizontal: space.gutter, paddingTop: space.sm, paddingBottom: space.xl, gap: space.md },
  highlightStrip: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: space.md,
    paddingHorizontal: space.lg,
    paddingVertical: space.md,
  },
  highlightLeft: { flex: 1, minWidth: 0, gap: space.xxs },
  scorePill: {
    paddingHorizontal: space.md,
    paddingVertical: space.xs,
    borderRadius: radius.pill,
    backgroundColor: colors.accent,
  },
  statsCard: { padding: space.lg },
  statsGrid: { flexDirection: 'row', flexWrap: 'wrap', rowGap: space.md },
  quarterStat: { flexBasis: '25%', paddingEnd: space.sm },
  halfStat: { flexBasis: '50%', paddingEnd: space.sm },
  timelineList: { gap: 0 },
  connectorWrap: { alignItems: 'center', paddingVertical: space.xxs },
  connectorLine: { width: 2, height: space.md, backgroundColor: colors.accentBorder },
  connectorPill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: space.tight,
    paddingHorizontal: space.md,
    paddingVertical: space.xs,
    borderRadius: radius.pill,
    backgroundColor: colors.forest800,
    borderWidth: size.hairline,
    borderColor: colors.accentBorder,
    maxWidth: '100%',
  },
  connectorText: { flexShrink: 1 },
  emptyCard: { padding: space.lg, gap: space.xs },
});
