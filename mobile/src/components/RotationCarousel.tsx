import { useEffect, useMemo, useState } from 'react';
import { PanResponder, Pressable, ScrollView, StyleSheet, Text, View, type LayoutChangeEvent } from 'react-native';
import Animated, {
  type SharedValue,
  useAnimatedStyle,
  useSharedValue,
  withSpring,
  withTiming,
} from 'react-native-reanimated';
import Svg, { Circle, Path } from 'react-native-svg';
import { useTheme } from '@/theme/useTheme';
import { Icon } from './Icon';

export type RotationFilterOptionId = 'default' | 'water' | 'soil' | 'pest' | 'ease';

export type CropPickerItem = {
  id: string;
  name: string;
  family?: string;
  category?: string;
};

export type CarouselSlotItem = {
  cropId: string;
  cropName: string;
  order: number;
  status: 'Current' | 'Upcoming' | 'Planned';
  shortSeason: string;
  fullSeason: string;
  actionPrefix?: string;
  actionHighlight?: string;
  yieldLabel: string;
  waterPercent?: number;
  soilBenefit: string;
  family?: string;
  dateSpan?: string;
  growthDays?: string;
};

export type AlternativePlanItem = {
  id: string;
  name: string;
  rank: number;
  score: number;
  rating: string;
  period: string;
  title: string;
  badge: string;
  slots: { cropId: string; cropName: string }[];
  isBest?: boolean;
  cropCount?: number;
  totalDays?: number;
  isCustom?: boolean;
  filterScores?: Record<RotationFilterOptionId, number>;
  filterBadges?: Record<RotationFilterOptionId, string>;
  customComparison?: { gapPts: number; reason: string };
  smartSwap?: {
    replaceCropId: string;
    replaceCropName: string;
    withCropId: string;
    withCropName: string;
    gainPts: number;
    reason: string;
  };
};

const CARD_WIDTH = 104;
const CARD_HEIGHT = 104;
const TRACK_HEIGHT = 136;
const ARROW_WIDTH = 22;
const ARROW_HEIGHT = 14;
const INITIAL_ANCHOR_X = 14;
const INITIAL_GAP = 12;
const INTERACTED_GAP = 24;
const LIME = '#b8f334';
const SPRING_CONFIG = { damping: 20, stiffness: 180, mass: 0.8 } as const;
const INITIAL_SCALES = [1.04, 0.94, 0.88, 0.84, 0.80] as const;

function getInitialScale(index: number): number {
  return INITIAL_SCALES[index] ?? Math.max(0.74, 0.80 - (index - 4) * 0.04);
}

function getCardMetrics(
  index: number,
  focusedIndex: number,
  hasInteracted: boolean,
  trackWidth: number
) {
  if (!hasInteracted) {
    return {
      targetX: INITIAL_ANCHOR_X + index * (CARD_WIDTH + INITIAL_GAP),
      targetScale: getInitialScale(index),
      targetOpacity: index === 0 ? 1 : Math.max(0.54, 0.94 - index * 0.08),
    };
  }

  const centerOffset = (trackWidth - CARD_WIDTH) / 2;
  const diff = index - focusedIndex;
  const absDiff = Math.abs(diff);

  return {
    targetX: centerOffset + diff * (CARD_WIDTH + INTERACTED_GAP),
    targetScale: diff === 0 ? 1.08 : Math.max(0.76, 0.90 - absDiff * 0.06),
    targetOpacity: diff === 0 ? 1 : Math.max(0.42, 0.85 - absDiff * 0.16),
  };
}

function truncateBenefit(text: string): string {
  const trimmed = text.trim();
  if (trimmed.length <= 28) return trimmed;
  return `${trimmed.slice(0, 27).trimEnd()}…`;
}

function AnimatedCarouselCard({
  slot,
  index,
  focusedIndex,
  hasInteracted,
  trackWidth,
  dragX,
  reducedMotion,
  onPress,
}: {
  slot: CarouselSlotItem;
  index: number;
  focusedIndex: number;
  hasInteracted: boolean;
  trackWidth: number;
  dragX: SharedValue<number>;
  reducedMotion: boolean;
  onPress: () => void;
}) {
  const { targetX, targetScale, targetOpacity } = getCardMetrics(
    index,
    focusedIndex,
    hasInteracted,
    trackWidth
  );

  const animX = useSharedValue(targetX);
  const animScale = useSharedValue(targetScale);
  const animOpacity = useSharedValue(targetOpacity);

  useEffect(() => {
    if (reducedMotion) {
      animX.set(targetX);
      animScale.set(targetScale);
      animOpacity.set(targetOpacity);
      return;
    }
    animX.set(withSpring(targetX, SPRING_CONFIG));
    animScale.set(withSpring(targetScale, SPRING_CONFIG));
    animOpacity.set(withTiming(targetOpacity, { duration: 180 }));
  }, [targetX, targetScale, targetOpacity, reducedMotion, animX, animScale, animOpacity]);

  const animatedStyle = useAnimatedStyle(() => ({
    opacity: animOpacity.get(),
    transform: [
      { translateX: animX.get() + dragX.get() },
      { scale: animScale.get() },
    ],
  }));

  const diff = index - focusedIndex;
  const isFocalCard = hasInteracted ? diff === 0 : index === 0;
  const isLeftShrunkCard = hasInteracted && diff < 0;
  const zIndex = hasInteracted ? Math.round(20 - Math.abs(diff) * 4) : 20 - index;

  return (
    <Animated.View style={[styles.slotCardPosition, { zIndex }, animatedStyle]}>
      <Pressable
        accessibilityRole="button"
        accessibilityLabel={`Focus ${slot.cropName}`}
        onPress={onPress}
        style={[
          styles.slotCard,
          isFocalCard
            ? styles.slotCardFocal
            : isLeftShrunkCard
            ? styles.slotCardLeftShrunk
            : styles.slotCardDefault,
        ]}
      >
        <View style={styles.slotTopRow}>
          <Text
            style={[
              styles.slotOrder,
              isFocalCard ? styles.slotOrderFocal : styles.slotOrderMuted,
            ]}
          >
            {slot.order}.
          </Text>

          {slot.status === 'Current' && (
            <View
              style={[
                styles.statusBadge,
                isFocalCard ? styles.statusBadgeCurrentFocal : styles.statusBadgeCurrent,
              ]}
            >
              <Text
                style={[
                  styles.statusBadgeText,
                  isFocalCard ? styles.statusTextCurrentFocal : styles.statusTextCurrent,
                ]}
              >
                Current
              </Text>
            </View>
          )}

          {slot.status !== 'Current' && isFocalCard && (
            <View style={styles.statusBadgeFocus}>
              <Text style={styles.statusTextFocus}>Focus</Text>
            </View>
          )}
        </View>

        <View style={styles.slotBottomRow}>
          <Text
            numberOfLines={2}
            style={[
              styles.slotCropName,
              slot.cropName.length > 10 ? styles.slotCropNameCompact : styles.slotCropNameRegular,
              isFocalCard
                ? slot.order === 1
                  ? styles.slotCropNameAccent
                  : styles.slotCropNameWhite
                : styles.slotCropNameMuted,
            ]}
          >
            {slot.cropName}
          </Text>
          <Text
            numberOfLines={1}
            style={[
              styles.slotSeason,
              isFocalCard ? styles.slotSeasonFocal : styles.slotSeasonMuted,
            ]}
          >
            {slot.shortSeason}
          </Text>
        </View>
      </Pressable>
    </Animated.View>
  );
}

