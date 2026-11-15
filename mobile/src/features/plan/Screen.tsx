import { router } from 'expo-router';
import { useMemo, useState } from 'react';
import { Pressable, RefreshControl, ScrollView, StyleSheet, View, useWindowDimensions } from 'react-native';
import { useOffline, viewState } from '@/api/query';
import { TimelineCard } from '@/components/cards';
import { Feedback } from '@/components/feedback';
import { Icon } from '@/components/Icon';
import { PlanSheet } from '@/components/PlanSheet';
import {
  AlternativesList,
  CustomCropBuilderCard,
  FocusedCropBanner,
  RotationCarousel,
  RotationFilterBar,
  type CarouselSlotItem,
  type CropPickerItem,
} from '@/components/RotationCarousel';
import { Label, Stat, Surface } from '@/components/primitives';
import { strings } from '@/i18n/strings';
import { usePlanner } from '@/state/usePlanner';
import { colors, icons, radius, size, space } from '@/theme/tokens';
import { formatNumber } from '@/utils/format';
import { tap } from '@/utils/haptics';
import { useCountryData } from '../country/hooks';
import { useCrops } from '../crop/hooks';
import { FlowScreen, ScrollFrame } from '../planner/FlowScreen';
import { useStrategies } from '../strategy/hooks';
import { getSelectedStrategy } from '../strategy/model';
import {
  evaluateRotationExpiry,
  evaluateSlotExpiry,
  type ExpiryThresholds,
  type ExpiryUrgency,
} from './expiryExplain';
import { usePlan } from './hooks';
import { rankRotationsByFilter, type Plan, type RotationFilterId, type RotationOption } from './model';

const AMBER = '#F5C451';
const AMBER_FILL = 'rgba(245, 196, 81, 0.14)';
const AMBER_BORDER = 'rgba(245, 196, 81, 0.45)';

function urgencyColor(urgency: ExpiryUrgency): string {
  if (urgency === 'critical') return colors.danger;
  if (urgency === 'tight') return AMBER;
  return colors.accent;
}

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
    rawSowingDate: item.rawSowingDate,
    rawHarvestDate: item.rawHarvestDate,
    safeExpiryDate: item.safeExpiryDate,
    hardExpiryDate: item.hardExpiryDate,
    rawSafeExpiryDate: item.rawSafeExpiryDate,
    rawHardExpiryDate: item.rawHardExpiryDate,
    daysUntilSafeExpiry: item.daysUntilSafeExpiry,
    daysUntilHardExpiry: item.daysUntilHardExpiry,
    delaySlackDays: item.delaySlackDays,
    turnaroundBufferDays: item.turnaroundBufferDays,
    collisionProbabilityPct: item.collisionProbabilityPct,
    growthCycleDays: item.growthCycleDays,
    uncertaintyCone: item.uncertaintyCone,
  }));
}

const FILTER_LABELS: Record<RotationFilterId, string> = {
  default: 'Best Match',
  water: 'Water Saving',
  soil: 'Soil & Nitrogen',
  pest: 'Pest Break',
  ease: 'Easy Cycle',
};