function AnimatedConnectorArrow({
  index,
  focusedIndex,
  hasInteracted,
  trackWidth,
  dragX,
  reducedMotion,
}: {
  index: number;
  focusedIndex: number;
  hasInteracted: boolean;
  trackWidth: number;
  dragX: SharedValue<number>;
  reducedMotion: boolean;
}) {
  const gap = hasInteracted ? INTERACTED_GAP : INITIAL_GAP;
  const { targetX: leftCardX } = getCardMetrics(index, focusedIndex, hasInteracted, trackWidth);
  const targetX = leftCardX + CARD_WIDTH + (gap - ARROW_WIDTH) / 2;
  const minDist = Math.min(Math.abs(index - focusedIndex), Math.abs(index + 1 - focusedIndex));
  const targetOpacity = hasInteracted ? (minDist <= 1 ? 0.95 : 0.45) : 0;

  const animX = useSharedValue(targetX);
  const animOpacity = useSharedValue(targetOpacity);

  useEffect(() => {
    if (reducedMotion) {
      animX.set(targetX);
      animOpacity.set(targetOpacity);
      return;
    }
    animX.set(withSpring(targetX, SPRING_CONFIG));
    animOpacity.set(withTiming(targetOpacity, { duration: 200 }));
  }, [targetX, targetOpacity, reducedMotion, animX, animOpacity]);

  const animatedStyle = useAnimatedStyle(() => ({
    opacity: animOpacity.get(),
    transform: [{ translateX: animX.get() + dragX.get() }],
  }));

  return (
    <Animated.View pointerEvents="none" style={[styles.arrowContainer, animatedStyle]}>
      <Svg width={ARROW_WIDTH} height={ARROW_HEIGHT} viewBox="0 0 22 14">
        <Circle cx="3" cy="7" r="1.4" fill={LIME} />
        <Circle cx="7.5" cy="7" r="1.4" fill={LIME} />
        <Circle cx="12" cy="7" r="1.4" fill={LIME} />
        <Path
          d="M15 3.5L19.5 7L15 10.5"
          stroke={LIME}
          strokeWidth="1.8"
          strokeLinecap="round"
          strokeLinejoin="round"
          fill="none"
        />
      </Svg>
    </Animated.View>
  );
}

export function FocusedCropBanner({ slot, totalSlots }: { slot: CarouselSlotItem; totalSlots: number }) {
  const durationLabel =
    slot.growthDays || slot.fullSeason.split('·')[1]?.trim() || '95 days';
  const windowLabel = slot.dateSpan || slot.shortSeason;
  const benefitLabel = truncateBenefit(slot.soilBenefit || 'Balances soil nutrients');

  return (
    <View style={styles.bannerCard}>
      <View style={styles.bannerTopRow}>
        <View style={styles.bannerStagePill}>
          {slot.order === 1 && <View style={styles.bannerStageDot} />}
          <Text style={styles.bannerStageText}>
            Stage {slot.order} of {totalSlots}
          </Text>
        </View>

        <View style={styles.bannerBenefitPill}>
          <Icon name="sprout" size={12} color={LIME} />
          <Text style={styles.bannerBenefitText} numberOfLines={1}>
            {benefitLabel}
          </Text>
        </View>
      </View>

      <View style={styles.bannerMiddleRow}>
        <Text style={styles.bannerCropName} numberOfLines={1}>
          {slot.cropName}
        </Text>
        <View style={styles.bannerFamilyPill}>
          <Text style={styles.bannerFamilyText} numberOfLines={1}>
            {slot.family || 'Crop'}
          </Text>
        </View>
      </View>

      <View style={styles.bannerMetricStrip}>
        <View style={styles.bannerMetricColWide}>
          <Text style={styles.bannerMetricLabel}>WINDOW</Text>
          <Text style={styles.bannerMetricValue} numberOfLines={2}>
            {windowLabel}
          </Text>
        </View>

        <View style={styles.bannerMetricDivider} />

        <View style={styles.bannerMetricCol}>
          <Text style={styles.bannerMetricLabel}>DURATION</Text>
          <Text style={styles.bannerMetricValue} numberOfLines={2}>
            {durationLabel}
          </Text>
        </View>

        <View style={styles.bannerMetricDivider} />

        <View style={styles.bannerMetricCol}>
          <Text style={styles.bannerMetricLabel}>EST. YIELD</Text>
          <Text style={[styles.bannerMetricValue, styles.bannerMetricValueAccent]} numberOfLines={1}>
            {slot.yieldLabel}
          </Text>
        </View>
      </View>
    </View>
  );
}

export function RotationCarousel({
  slots,
  focusedIndex,
  hasInteracted,
  onFocusSlot,
  onReset,
}: {
  slots: readonly CarouselSlotItem[];
  focusedIndex: number;
  hasInteracted: boolean;
  onFocusSlot: (index: number, markInteracted?: boolean) => void;
  onReset: () => void;
}) {
  const { reducedMotion } = useTheme();
  const [trackWidth, setTrackWidth] = useState(346);
  const dragX = useSharedValue(0);
  const haloOpacity = useSharedValue(hasInteracted ? 1 : 0);

  const safeFocusedIndex =
    slots.length === 0 ? 0 : Math.max(0, Math.min(focusedIndex, slots.length - 1));
  const currentGap = hasInteracted ? INTERACTED_GAP : INITIAL_GAP;
  const itemStride = CARD_WIDTH + currentGap;

  useEffect(() => {
    const target = hasInteracted ? 1 : 0;
    if (reducedMotion) {
      haloOpacity.set(target);
      return;
    }
    haloOpacity.set(withTiming(target, { duration: 220 }));
  }, [hasInteracted, reducedMotion, haloOpacity]);

  const haloAnimatedStyle = useAnimatedStyle(() => ({
    opacity: haloOpacity.get(),
  }));

  const panResponder = useMemo(
    () =>
      PanResponder.create({
        onStartShouldSetPanResponder: () => false,
        onMoveShouldSetPanResponder: (_, gesture) =>
          Math.abs(gesture.dx) > 5 && Math.abs(gesture.dx) > Math.abs(gesture.dy),
        onMoveShouldSetPanResponderCapture: (_, gesture) =>
          Math.abs(gesture.dx) > 6 && Math.abs(gesture.dx) > Math.abs(gesture.dy),
        onPanResponderMove: (_, gesture) => {
          dragX.set(gesture.dx);
        },
        onPanResponderRelease: (_, gesture) => {
          dragX.set(reducedMotion ? 0 : withSpring(0, SPRING_CONFIG));
          if (slots.length === 0) return;

          const projectedDx =
            Math.abs(gesture.vx) > 0.35 && Math.abs(gesture.dx) > 16
              ? gesture.dx + gesture.vx * 90
              : gesture.dx;
          const rawFocal = safeFocusedIndex - projectedDx / itemStride;
          const nextIdx = Math.max(0, Math.min(slots.length - 1, Math.round(rawFocal)));
          if (Math.abs(gesture.dx) > 6 || nextIdx !== safeFocusedIndex) {
            onFocusSlot(nextIdx, true);
          }
        },
        onPanResponderTerminate: () => {
          dragX.set(reducedMotion ? 0 : withSpring(0, SPRING_CONFIG));
        },
      }),
    [safeFocusedIndex, itemStride, slots.length, onFocusSlot, dragX, reducedMotion]
  );

  const handleTrackLayout = (event: LayoutChangeEvent) => {
    const nextWidth = event.nativeEvent.layout.width;
    if (nextWidth > 0 && nextWidth !== trackWidth) {
      setTrackWidth(nextWidth);
    }
  };

  return (
    <View style={styles.carouselContainer}>
      <View style={styles.carouselHeader}>
        <Text style={styles.carouselTitle}>Rotation Cycle</Text>

        <View style={styles.carouselHeaderRight}>
          {hasInteracted && (
            <Pressable
              accessibilityRole="button"
              accessibilityLabel="Reset view"
              onPress={onReset}
              hitSlop={8}
              style={styles.resetPill}
            >
              <Text style={styles.resetText}>Reset view</Text>
            </Pressable>
          )}
          <View style={styles.stageCountPill}>
            <Text style={styles.counterText}>
              Stage {slots.length > 0 ? safeFocusedIndex + 1 : 0} of {slots.length}
            </Text>
          </View>
        </View>
      </View>

      <View
        style={styles.trackStage}
        onLayout={handleTrackLayout}
        {...panResponder.panHandlers}
      >
        <Animated.View
          pointerEvents="none"
          style={[
            styles.centerHalo,
            { left: Math.max(0, (trackWidth - 124) / 2) },
            haloAnimatedStyle,
          ]}
        />

        <View style={styles.cardsTrack}>
          {slots.map((slot, index) => (
            <AnimatedCarouselCard
              key={`${slot.cropId}-${index}`}
              slot={slot}
              index={index}
              focusedIndex={safeFocusedIndex}
              hasInteracted={hasInteracted}
              trackWidth={trackWidth}
              dragX={dragX}
              reducedMotion={reducedMotion}
              onPress={() => onFocusSlot(index, true)}
            />
          ))}

          {slots.slice(0, -1).map((slot, index) => (
            <AnimatedConnectorArrow
              key={`arrow-${slot.cropId}-${index}`}
              index={index}
              focusedIndex={safeFocusedIndex}
              hasInteracted={hasInteracted}
              trackWidth={trackWidth}
              dragX={dragX}
              reducedMotion={reducedMotion}
            />
          ))}
        </View>
      </View>

      <View style={styles.carouselFooter}>
        <Text style={styles.footerHint}>
          {hasInteracted ? 'Swipe or tap stage to focus' : 'Swipe or tap any crop'}
        </Text>

        <View style={styles.dotsRow}>
          {slots.map((slot, idx) => {
            const isCurrentDot = idx === safeFocusedIndex;
            return (
              <Pressable
                key={`dot-${slot.cropId}-${idx}`}
                accessibilityRole="button"
                accessibilityLabel={`Focus ${slot.cropName}`}
                onPress={() => onFocusSlot(idx, true)}
                hitSlop={6}
                style={[styles.dot, isCurrentDot ? styles.dotActive : styles.dotInactive]}
              />
            );
          })}
        </View>
      </View>
    </View>
  );
}

type FilterIconName = 'sparkle' | 'drop' | 'sprout' | 'shield' | 'clock';

const FILTER_OPTIONS: readonly {
  id: RotationFilterOptionId;
  label: string;
  icon: FilterIconName;
}[] = [
  { id: 'default', label: 'Best Match', icon: 'sparkle' },
  { id: 'water', label: 'Water Saving', icon: 'drop' },
  { id: 'soil', label: 'Soil & Nitrogen', icon: 'sprout' },
  { id: 'pest', label: 'Pest Break', icon: 'shield' },
  { id: 'ease', label: 'Easy Cycle', icon: 'clock' },
];

function FilterBarIcon({
  name,
  color,
  size = 13,
}: {
  name: FilterIconName;
  color: string;
  size?: number;
}) {
  if (name === 'drop' || name === 'sprout') {
    return <Icon name={name} size={size} color={color} />;
  }
  const path =
    name === 'sparkle'
      ? 'M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9L12 3ZM19 3v4M21 5h-4M5 17v3M6.5 18.5h-3'
      : name === 'shield'
        ? 'M12 3l7 3v5c0 4.5-3 8.3-7 10-4-1.7-7-5.5-7-10V6l7-3Z'
        : 'M12 21a9 9 0 1 0 0-18 9 9 0 0 0 0 18ZM12 7v5l3 2';
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24" aria-hidden>
      <Path
        d={path}
        fill="none"
        stroke={color}
        strokeWidth={1.8}
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </Svg>
  );
}

export function RotationFilterBar({
  activeFilter,
  onSelectFilter,
}: {
  activeFilter: RotationFilterOptionId;
  onSelectFilter: (filter: RotationFilterOptionId) => void;
}) {
  return (
    <ScrollView
      horizontal
      showsHorizontalScrollIndicator={false}
      contentContainerStyle={styles.filterBarContent}
      style={styles.filterBarScroll}
    >
      {FILTER_OPTIONS.map((opt) => {
        const isActive = opt.id === activeFilter;
        const fgColor = isActive ? '#18200e' : '#e5ecd8';
        return (
          <Pressable
            key={opt.id}
            accessibilityRole="button"
            accessibilityLabel={opt.label}
            accessibilityState={{ selected: isActive }}
            onPress={() => onSelectFilter(opt.id)}
            style={[
              styles.filterPill,
              isActive ? styles.filterPillActive : styles.filterPillInactive,
            ]}
          >
            <FilterBarIcon name={opt.icon} color={fgColor} size={13} />
            <Text
              style={[
                styles.filterPillText,
                isActive ? styles.filterPillTextActive : styles.filterPillTextInactive,
              ]}
              numberOfLines={1}
            >
              {opt.label}
            </Text>
          </Pressable>
        );
      })}
    </ScrollView>
  );
}