function Overview({
  plan,
  rotation,
  activeFilter,
  slots,
  focusedIndex,
  hasInteracted,
  thresholds,
  onFocusSlot,
  onReset,
  onOpenAlternatives,
  onOpenThresholds,
  onOpenMonitor,
}: {
  plan: Plan;
  rotation?: RotationOption;
  activeFilter: RotationFilterId;
  slots: readonly CarouselSlotItem[];
  focusedIndex: number;
  hasInteracted: boolean;
  thresholds: ExpiryThresholds;
  onFocusSlot: (index: number, markInteracted?: boolean) => void;
  onReset: () => void;
  onOpenAlternatives: () => void;
  onOpenThresholds: () => void;
  onOpenMonitor: () => void;
}) {
  const { fontScale, width } = useWindowDimensions();
  const wrap = fontScale > 1.15 || width < 440;
  const safeIdx = Math.max(0, Math.min(focusedIndex, Math.max(0, slots.length - 1)));
  const focusedSlot = slots[safeIdx];
  const nextFocusedCropName = slots[safeIdx + 1]?.cropName;

  const isBest = Boolean(rotation?.isBest || rotation?.rank === 1);
  const rankBadge = rotation?.isCustom
    ? `★ Your Custom Rotation · #${rotation.rank}`
    : isBest
      ? activeFilter === 'default'
        ? '★ Best Rotation'
        : `★ #1 ${FILTER_LABELS[activeFilter]}`
      : `Alternative #${rotation?.rank ?? 1}`;
  const sequenceTitle = rotation?.name || slots.map((slot) => slot.cropName).join(' → ');

  const rotEval = useMemo(
    () =>
      evaluateRotationExpiry(
        rotation ?? { name: sequenceTitle, slots },
        thresholds,
      ),
    [rotation, sequenceTitle, slots, thresholds],
  );

  const summaryStats = [
    ['Field Area', plan.area, false],
    ['Crop Stages', `${slots.length} crops`, true],
    ['Agronomic Fit', `${formatNumber(rotation?.totalAgronomicScore ?? 0)} pts`, true],
    ['Turnaround', `${rotation?.turnaroundSummary?.bufferDays ?? thresholds.expirySafetyDays}d buffer`, false],
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
          <View style={styles.highlightRight}>
            <View style={styles.scorePill}>
              <Label variant="smallBold" tone="forest950">
                {formatNumber(rotation?.score ?? 0)} pts
              </Label>
            </View>
            <View
              style={[
                styles.expiryHighlightPill,
                rotEval.urgency === 'critical'
                  ? styles.expiryHighlightCritical
                  : rotEval.urgency === 'tight'
                    ? styles.expiryHighlightTight
                    : styles.expiryHighlightSafe,
              ]}
            >
              <View style={[styles.expiryDot, { backgroundColor: urgencyColor(rotEval.urgency) }]} />
              <Label variant="label" tone="cream" numberOfLines={1}>
                {rotEval.shortPill}
              </Label>
            </View>
          </View>
        </Surface>
      </Pressable>

      {slots.length > 0 && (
        <RotationCarousel
          slots={slots}
          focusedIndex={focusedIndex}
          hasInteracted={hasInteracted}
          thresholds={thresholds}
          onFocusSlot={onFocusSlot}
          onReset={onReset}
        />
      )}

      {focusedSlot && (
        <FocusedCropBanner
          slot={focusedSlot}
          totalSlots={slots.length}
          nextCropName={nextFocusedCropName}
          thresholds={thresholds}
          onOpenThresholds={onOpenThresholds}
        />
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

        <View
          style={[
            styles.expirySummaryBox,
            rotEval.urgency === 'critical'
              ? styles.expirySummaryCritical
              : rotEval.urgency === 'tight'
                ? styles.expirySummaryTight
                : styles.expirySummarySafe,
          ]}
        >
          <View style={styles.expirySummaryHeader}>
            <View style={styles.expirySummaryTitleRow}>
              <View style={[styles.expiryDot, { backgroundColor: urgencyColor(rotEval.urgency) }]} />
              <Label variant="smallBold" tone="cream" style={styles.breakable}>
                {rotEval.headline}
              </Label>
            </View>
            <Label variant="label" tone={rotEval.urgency === 'critical' ? 'danger' : 'accent'}>
              {rotEval.badgeText}
            </Label>
          </View>
          <Label variant="caption" tone="sage">
            {rotEval.advisory}
          </Label>

          <View style={styles.thresholdActionsRow}>
            <Pressable
              accessibilityRole="button"
              accessibilityLabel={`${strings.adjustThresholds} in Account and Farms`}
              onPress={onOpenThresholds}
              style={styles.thresholdActionPill}
            >
              <Label variant="smallBold" tone="accent" numberOfLines={1}>
                {thresholds.expirySafetyDays}d buf · {thresholds.collisionThresholdPct}% alert · σ={thresholds.weatherVolatility.toFixed(2)} · {strings.adjustThresholds} →
              </Label>
            </Pressable>
            <Pressable
              accessibilityRole="button"
              accessibilityLabel="Track live drift in 3D Monitor"
              onPress={onOpenMonitor}
              style={styles.monitorActionPill}
            >
              <Icon name="activity" size={icons.badge} color={colors.cream} />
              <Label variant="smallBold" tone="cream" numberOfLines={1}>
                Track live drift →
              </Label>
            </Pressable>
          </View>
        </View>
      </Surface>
    </>
  );
}

type TurnaroundStatus = 'optimal' | 'tight' | 'collision' | 'excessive_fallow' | string;

function resolveConnectorTone(status?: TurnaroundStatus) {
  const key = (status ?? 'optimal').toLowerCase();
  if (key === 'collision') {
    return {
      line: colors.dangerBorder,
      bg: colors.dangerFill,
      border: colors.dangerBorder,
      icon: colors.danger,
      labelTone: 'danger' as const,
      tag: 'COLLISION RISK',
    };
  }
  if (key === 'tight') {
    return {
      line: AMBER_BORDER,
      bg: AMBER_FILL,
      border: AMBER_BORDER,
      icon: AMBER,
      labelTone: 'cream' as const,
      tag: 'TIGHT BUFFER',
    };
  }
  if (key === 'excessive_fallow') {
    return {
      line: colors.border,
      bg: colors.innerDark,
      border: colors.border,
      icon: colors.sage,
      labelTone: 'sage' as const,
      tag: 'EXTENDED FALLOW',
    };
  }
  return {
    line: colors.accentBorder,
    bg: colors.forest800,
    border: colors.accentBorder,
    icon: colors.accent,
    labelTone: 'accent' as const,
    tag: 'OPTIMAL',
  };
}

function TurnaroundConnector({
  bufferDays,
  nextCropName,
  status,
  advisory,
}: {
  bufferDays: number;
  nextCropName: string;
  status?: TurnaroundStatus;
  advisory?: string;
}) {
  const tone = resolveConnectorTone(status);
  return (
    <View style={styles.connectorWrap}>
      <View style={[styles.connectorLine, { backgroundColor: tone.line }]} />
      <View
        style={[
          styles.connectorPill,
          { backgroundColor: tone.bg, borderColor: tone.border },
        ]}
      >
        <View style={styles.connectorHeaderRow}>
          <Icon name="calendar" size={icons.badge} color={tone.icon} />
          <Label variant="caption" tone="cream" numberOfLines={1} style={styles.connectorText}>
            {bufferDays}d turnaround ({tone.tag}) → Next:{' '}
            <Label variant="smallBold" tone={tone.labelTone}>{nextCropName}</Label>
          </Label>
        </View>
        {!!advisory && (
          <Label variant="label" tone="sage" style={styles.connectorAdvisory}>
            {advisory}
          </Label>
        )}
      </View>
      <View style={[styles.connectorLine, { backgroundColor: tone.line }]} />
    </View>
  );
}

function RotationTimeline({
  plan,
  rotation,
  thresholds,
}: {
  plan: Plan;
  rotation?: RotationOption;
  thresholds: ExpiryThresholds;
}) {
  if (!rotation) {
    return (
      <View style={styles.timelineList}>
        {plan.timeline.map((item, index) => {
          const nextItem = plan.timeline[index + 1];
          const slotEval = evaluateSlotExpiry(
            {
              cropName: item.crop.name,
              rawSowingDate: item.rawSowingDate,
              rawHarvestDate: item.rawHarvestDate,
              safeExpiryDate: item.safeExpiryDate,
              hardExpiryDate: item.hardExpiryDate,
              rawSafeExpiryDate: item.rawSafeExpiryDate,
              rawHardExpiryDate: item.rawHardExpiryDate,
              daysUntilSafeExpiry: item.daysUntilSafeExpiry,
              daysUntilHardExpiry: item.daysUntilHardExpiry,
              delaySlackDays: item.delaySlackDays,
              turnaroundBufferDays: item.turnaroundBufferDays,
              collisionProbabilityPct: item.collisionProbabilityPct,
              growthDays: item.growthDays,
              growthCycleDays: item.growthCycleDays,
              uncertaintyCone: item.uncertaintyCone,
            },
            thresholds,
            nextItem?.crop.name,
          );
          const bufferDays = item.turnaroundBufferDays ?? thresholds.expirySafetyDays;
          const connectorStatus =
            (item.collisionProbabilityPct ?? 0) >= thresholds.collisionThresholdPct
              ? 'collision'
              : (item.daysUntilSafeExpiry != null && item.daysUntilSafeExpiry < thresholds.expirySafetyDays)
                ? 'tight'
                : 'optimal';

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
                turnaround={item.turnaroundBufferDays != null ? `${item.turnaroundBufferDays}d` : undefined}
                expiry={
                  item.safeExpiryDate || item.hardExpiryDate
                    ? `${item.safeExpiryDate ?? '–'} / ${item.hardExpiryDate ?? '–'}`
                    : undefined
                }
                collisionPct={item.collisionProbabilityPct}
                safeExpiryDate={item.safeExpiryDate}
                hardExpiryDate={item.hardExpiryDate}
                delaySlackDays={item.delaySlackDays}
                uncertaintyCone={item.uncertaintyCone}
                urgency={slotEval.urgency}
                explanation={slotEval.explanation}
                safeCountdownLabel={slotEval.safeCountdownLabel}
                hardCountdownLabel={slotEval.hardCountdownLabel}
                barMetrics={slotEval.barMetrics}
              />
              {nextItem && (
                <TurnaroundConnector
                  bufferDays={bufferDays}
                  nextCropName={nextItem.crop.name}
                  status={connectorStatus}
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
        const slotEval = evaluateSlotExpiry(slot, thresholds, nextSlot?.cropName);
        const slotCollision = slot.collisionProbabilityPct ?? 0;
        const connectorStatus =
          slotCollision >= thresholds.collisionThresholdPct ||
          (slot.daysUntilHardExpiry != null && slot.daysUntilHardExpiry <= 0)
            ? 'collision'
            : index === 0 && rotation.turnaroundSummary?.status
              ? rotation.turnaroundSummary.status
              : slot.daysUntilSafeExpiry != null && slot.daysUntilSafeExpiry < thresholds.expirySafetyDays
                ? 'tight'
                : rotation.turnaroundSummary?.status ?? 'optimal';
        const connectorAdvisory =
          index === 0
            ? rotation.turnaroundSummary?.advisory
            : slotCollision >= thresholds.collisionThresholdPct
              ? `${slot.cropName} carries ${Math.round(slotCollision)}% overlap risk into ${nextSlot?.cropName ?? 'next crop'}.`
              : undefined;

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
              turnaround={slot.turnaroundBufferDays != null ? `${slot.turnaroundBufferDays}d` : undefined}
              expiry={
                slot.safeExpiryDate || slot.hardExpiryDate
                  ? `${slot.safeExpiryDate ?? '–'} / ${slot.hardExpiryDate ?? '–'}`
                  : undefined
              }
              collisionPct={slot.collisionProbabilityPct}
              safeExpiryDate={slot.safeExpiryDate}
              hardExpiryDate={slot.hardExpiryDate}
              delaySlackDays={slot.delaySlackDays}
              uncertaintyCone={slot.uncertaintyCone}
              urgency={slotEval.urgency}
              explanation={slotEval.explanation}
              safeCountdownLabel={slotEval.safeCountdownLabel}
              hardCountdownLabel={slotEval.hardCountdownLabel}
              barMetrics={slotEval.barMetrics}
            />
            {nextSlot && (
              <TurnaroundConnector
                bufferDays={bufferDays}
                nextCropName={nextSlot.cropName}
                status={connectorStatus}
                advisory={connectorAdvisory}
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
  const rotationFilter = usePlanner((draft) => draft.rotationFilter);
  const customCropIds = usePlanner((draft) => draft.customCropIds);
  const expirySafetyDays = usePlanner((draft) => draft.expirySafetyDays);
  const collisionThresholdPct = usePlanner((draft) => draft.collisionThresholdPct);
  const weatherVolatility = usePlanner((draft) => draft.weatherVolatility);
  const setRotationFilter = usePlanner((draft) => draft.setRotationFilter);
  const setCustomCropIds = usePlanner((draft) => draft.setCustomCropIds);
  const toggleCustomCropId = usePlanner((draft) => draft.toggleCustomCropId);

  const thresholds = useMemo<ExpiryThresholds>(
    () => ({ expirySafetyDays, collisionThresholdPct, weatherVolatility }),
    [expirySafetyDays, collisionThresholdPct, weatherVolatility],
  );

  const bootstrap = useCountryData();
  const strategies = useStrategies(countryId);
  const selected = getSelectedStrategy(strategies.data, strategyId, bootstrap.data?.defaultStrategyId);
  const cropRegion = useMemo(
    () => ({ latitude, longitude, sowingDate }),
    [latitude, longitude, sowingDate],
  );
  const cropsQuery = useCrops(countryId, '', '', cropRegion);
  const availableCrops = useMemo<CropPickerItem[]>(
    () =>
      (cropsQuery.data?.pages.flatMap((page) => page.items) ?? []).map((c) => ({
        id: c.id,
        name: c.name,
        family: c.family,
        category: c.category,
      })),
    [cropsQuery.data],
  );

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
          customCropIds: customCropIds.length > 0 ? customCropIds : undefined,
          expirySafetyDays,
        }
      : null),
    [
      reached,
      countryId,
      closed,
      selected,
      points,
      latitude,
      longitude,
      boundary,
      areaHa,
      irrigation,
      cropId,
      bootstrap.data?.defaultCropId,
      sowingDate,
      customCropIds,
      expirySafetyDays,
    ],
  );

  const query = usePlan(draft);
  const baseDraftKey = draft
    ? `${draft.countryId}|${draft.strategyId}|${draft.cropId ?? ''}|${draft.sowingDate}|${draft.irrigation}|${draft.latitude ?? ''}|${draft.longitude ?? ''}|${draft.expirySafetyDays ?? ''}`
    : '';
  const [retainedPlan, setRetainedPlan] = useState<{ key: string; data: Plan } | null>(null);

  if (query.data && baseDraftKey && (retainedPlan?.key !== baseDraftKey || retainedPlan.data !== query.data)) {
    setRetainedPlan({ key: baseDraftKey, data: query.data });
  }

  const plan = query.data ?? (retainedPlan && retainedPlan.key === baseDraftKey ? retainedPlan.data : undefined);
  const hasPlanData = !!plan;
  const offline = useOffline();
  const state = viewState({
    isPaused: query.isPaused || strategies.isPaused || bootstrap.isPaused,
    isPending:
      strategies.isPending ||
      bootstrap.isPending ||
      (!!draft && !hasPlanData && (query.isPending || (query.isFetching && !query.data))),
    isError: query.isError || strategies.isError || bootstrap.isError,
  }, offline, hasPlanData);

  const [active, setActive] = useState<string>(tabs[0].id);
  const [focusedIndex, setFocusedIndex] = useState(0);
  const [hasInteracted, setHasInteracted] = useState(false);

  const refresh = () => {
    void strategies.refetch();
    void bootstrap.refetch();
    void cropsQuery.refetch();
    if (draft) void query.refetch();
  };

  const rankedRotations = useMemo(
    () => rankRotationsByFilter(plan?.rotations ?? [], rotationFilter),
    [plan?.rotations, rotationFilter],
  );

  const customRotation = useMemo(
    () => rankedRotations.find((rot) => rot.isCustom),
    [rankedRotations],
  );

  const activeRotation = useMemo(() => {
    if (!rankedRotations.length) return undefined;
    if (selectedRotationId) {
      const matched = rankedRotations.find((rot) => rot.id === selectedRotationId);
      if (matched) return matched;
    }
    if (customCropIds.length > 0 && customRotation) {
      return customRotation;
    }
    return rankedRotations[0];
  }, [rankedRotations, selectedRotationId, customCropIds.length, customRotation]);

  const slots = useMemo<CarouselSlotItem[]>(() => {
    if (activeRotation?.slots.length) return activeRotation.slots;
    if (plan) return buildFallbackSlots(plan);
    return [];
  }, [activeRotation, plan]);

  const safeFocusedIndex = Math.max(0, Math.min(focusedIndex, Math.max(0, slots.length - 1)));

  const pinnedCropId = selected?.requiresCrop
    ? (cropId ?? bootstrap.data?.defaultCropId ?? undefined)
    : undefined;
  const pinnedCropName = pinnedCropId
    ? (availableCrops.find((c) => c.id === pinnedCropId)?.name ??
        (plan?.crop.id === pinnedCropId ? plan.crop.name : undefined))
    : undefined;

  const handleSmartSwap = (replaceCropId: string, withCropId: string) => {
    tap();
    const hasReplace = customCropIds.includes(replaceCropId);
    const replaced = hasReplace
      ? customCropIds.map((id) => (id === replaceCropId ? withCropId : id))
      : [...customCropIds, withCropId];
    const nextIds = Array.from(new Set(replaced)).slice(0, 4);
    setCustomCropIds(nextIds);
    selectRotation(null);
    setFocusedIndex(0);
    setHasInteracted(false);
  };

  const filterAndBuilder = (
    <>
      <RotationFilterBar
        activeFilter={rotationFilter}
        onSelectFilter={(filter) => {
          tap();
          setRotationFilter(filter);
          selectRotation(null);
          setFocusedIndex(0);
          setHasInteracted(false);
        }}
      />
      <CustomCropBuilderCard
        availableCrops={availableCrops}
        selectedCropIds={customCropIds}
        pinnedCropId={pinnedCropId}
        pinnedCropName={pinnedCropName}
        customRotation={customRotation}
        totalRotations={rankedRotations.length}
        onToggleCrop={(id) => {
          tap();
          toggleCustomCropId(id);
          selectRotation(null);
          setFocusedIndex(0);
          setHasInteracted(false);
        }}
        onClearCrops={() => {
          tap();
          setCustomCropIds([]);
          selectRotation(null);
          setFocusedIndex(0);
          setHasInteracted(false);
        }}
        onApplySmartSwap={handleSmartSwap}
        onSelectCustomRotation={(id) => {
          tap();
          selectRotation(id);
          setFocusedIndex(0);
          setHasInteracted(false);
        }}
      />
    </>
  );

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
                      <>
                        {filterAndBuilder}
                        <Overview
                          plan={plan}
                          rotation={activeRotation}
                          activeFilter={rotationFilter}
                          slots={slots}
                          focusedIndex={safeFocusedIndex}
                          hasInteracted={hasInteracted}
                          thresholds={thresholds}
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
                          onOpenThresholds={() => {
                            tap();
                            router.push('/login');
                          }}
                          onOpenMonitor={() => {
                            tap();
                            router.navigate('/monitor');
                          }}
                        />
                      </>
                    )
                    : active === 'timeline'
                      ? <RotationTimeline plan={plan} rotation={activeRotation} thresholds={thresholds} />
                      : (
                        <>
                          {filterAndBuilder}
                          {rankedRotations.length > 0
                            ? (
                              <AlternativesList
                                rotations={rankedRotations}
                                selectedId={activeRotation?.id}
                                activeFilter={rotationFilter}
                                thresholds={thresholds}
                                onSelect={(id) => {
                                  tap();
                                  selectRotation(id);
                                  setFocusedIndex(0);
                                  setHasInteracted(false);
                                  setActive('overview');
                                }}
                                onApplySmartSwap={handleSmartSwap}
                              />
                            )
                            : (
                              <Surface kind="card" rounding={radius.tile} style={styles.emptyCard}>
                                <Label variant="button" tone="cream">Single rotation active</Label>
                                <Label variant="caption" tone="sage">
                                  Additional crop rotation alternatives appear when multiple seasonal combinations fit this field.
                                </Label>
                              </Surface>
                            )}
                        </>
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
  highlightRight: { alignItems: 'flex-end', gap: space.xs },
  scorePill: {
    paddingHorizontal: space.md,
    paddingVertical: space.xs,
    borderRadius: radius.pill,
    backgroundColor: colors.accent,
  },
  expiryHighlightPill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: space.xs,
    paddingHorizontal: space.sm,
    paddingVertical: space.xxs + 1,
    borderRadius: radius.pill,
    borderWidth: size.hairline,
  },
  expiryHighlightSafe: { backgroundColor: colors.highlight, borderColor: colors.accentBorder },
  expiryHighlightTight: { backgroundColor: AMBER_FILL, borderColor: AMBER_BORDER },
  expiryHighlightCritical: { backgroundColor: colors.dangerFill, borderColor: colors.dangerBorder },
  expiryDot: { width: 7, height: 7, borderRadius: 4, flexShrink: 0 },
  statsCard: { padding: space.lg, gap: space.md },
  statsGrid: { flexDirection: 'row', flexWrap: 'wrap', rowGap: space.md },
  quarterStat: { flexBasis: '25%', paddingEnd: space.sm },
  halfStat: { flexBasis: '50%', paddingEnd: space.sm },
  expirySummaryBox: {
    padding: space.md,
    borderRadius: radius.tile,
    borderWidth: size.hairline,
    gap: space.xs,
  },
  expirySummarySafe: { backgroundColor: colors.innerDark, borderColor: colors.accentBorder },
  expirySummaryTight: { backgroundColor: AMBER_FILL, borderColor: AMBER_BORDER },
  expirySummaryCritical: { backgroundColor: colors.dangerFill, borderColor: colors.dangerBorder },
  expirySummaryHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    flexWrap: 'wrap',
    gap: space.xs,
  },
  expirySummaryTitleRow: { flexDirection: 'row', alignItems: 'center', gap: space.xs, flex: 1, minWidth: 160 },
  breakable: { flexShrink: 1 },
  thresholdActionsRow: { flexDirection: 'row', flexWrap: 'wrap', gap: space.xs, marginTop: space.xs },
  thresholdActionPill: {
    paddingHorizontal: space.md,
    paddingVertical: space.xs,
    borderRadius: radius.pill,
    backgroundColor: colors.highlight,
    borderWidth: size.hairline,
    borderColor: colors.accentBorder,
    flexShrink: 1,
  },
  monitorActionPill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: space.xs,
    paddingHorizontal: space.md,
    paddingVertical: space.xs,
    borderRadius: radius.pill,
    backgroundColor: colors.chip,
    borderWidth: size.hairline,
    borderColor: colors.border,
  },
  timelineList: { gap: 0 },
  connectorWrap: { alignItems: 'center', paddingVertical: space.xxs },
  connectorLine: { width: 2, height: space.md, backgroundColor: colors.accentBorder },
  connectorPill: {
    alignItems: 'center',
    gap: space.xxs,
    paddingHorizontal: space.md,
    paddingVertical: space.xs,
    borderRadius: radius.tile,
    backgroundColor: colors.forest800,
    borderWidth: size.hairline,
    borderColor: colors.accentBorder,
    maxWidth: '100%',
  },
  connectorHeaderRow: { flexDirection: 'row', alignItems: 'center', gap: space.tight, maxWidth: '100%' },
  connectorText: { flexShrink: 1 },
  connectorAdvisory: { textAlign: 'center', paddingHorizontal: space.xs },
  emptyCard: { padding: space.lg, gap: space.xs },
});