function formatCropTag(crop: CropPickerItem): string | undefined {
  const raw = `${crop.family ?? ''} ${crop.category ?? ''}`.trim().toLowerCase();
  if (!raw) return undefined;
  if (raw.includes('fabaceae') || raw.includes('legume') || raw.includes('pulse')) return 'Legume';
  if (raw.includes('poaceae') || raw.includes('gramineae') || raw.includes('cereal') || raw.includes('grain')) return 'Cereal';
  if (raw.includes('root') || raw.includes('tuber') || raw.includes('convolvulaceae') || raw.includes('euphorbiaceae')) return 'Root';
  if (raw.includes('solanaceae')) return 'Solanaceae';
  if (raw.includes('brassicaceae')) return 'Brassica';
  if (raw.includes('oilseed') || raw.includes('pedaliaceae') || raw.includes('asteraceae')) return 'Oilseed';
  if (raw.includes('malvaceae')) return 'Fiber';
  const fallback = crop.category || crop.family;
  if (!fallback) return undefined;
  return fallback.length > 12 ? `${fallback.slice(0, 11).trimEnd()}…` : fallback;
}

export function CustomCropBuilderCard({
  availableCrops,
  selectedCropIds,
  pinnedCropId,
  pinnedCropName,
  customRotation,
  totalRotations,
  onToggleCrop,
  onClearCrops,
  onApplySmartSwap,
  onSelectCustomRotation,
}: {
  availableCrops: readonly CropPickerItem[];
  selectedCropIds: readonly string[];
  pinnedCropId?: string;
  pinnedCropName?: string;
  customRotation?: AlternativePlanItem;
  totalRotations?: number;
  onToggleCrop: (cropId: string) => void;
  onClearCrops: () => void;
  onApplySmartSwap?: (replaceCropId: string, withCropId: string) => void;
  onSelectCustomRotation?: (rotationId: string) => void;
}) {
  const [expanded, setExpanded] = useState(false);
  const pickerCrops = availableCrops.slice(0, 18);

  return (
    <View style={[styles.builderCard, customRotation && styles.builderCardActive]}>
      {customRotation ? (
        <View style={styles.builderCustomBlock}>
          <View style={styles.builderCustomHeader}>
            <Pressable
              accessibilityRole="button"
              accessibilityLabel={`Select your custom rotation ranked #${customRotation.rank}`}
              onPress={() => onSelectCustomRotation?.(customRotation.id)}
              style={styles.builderCustomHeaderLeft}
            >
              <View style={styles.builderBadgeRow}>
                <View style={styles.builderCustomBadge}>
                  <Text style={styles.builderCustomBadgeText}>★ YOUR CUSTOM ROTATION</Text>
                </View>
                <Text style={styles.builderRankMeta} numberOfLines={1}>
                  Ranked #{customRotation.rank} of {totalRotations ?? 1} · {Math.round(customRotation.score)} pts
                </Text>
              </View>
              <Text style={styles.builderChainText} numberOfLines={2}>
                {customRotation.slots.map((s) => s.cropName).join(' → ')}
              </Text>
            </Pressable>

            <Pressable
              accessibilityRole="button"
              accessibilityLabel={expanded ? 'Close crop editor' : 'Edit crops'}
              onPress={() => setExpanded((prev) => !prev)}
              hitSlop={6}
              style={styles.builderEditPill}
            >
              <Text style={styles.builderEditPillText}>
                {expanded ? 'Close' : 'Edit crops'}
              </Text>
            </Pressable>
          </View>

          {customRotation.customComparison && (
            <View
              style={[
                styles.comparisonPill,
                customRotation.rank === 1 || customRotation.customComparison.gapPts >= 0
                  ? styles.comparisonPillLime
                  : styles.comparisonPillAmber,
              ]}
            >
              <Text
                style={[
                  styles.comparisonPillText,
                  customRotation.rank === 1 || customRotation.customComparison.gapPts >= 0
                    ? styles.comparisonPillTextLime
                    : styles.comparisonPillTextAmber,
                ]}
                numberOfLines={2}
              >
                {customRotation.rank === 1 || customRotation.customComparison.gapPts >= 0
                  ? customRotation.customComparison.reason.startsWith('★')
                    ? customRotation.customComparison.reason
                    : `★ #1 Best choice · ${customRotation.customComparison.reason}`
                  : `Rank #${customRotation.rank}: ${customRotation.customComparison.reason} (${customRotation.customComparison.gapPts} pts vs #1)`}
              </Text>
            </View>
          )}

          {customRotation.smartSwap && (
            <Pressable
              accessibilityRole="button"
              accessibilityLabel={`Swap ${customRotation.smartSwap.replaceCropName} to ${customRotation.smartSwap.withCropName}`}
              onPress={() =>
                onApplySmartSwap?.(
                  customRotation.smartSwap!.replaceCropId,
                  customRotation.smartSwap!.withCropId
                )
              }
              style={styles.smartSwapChip}
            >
              <FilterBarIcon name="sparkle" color={LIME} size={13} />
              <Text style={styles.smartSwapChipText} numberOfLines={2}>
                Swap {customRotation.smartSwap.replaceCropName} → {customRotation.smartSwap.withCropName} (+
                {Math.round(customRotation.smartSwap.gainPts)} pts · {customRotation.smartSwap.reason})
              </Text>
            </Pressable>
          )}
        </View>
      ) : (
        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Test and score your own crops"
          onPress={() => setExpanded((prev) => !prev)}
          style={styles.builderEmptyRow}
        >
          <View style={styles.builderEmptyLeft}>
            <View style={styles.builderEmptyIconWrap}>
              <Icon name="sprout" size={16} color={LIME} />
            </View>
            <View style={styles.builderEmptyCopy}>
              <Text style={styles.builderEmptyTitle} numberOfLines={1}>
                Test & Score Your Own Crops
              </Text>
              <Text style={styles.builderEmptySubtitle} numberOfLines={2}>
                Pick 2–4 crops you have to see their best rotation order & rank
              </Text>
            </View>
          </View>

          <View style={styles.pickCropsPill}>
            <Text style={styles.pickCropsPillText}>
              {expanded ? 'Close' : '+ Pick crops'}
            </Text>
          </View>
        </Pressable>
      )}

      {expanded && (
        <View style={styles.builderDrawer}>
          {pinnedCropName ? (
            <View style={styles.pinnedCropPill}>
              <Icon name="pin" size={12} color={LIME} />
              <Text style={styles.pinnedCropText} numberOfLines={1}>
                Stage 1 (In field): {pinnedCropName} (Pinned)
              </Text>
            </View>
          ) : null}

          <View style={styles.cropGrid}>
            {pickerCrops.map((crop) => {
              const isPinned = Boolean(pinnedCropId && crop.id === pinnedCropId);
              const isSelected = selectedCropIds.includes(crop.id);
              const tag = formatCropTag(crop);
              return (
                <Pressable
                  key={crop.id}
                  accessibilityRole="button"
                  accessibilityState={{ selected: isSelected, disabled: isPinned }}
                  disabled={isPinned}
                  onPress={() => onToggleCrop(crop.id)}
                  style={[
                    styles.cropPickerPill,
                    isSelected
                      ? styles.cropPickerPillSelected
                      : isPinned
                        ? styles.cropPickerPillPinned
                        : styles.cropPickerPillUnselected,
                  ]}
                >
                  <Text
                    style={[
                      styles.cropPickerName,
                      isSelected ? styles.cropPickerNameSelected : styles.cropPickerNameUnselected,
                    ]}
                    numberOfLines={1}
                  >
                    {crop.name}
                  </Text>
                  {tag ? (
                    <Text
                      style={[
                        styles.cropPickerTag,
                        isSelected ? styles.cropPickerTagSelected : styles.cropPickerTagUnselected,
                      ]}
                      numberOfLines={1}
                    >
                      {tag}
                    </Text>
                  ) : null}
                </Pressable>
              );
            })}
          </View>

          <View style={styles.drawerFooterRow}>
            <View style={styles.drawerFooterLeft}>
              <Text style={styles.drawerSelectionCount}>
                {selectedCropIds.length} selected (pick 2–4)
              </Text>
              {selectedCropIds.length > 0 && (
                <Pressable
                  accessibilityRole="button"
                  accessibilityLabel="Reset selected crops"
                  onPress={onClearCrops}
                  hitSlop={6}
                  style={styles.drawerResetBtn}
                >
                  <Text style={styles.drawerResetText}>Reset</Text>
                </Pressable>
              )}
            </View>

            <Pressable
              accessibilityRole="button"
              accessibilityLabel="Done picking crops"
              onPress={() => setExpanded(false)}
              style={styles.drawerDonePill}
            >
              <Text style={styles.drawerDoneText}>Done</Text>
            </Pressable>
          </View>
        </View>
      )}
    </View>
  );
}

export function AlternativesList({
  rotations,
  selectedId,
  activeFilter,
  onSelect,
  onApplySmartSwap,
}: {
  rotations: readonly AlternativePlanItem[];
  selectedId?: string;
  activeFilter?: RotationFilterOptionId;
  onSelect: (id: string) => void;
  onApplySmartSwap?: (replaceCropId: string, withCropId: string) => void;
}) {
  const filterLabel = (activeFilter ?? 'default').toUpperCase();

  return (
    <View style={styles.alternativesList}>
      {rotations.map((rot, index) => {
        const isSelected = rot.id === selectedId;
        const isCustom = Boolean(rot.isCustom);
        const isTopRegional = rot.rank === 1 && !isCustom;
        const isBest = !isCustom && (rot.isBest ?? (rot.rank === 1 || index === 0));
        const cardTitle = isCustom
          ? 'Your Custom Rotation'
          : isBest
            ? 'Best Rotation'
            : `Alternative ${index + 1}`;
        const cropCount = rot.cropCount ?? rot.slots.length;
        const metaSummary = rot.totalDays
          ? `${cropCount} crops · ${rot.totalDays}d cycle`
          : `${cropCount} crops`;
        const isPositiveCustom =
          rot.rank === 1 || (rot.customComparison != null && rot.customComparison.gapPts >= 0);

        return (
          <Pressable
            key={rot.id}
            accessibilityRole="button"
            accessibilityState={{ selected: isSelected }}
            onPress={() => onSelect(rot.id)}
            style={[
              styles.alternativeCard,
              isCustom
                ? isSelected
                  ? styles.alternativeCardCustomSelected
                  : styles.alternativeCardCustom
                : isSelected
                  ? styles.alternativeCardSelected
                  : isBest
                    ? styles.alternativeCardBest
                    : styles.alternativeCardUnselected,
            ]}
          >
            <View style={styles.alternativeHeaderRow}>
              <View style={styles.alternativeLeftCol}>
                {isCustom ? (
                  <Text style={styles.bestTagText} numberOfLines={1}>
                    ★ YOUR CUSTOM ROTATION · RANK #{rot.rank}
                  </Text>
                ) : isTopRegional ? (
                  <Text style={styles.bestTagText} numberOfLines={1}>
                    ★ #1 BEST FOR {filterLabel} · {rot.period}
                  </Text>
                ) : isBest ? (
                  <Text style={styles.bestTagText} numberOfLines={1}>
                    ★ BEST ROTATION · {rot.period}
                  </Text>
                ) : (
                  <Text style={styles.alternativePeriod} numberOfLines={1}>
                    {rot.period}
                  </Text>
                )}

                {isCustom ? (
                  <View style={styles.customTitleRow}>
                    <Text style={styles.alternativeTitle} numberOfLines={1}>
                      {cardTitle}
                    </Text>
                    <Text style={styles.customTitleScore} numberOfLines={1}>
                      {Math.round(rot.score)} pts
                    </Text>
                  </View>
                ) : (
                  <Text style={styles.alternativeTitle} numberOfLines={1}>
                    {cardTitle}
                  </Text>
                )}

                <Text style={styles.alternativeMeta} numberOfLines={1}>
                  {metaSummary}
                </Text>
              </View>

              <View style={styles.alternativeRightCol}>
                {isSelected ? (
                  <View style={styles.selectedPill}>
                    <Text style={styles.selectedPillText}>Selected</Text>
                  </View>
                ) : (
                  <View style={styles.selectPill}>
                    <Text style={styles.selectPillText}>Select alternative</Text>
                  </View>
                )}

                <View style={styles.alternativeBadge}>
                  <Icon name={isBest || isCustom ? 'check' : 'sprout'} size={11} color={LIME} />
                  <Text style={styles.alternativeBadgeText} numberOfLines={1}>
                    {rot.badge} · {Math.round(rot.score)} pts
                  </Text>
                </View>
              </View>
            </View>

            <View style={styles.sequenceWrap}>
              {rot.slots.map((slot, slotIdx) => (
                <View key={`${rot.id}-${slot.cropId}-${slotIdx}`} style={styles.sequenceItemRow}>
                  <View
                    style={[
                      styles.sequencePill,
                      slotIdx === 0 && styles.sequencePillFirst,
                    ]}
                  >
                    <Text
                      style={[
                        styles.sequencePillOrder,
                        slotIdx === 0 && styles.sequencePillOrderFirst,
                      ]}
                    >
                      {slotIdx + 1}
                    </Text>
                    <Text
                      style={[
                        styles.sequencePillText,
                        slotIdx === 0 && styles.sequencePillTextFirst,
                      ]}
                      numberOfLines={1}
                    >
                      {slot.cropName}
                    </Text>
                  </View>
                  {slotIdx < rot.slots.length - 1 && (
                    <Text style={styles.sequenceArrow}>→</Text>
                  )}
                </View>
              ))}
            </View>

            {isCustom && rot.customComparison && (
              <View
                style={[
                  styles.comparisonPill,
                  isPositiveCustom ? styles.comparisonPillLime : styles.comparisonPillAmber,
                ]}
              >
                <Text
                  style={[
                    styles.comparisonPillText,
                    isPositiveCustom ? styles.comparisonPillTextLime : styles.comparisonPillTextAmber,
                  ]}
                  numberOfLines={2}
                >
                  {rot.customComparison.reason}
                </Text>
              </View>
            )}

            {isCustom && rot.smartSwap && (
              <Pressable
                accessibilityRole="button"
                accessibilityLabel={`Swap ${rot.smartSwap.replaceCropName} to ${rot.smartSwap.withCropName}`}
                onPress={(e) => {
                  e?.stopPropagation?.();
                  onApplySmartSwap?.(
                    rot.smartSwap!.replaceCropId,
                    rot.smartSwap!.withCropId
                  );
                }}
                style={styles.smartSwapChip}
              >
                <FilterBarIcon name="sparkle" color={LIME} size={13} />
                <Text style={styles.smartSwapChipText} numberOfLines={2}>
                  Swap {rot.smartSwap.replaceCropName} → {rot.smartSwap.withCropName} (+
                  {Math.round(rot.smartSwap.gainPts)} pts)
                </Text>
              </Pressable>
            )}
          </Pressable>
        );
      })}
    </View>
  );
}

const styles = StyleSheet.create({
  bannerCard: {
    width: '100%',
    borderRadius: 20,
    backgroundColor: '#243117',
    borderColor: '#4c6132',
    borderWidth: 1,
    paddingHorizontal: 16,
    paddingVertical: 14,
    gap: 10,
  },
  bannerTopRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 8,
  },
  bannerStagePill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 999,
    backgroundColor: '#1b2411',
    borderWidth: 1,
    borderColor: '#3b4b27',
  },
  bannerStageDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
    backgroundColor: LIME,
  },
  bannerStageText: {
    fontSize: 11.5,
    fontWeight: '600',
    color: '#d4e2c2',
  },
  bannerBenefitPill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
    flexShrink: 1,
    paddingHorizontal: 10,
    paddingVertical: 4,
    borderRadius: 999,
    backgroundColor: 'rgba(184, 243, 52, 0.1)',
    borderWidth: 1,
    borderColor: 'rgba(184, 243, 52, 0.28)',
  },
  bannerBenefitText: {
    fontSize: 11.5,
    fontWeight: '600',
    color: LIME,
    flexShrink: 1,
  },
  bannerMiddleRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 10,
  },
  bannerCropName: {
    flex: 1,
    fontSize: 22,
    fontWeight: '700',
    color: '#ffffff',
    letterSpacing: -0.2,
  },
  bannerFamilyPill: {
    paddingHorizontal: 10,
    paddingVertical: 3,
    borderRadius: 999,
    backgroundColor: '#314020',
    borderWidth: 1,
    borderColor: '#485b32',
  },
  bannerFamilyText: {
    fontSize: 11,
    fontWeight: '600',
    color: '#c2d2b0',
  },
  bannerMetricStrip: {
    flexDirection: 'row',
    alignItems: 'stretch',
    borderRadius: 14,
    backgroundColor: '#1a2310',
    borderWidth: 1,
    borderColor: '#354424',
    paddingVertical: 10,
    paddingHorizontal: 10,
  },
  bannerMetricColWide: {
    flex: 1.35,
    justifyContent: 'center',
    gap: 2,
  },
  bannerMetricCol: {
    flex: 0.9,
    justifyContent: 'center',
    gap: 2,
  },
  bannerMetricDivider: {
    width: 1,
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
    marginHorizontal: 8,
  },
  bannerMetricLabel: {
    fontSize: 9.5,
    fontWeight: '700',
    letterSpacing: 0.7,
    color: '#8fa07e',
  },
  bannerMetricValue: {
    fontSize: 12.5,
    fontWeight: '700',
    lineHeight: 16,
    color: '#f1f4e6',
  },
  bannerMetricValueAccent: {
    color: LIME,
  },

  carouselContainer: {
    width: '100%',
    height: 198,
    borderRadius: 22,
    backgroundColor: '#232f17',
    borderColor: '#4c6132',
    borderWidth: 1,
    paddingTop: 10,
    paddingBottom: 10,
    justifyContent: 'space-between',
    overflow: 'hidden',
  },
  carouselHeader: {
    paddingHorizontal: 16,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 8,
    zIndex: 10,
  },
  carouselTitle: {
    fontSize: 13.5,
    fontWeight: '600',
    color: '#dce8ce',
  },
  carouselHeaderRight: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
  },
  resetPill: {
    paddingHorizontal: 9,
    paddingVertical: 3,
    borderRadius: 999,
    backgroundColor: 'rgba(184, 243, 52, 0.12)',
    borderWidth: 1,
    borderColor: 'rgba(184, 243, 52, 0.35)',
  },
  resetText: {
    fontSize: 10.5,
    fontWeight: '600',
    color: LIME,
  },
  stageCountPill: {
    paddingHorizontal: 9,
    paddingVertical: 3,
    borderRadius: 999,
    backgroundColor: '#2f3d1f',
    borderWidth: 1,
    borderColor: '#45572f',
  },
  counterText: {
    fontSize: 10.5,
    fontWeight: '600',
    color: '#b8c8a6',
  },

  trackStage: {
    width: '100%',
    height: TRACK_HEIGHT,
    overflow: 'hidden',
    position: 'relative',
  },
  centerHalo: {
    position: 'absolute',
    top: (TRACK_HEIGHT - 122) / 2,
    width: 124,
    height: 122,
    borderRadius: 22,
    backgroundColor: 'rgba(184, 243, 52, 0.12)',
  },
  cardsTrack: {
    width: '100%',
    height: '100%',
    position: 'relative',
  },
  slotCardPosition: {
    position: 'absolute',
    top: (TRACK_HEIGHT - CARD_HEIGHT) / 2,
    left: 0,
    width: CARD_WIDTH,
    height: CARD_HEIGHT,
  },
  slotCard: {
    width: CARD_WIDTH,
    height: CARD_HEIGHT,
    borderRadius: 16,
    padding: 10,
    justifyContent: 'space-between',
  },
  slotCardFocal: {
    backgroundColor: '#3c511e',
    borderWidth: 1.8,
    borderColor: LIME,
    shadowColor: LIME,
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.24,
    shadowRadius: 10,
    elevation: 6,
  },
  slotCardLeftShrunk: {
    backgroundColor: 'rgba(33, 43, 21, 0.88)',
    borderWidth: 1,
    borderColor: 'rgba(61, 77, 41, 0.85)',
  },
  slotCardDefault: {
    backgroundColor: 'rgba(43, 55, 28, 0.95)',
    borderWidth: 1,
    borderColor: '#495c32',
  },
  slotTopRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 4,
  },
  slotOrder: {
    fontSize: 12,
    fontWeight: '600',
  },
  slotOrderFocal: {
    color: '#d8e8c5',
  },
  slotOrderMuted: {
    color: '#97a786',
  },
  statusBadge: {
    paddingHorizontal: 7,
    paddingVertical: 2,
    borderRadius: 999,
  },
  statusBadgeCurrentFocal: {
    backgroundColor: '#314218',
    borderWidth: 1,
    borderColor: '#658038',
  },
  statusBadgeCurrent: {
    backgroundColor: '#2a3619',
  },
  statusBadgeText: {
    fontSize: 9.5,
    fontWeight: '600',
  },
  statusTextCurrentFocal: {
    color: '#e7f7c8',
  },
  statusTextCurrent: {
    color: '#a8b897',
  },
  statusBadgeFocus: {
    paddingHorizontal: 6,
    paddingVertical: 2,
    borderRadius: 999,
    backgroundColor: 'rgba(184, 243, 52, 0.2)',
    borderWidth: 1,
    borderColor: 'rgba(184, 243, 52, 0.42)',
  },
  statusTextFocus: {
    fontSize: 9.5,
    fontWeight: '700',
    color: LIME,
  },
  slotBottomRow: {
    marginTop: 'auto',
  },
  slotCropName: {
    fontWeight: '700',
    lineHeight: 17,
  },
  slotCropNameCompact: {
    fontSize: 13,
  },
  slotCropNameRegular: {
    fontSize: 14,
  },
  slotCropNameAccent: {
    color: LIME,
  },
  slotCropNameWhite: {
    color: '#ffffff',
  },
  slotCropNameMuted: {
    color: 'rgba(255, 255, 255, 0.9)',
  },
  slotSeason: {
    fontSize: 10.5,
    marginTop: 2,
  },
  slotSeasonFocal: {
    color: '#c2d1b2',
  },
  slotSeasonMuted: {
    color: '#8fa07e',
  },
  arrowContainer: {
    position: 'absolute',
    top: (TRACK_HEIGHT - ARROW_HEIGHT) / 2,
    left: 0,
    width: ARROW_WIDTH,
    height: ARROW_HEIGHT,
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 10,
  },

  carouselFooter: {
    paddingHorizontal: 16,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 8,
  },
  footerHint: {
    fontSize: 10.5,
    color: '#8fa07e',
  },
  dotsRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
  },
  dot: {
    height: 6,
    borderRadius: 999,
  },
  dotActive: {
    width: 16,
    backgroundColor: LIME,
  },
  dotInactive: {
    width: 6,
    backgroundColor: '#536441',
  },

  alternativesList: {
    gap: 10,
  },
  alternativeCard: {
    width: '100%',
    borderRadius: 20,
    padding: 14,
    borderWidth: 1,
    gap: 10,
  },
  alternativeCardSelected: {
    backgroundColor: '#2a3819',
    borderColor: LIME,
    borderWidth: 1.5,
  },
  alternativeCardBest: {
    backgroundColor: '#233015',
    borderColor: 'rgba(184, 243, 52, 0.45)',
  },
  alternativeCardUnselected: {
    backgroundColor: 'rgba(31, 41, 20, 0.92)',
    borderColor: '#374727',
  },
  alternativeHeaderRow: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
    gap: 10,
  },
  alternativeLeftCol: {
    flex: 1,
    minWidth: 0,
    gap: 2,
  },
  bestTagText: {
    fontSize: 10.5,
    fontWeight: '700',
    letterSpacing: 0.5,
    color: LIME,
  },
  alternativePeriod: {
    fontSize: 11,
    fontWeight: '500',
    color: '#9eb08e',
  },
  alternativeTitle: {
    fontSize: 16,
    fontWeight: '700',
    color: '#ffffff',
  },
  alternativeMeta: {
    fontSize: 11.5,
    color: '#9eb08e',
  },
  alternativeRightCol: {
    alignItems: 'flex-end',
    gap: 6,
    flexShrink: 0,
  },
  selectedPill: {
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: 999,
    backgroundColor: LIME,
  },
  selectedPillText: {
    fontSize: 11,
    fontWeight: '700',
    color: '#161f0a',
  },
  selectPill: {
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: 999,
    backgroundColor: '#313d21',
    borderWidth: 1,
    borderColor: '#455431',
  },
  selectPillText: {
    fontSize: 11,
    fontWeight: '600',
    color: 'rgba(255, 255, 255, 0.9)',
  },
  alternativeBadge: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 999,
    backgroundColor: '#1c2511',
    borderWidth: 1,
    borderColor: '#3b4c28',
    maxWidth: 170,
  },
  alternativeBadgeText: {
    fontSize: 10.5,
    fontWeight: '600',
    color: '#d2e2bf',
    flexShrink: 1,
  },
  sequenceWrap: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    alignItems: 'center',
    rowGap: 6,
    columnGap: 5,
  },
  sequenceItemRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
  },
  sequencePill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 999,
    backgroundColor: '#1b2411',
    borderWidth: 1,
    borderColor: '#394827',
  },
  sequencePillFirst: {
    backgroundColor: 'rgba(184, 243, 52, 0.12)',
    borderColor: 'rgba(184, 243, 52, 0.38)',
  },
  sequencePillOrder: {
    fontSize: 10,
    fontWeight: '700',
    color: '#93a581',
  },
  sequencePillOrderFirst: {
    color: LIME,
  },
  sequencePillText: {
    fontSize: 11.5,
    fontWeight: '600',
    color: '#e5ecd8',
  },
  sequencePillTextFirst: {
    color: LIME,
  },
  sequenceArrow: {
    fontSize: 12,
    fontWeight: '700',
    color: '#7f9369',
  },

  filterBarScroll: {
    width: '100%',
    flexGrow: 0,
  },
  filterBarContent: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
    paddingVertical: 2,
  },
  filterPill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: 12,
    paddingVertical: 7,
    borderRadius: 999,
    borderWidth: 1,
  },
  filterPillActive: {
    backgroundColor: LIME,
    borderColor: LIME,
  },
  filterPillInactive: {
    backgroundColor: '#222b15',
    borderColor: '#334022',
  },
  filterPillText: {
    fontSize: 12,
    fontWeight: '600',
  },
  filterPillTextActive: {
    color: '#18200e',
    fontWeight: '700',
  },
  filterPillTextInactive: {
    color: '#dfe8cf',
  },

  builderCard: {
    width: '100%',
    borderRadius: 20,
    backgroundColor: '#212c15',
    borderWidth: 1,
    borderColor: '#3a4b26',
    padding: 12,
    gap: 10,
  },
  builderCardActive: {
    backgroundColor: '#253214',
    borderWidth: 1.5,
    borderColor: 'rgba(184, 243, 52, 0.72)',
  },
  builderCustomBlock: {
    gap: 8,
  },
  builderCustomHeader: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    justifyContent: 'space-between',
    gap: 10,
  },
  builderCustomHeaderLeft: {
    flex: 1,
    minWidth: 0,
    gap: 4,
  },
  builderBadgeRow: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    alignItems: 'center',
    gap: 6,
  },
  builderCustomBadge: {
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 999,
    backgroundColor: 'rgba(184, 243, 52, 0.16)',
    borderWidth: 1,
    borderColor: 'rgba(184, 243, 52, 0.42)',
  },
  builderCustomBadgeText: {
    fontSize: 9.5,
    fontWeight: '700',
    letterSpacing: 0.45,
    color: LIME,
  },
  builderRankMeta: {
    fontSize: 11.5,
    fontWeight: '700',
    color: '#e5ecd8',
  },
  builderChainText: {
    fontSize: 13.5,
    fontWeight: '700',
    color: '#ffffff',
    lineHeight: 18,
  },
  builderEditPill: {
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 999,
    backgroundColor: '#314020',
    borderWidth: 1,
    borderColor: '#485b32',
    flexShrink: 0,
  },
  builderEditPillText: {
    fontSize: 11,
    fontWeight: '600',
    color: '#e5ecd8',
  },
  builderEmptyRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 10,
  },
  builderEmptyLeft: {
    flex: 1,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
    minWidth: 0,
  },
  builderEmptyIconWrap: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: 'rgba(184, 243, 52, 0.12)',
    borderWidth: 1,
    borderColor: 'rgba(184, 243, 52, 0.3)',
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  },
  builderEmptyCopy: {
    flex: 1,
    minWidth: 0,
    gap: 1,
  },
  builderEmptyTitle: {
    fontSize: 13.5,
    fontWeight: '700',
    color: '#ffffff',
  },
  builderEmptySubtitle: {
    fontSize: 11,
    color: '#9eb08e',
    lineHeight: 15,
  },
  pickCropsPill: {
    paddingHorizontal: 11,
    paddingVertical: 6,
    borderRadius: 999,
    backgroundColor: LIME,
    flexShrink: 0,
  },
  pickCropsPillText: {
    fontSize: 11.5,
    fontWeight: '700',
    color: '#18200e',
  },
  comparisonPill: {
    borderRadius: 12,
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderWidth: 1,
  },
  comparisonPillLime: {
    backgroundColor: 'rgba(184, 243, 52, 0.1)',
    borderColor: 'rgba(184, 243, 52, 0.34)',
  },
  comparisonPillAmber: {
    backgroundColor: 'rgba(245, 196, 81, 0.1)',
    borderColor: 'rgba(245, 196, 81, 0.34)',
  },
  comparisonPillText: {
    fontSize: 11.5,
    fontWeight: '600',
    lineHeight: 16,
  },
  comparisonPillTextLime: {
    color: LIME,
  },
  comparisonPillTextAmber: {
    color: '#f5c451',
  },
  smartSwapChip: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    borderRadius: 12,
    paddingHorizontal: 10,
    paddingVertical: 7,
    backgroundColor: 'rgba(184, 243, 52, 0.14)',
    borderWidth: 1,
    borderColor: 'rgba(184, 243, 52, 0.45)',
  },
  smartSwapChipText: {
    flex: 1,
    fontSize: 11.5,
    fontWeight: '700',
    color: '#eaf7c4',
    lineHeight: 16,
  },
  builderDrawer: {
    borderTopWidth: 1,
    borderTopColor: 'rgba(255, 255, 255, 0.08)',
    paddingTop: 10,
    gap: 10,
  },
  pinnedCropPill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    alignSelf: 'flex-start',
    paddingHorizontal: 10,
    paddingVertical: 5,
    borderRadius: 999,
    backgroundColor: '#1b2411',
    borderWidth: 1,
    borderColor: 'rgba(184, 243, 52, 0.35)',
  },
  pinnedCropText: {
    fontSize: 11,
    fontWeight: '600',
    color: '#d8e8c5',
  },
  cropGrid: {
    flexDirection: 'row',
    flexWrap: 'wrap',
    gap: 6,
  },
  cropPickerPill: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 5,
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 999,
    borderWidth: 1,
  },
  cropPickerPillSelected: {
    backgroundColor: LIME,
    borderColor: LIME,
  },
  cropPickerPillPinned: {
    backgroundColor: 'rgba(184, 243, 52, 0.14)',
    borderColor: 'rgba(184, 243, 52, 0.4)',
    opacity: 0.78,
  },
  cropPickerPillUnselected: {
    backgroundColor: '#222b15',
    borderColor: '#334022',
  },
  cropPickerName: {
    fontSize: 12,
    fontWeight: '600',
  },
  cropPickerNameSelected: {
    color: '#18200e',
    fontWeight: '700',
  },
  cropPickerNameUnselected: {
    color: '#f1f4e6',
  },
  cropPickerTag: {
    fontSize: 9.5,
    fontWeight: '600',
    paddingHorizontal: 5,
    paddingVertical: 1,
    borderRadius: 999,
    overflow: 'hidden',
  },
  cropPickerTagSelected: {
    color: '#253214',
    backgroundColor: 'rgba(24, 32, 14, 0.14)',
  },
  cropPickerTagUnselected: {
    color: '#9eb08e',
    backgroundColor: 'rgba(255, 255, 255, 0.06)',
  },
  drawerFooterRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: 10,
  },
  drawerFooterLeft: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 10,
  },
  drawerSelectionCount: {
    fontSize: 11.5,
    fontWeight: '600',
    color: '#9eb08e',
  },
  drawerResetBtn: {
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: 999,
    backgroundColor: '#2d391e',
  },
  drawerResetText: {
    fontSize: 11,
    fontWeight: '600',
    color: '#e5ecd8',
  },
  drawerDonePill: {
    paddingHorizontal: 14,
    paddingVertical: 6,
    borderRadius: 999,
    backgroundColor: LIME,
  },
  drawerDoneText: {
    fontSize: 12,
    fontWeight: '700',
    color: '#18200e',
  },

  alternativeCardCustom: {
    backgroundColor: '#253214',
    borderColor: LIME,
    borderWidth: 1.5,
  },
  alternativeCardCustomSelected: {
    backgroundColor: '#253214',
    borderColor: '#e2ff66',
    borderWidth: 1.5,
  },
  customTitleRow: {
    flexDirection: 'row',
    alignItems: 'baseline',
    gap: 8,
    flexWrap: 'wrap',
  },
  customTitleScore: {
    fontSize: 12.5,
    fontWeight: '700',
    color: LIME,
  },
});
