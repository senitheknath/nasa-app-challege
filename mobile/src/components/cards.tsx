import { type ReactNode } from 'react';
import { Pressable, StyleSheet, View } from 'react-native';
import type { ExpiryBarMetrics, ExpiryUrgency } from '@/features/plan/expiryExplain';
import type { SlotUncertaintyCone } from '@/features/plan/model';
import { strings } from '@/i18n/strings';
import { colors, icons, motion, radius, size, space } from '@/theme/tokens';
import { useTheme } from '@/theme/useTheme';
import { Icon, type IconName } from './Icon';
import { Chip, Label, Surface } from './primitives';

const AMBER = '#F5C451';
const AMBER_FILL = 'rgba(245, 196, 81, 0.14)';
const AMBER_BORDER = 'rgba(245, 196, 81, 0.45)';

export function Logo() {
  return (
    <View style={styles.line}>
      <Surface kind="glass" rounding={radius.pill} style={styles.logoIcon}><Icon name="sprout" color={colors.accent} /></Surface>
      <View>
        <Label variant="brand">{strings.brand}</Label>
        <Label variant="brandSub" tone="sage" style={styles.tag}>{strings.brandSub}</Label>
      </View>
    </View>
  );
}

export function SeasonBadge({ label }: { label: string }) {
  return (
    <Surface kind="glass" rounding={radius.pill} style={styles.season}>
      <View style={styles.dot} />
      <Label variant="badge" style={styles.breakable}>{label}</Label>
    </Surface>
  );
}

export function Workflow({ items }: { items: readonly { label: string; icon: IconName }[] }) {
  return (
    <Surface kind="glass" style={styles.workflow}>
      {items.map((item, index) => (
        <View key={item.label} style={[styles.workflowItem, index !== items.length - 1 && styles.workflowStretch]}>
          <View style={styles.workflowStep}>
            <View style={styles.workflowIcon}><Icon name={item.icon} color={colors.accent} /></View>
            <Label variant="label" style={styles.centerText}>{item.label}</Label>
          </View>
          {index !== items.length - 1 && <View style={styles.connector} />}
        </View>
      ))}
    </Surface>
  );
}

export function ChoiceCard({ selected, onPress, tag, tagRight, title, details, kind = 'strategy' }: {
  selected: boolean; onPress: () => void; tag: string; tagRight?: ReactNode; title: string; details: ReactNode; kind?: 'strategy' | 'crop';
}) {
  const { reducedMotion } = useTheme();
  return (
    <Pressable accessibilityRole="button" accessibilityState={{ selected }} aria-pressed={selected} onPress={onPress}
      style={({ pressed }) => pressed && !reducedMotion && styles.pressed}>
      <Surface kind={selected ? 'selected' : 'card'} style={[styles.selection, kind === 'strategy' && styles.strategy]}>
        <View style={styles.selectionBody}>
          <View style={styles.tagRow}>
            <Label variant="tag" tone="sage" style={styles.breakable}>{tag}</Label>
            {tagRight}
          </View>
          <Label variant={kind === 'strategy' ? 'strategy' : 'cardTitle'} style={styles.tag}>{title}</Label>
          {details}
        </View>
        <View style={[styles.selectIcon, kind === 'strategy' && styles.largeSelectIcon, selected && styles.selectedIcon]}>
          <Icon name={selected ? 'check' : 'diagonal'} color={selected ? colors.forest950 : colors.cream} />
        </View>
      </Surface>
    </Pressable>
  );
}

export function StrategyCard({ selected, onPress, tag, title, description }: {
  selected: boolean; onPress: () => void; tag: string; title: string; description: string;
}) {
  return <ChoiceCard selected={selected} onPress={onPress} tag={tag} title={title}
    details={<Label variant="detail" tone="sage" style={styles.tag}>{description}</Label>} />;
}

export function CropCard({
  selected,
  onPress,
  category,
  family,
  name,
  scientificName,
  cropYield,
  growthDays,
  suitability,
  reason,
  waterLabel,
}: {
  selected: boolean;
  onPress: () => void;
  category: string;
  family?: string;
  name: string;
  scientificName?: string;
  botanicalSummary?: string;
  coverageValue?: number;
  coverageLabel?: string;
  cropYield: string;
  growthDays?: string;
  suitability?: string;
  reason?: string;
  water: number;
  waterLabel: string;
}) {
  const headerTag = family ? `${category} · ${family}` : category;
  const suitabilityLabel = suitability === 'possible'
    ? 'Optimal fit'
    : suitability === 'check'
      ? 'Climate check'
      : undefined;

  return (
    <ChoiceCard
      kind="crop"
      selected={selected}
      onPress={onPress}
      tag={headerTag}
      tagRight={suitabilityLabel ? (
        <View style={[styles.suitabilityBadge, suitability === 'possible' ? styles.suitabilityOptimal : styles.suitabilityCheck]}>
          <Label variant="smallBold" tone={suitability === 'possible' ? 'accent' : 'cream'}>
            {suitabilityLabel}
          </Label>
        </View>
      ) : undefined}
      title={name}
      details={
        <>
          {scientificName ? <Label variant="caption" tone="sage">{scientificName}</Label> : null}
          <View style={[styles.cropFacts, !reason && styles.cropFactsCompact]}>
            <View style={styles.fact}>
              <Icon name="sprout" size={icons.small} color={colors.sage} />
              <Label variant="caption" tone="sage">{cropYield}</Label>
            </View>
            {growthDays ? (
              <View style={styles.fact}>
                <Icon name="calendar" size={icons.small} color={colors.sage} />
                <Label variant="caption" tone="sage">{growthDays}</Label>
              </View>
            ) : null}
            <View style={styles.fact}>
              <Icon name="drop" size={icons.small} color={colors.sage} />
              <Label variant="caption" tone="sage">{waterLabel}</Label>
            </View>
          </View>
          {reason ? (
            <Label variant="caption" tone="sage" numberOfLines={2} style={styles.cropReason}>
              {reason}
            </Label>
          ) : null}
        </>
      }
    />
  );
}

export type TimelineStage = {
  stage: string;
  label: string;
  durationDays: number;
  startDate: string;
  endDate: string;
  percent?: number;
};

const STAGE_COLORS = [
  colors.sage,
  colors.forest700,
  colors.accent,
  colors.cream,
] as const;

const SHORT_STAGE_NAMES: Record<string, string> = {
  initial: 'Initial',
  init: 'Initial',
  crop_development: 'Develop',
  development: 'Develop',
  canopy: 'Develop',
  dev: 'Develop',
  mid_season: 'Mid-Season',
  'mid-season': 'Mid-Season',
  mid: 'Mid-Season',
  late_season: 'Late',
  'late-season': 'Late',
  late: 'Late',
  ripening: 'Late',
};

function shortStageLabel(stage: string, fallback: string): string {
  const key = stage.trim().toLowerCase().replace(/\s+/g, '_');
  return SHORT_STAGE_NAMES[key] ?? fallback;
}

function urgencyDotColor(urgency?: ExpiryUrgency): string {
  if (urgency === 'critical') return colors.danger;
  if (urgency === 'tight') return AMBER;
  return colors.accent;
}

export function TimelineCard({
  season,
  crop,
  summary,
  note,
  first,
  dateSpan,
  harvestWindow,
  family,
  growthDays,
  stages,
  turnaround,
  expiry,
  collisionPct,
  safeExpiryDate,
  hardExpiryDate,
  delaySlackDays,
  uncertaintyCone,
  urgency,
  explanation,
  safeCountdownLabel,
  hardCountdownLabel,
  barMetrics,
}: {
  season: string;
  crop: string;
  summary: string;
  note: string;
  first: boolean;
  dateSpan?: string;
  harvestWindow?: string;
  family?: string;
  growthDays?: string;
  stages?: readonly TimelineStage[];
  turnaround?: string;
  expiry?: string;
  collisionPct?: number;
  safeExpiryDate?: string;
  hardExpiryDate?: string;
  delaySlackDays?: number;
  uncertaintyCone?: SlotUncertaintyCone;
  urgency?: ExpiryUrgency;
  explanation?: string;
  safeCountdownLabel?: string;
  hardCountdownLabel?: string;
  barMetrics?: ExpiryBarMetrics;
}) {
  const hasRichDetails = Boolean(
    dateSpan ||
      harvestWindow ||
      family ||
      growthDays ||
      stages?.length ||
      turnaround ||
      expiry ||
      collisionPct != null ||
      safeExpiryDate ||
      hardExpiryDate ||
      delaySlackDays != null ||
      uncertaintyCone ||
      urgency ||
      explanation,
  );

  if (!hasRichDetails) {
    return (
      <Surface rounding={radius.tile} style={styles.timeline}>
        <View style={styles.selectionBody}>
          <Label variant="label" tone="sage">{season}</Label>
          <Label variant="action">{crop}</Label>
          <Label variant="caption" tone="sage">{summary}</Label>
        </View>
        <View style={styles.timelineNote}><Chip label={note} accent={first} /></View>
      </Surface>
    );
  }

  const totalDays = stages?.reduce((sum, item) => sum + Math.max(0, item.durationDays), 0) ?? 0;
  const hasUncertaintyRange = Boolean(
    uncertaintyCone &&
      (uncertaintyCone.earlyEndDate ||
        uncertaintyCone.nominalEndDate ||
        uncertaintyCone.lateEndDate ||
        uncertaintyCone.spanDays != null),
  );
  const earlyPct = Math.max(4, Math.min(45, barMetrics?.earlyMarkerPct ?? 15));
  const latePct = Math.max(earlyPct + 10, Math.min(96, barMetrics?.lateMarkerPct ?? 85));
  const nominalPct = Math.max(earlyPct, Math.min(latePct, barMetrics?.nominalMarkerPct ?? 50));

  const hasExpiryPills = Boolean(
    safeExpiryDate ||
      hardExpiryDate ||
      expiry ||
      delaySlackDays != null ||
      collisionPct != null ||
      turnaround,
  );

  return (
    <Surface kind={first ? 'selected' : 'card'} rounding={radius.tile} style={styles.richTimeline}>
      <View style={styles.timelineTopRow}>
        <View style={styles.timelineMetaLeft}>
          <View style={[styles.stagePill, first ? styles.stagePillFirst : styles.stagePillNext]}>
            <Label variant="smallBold" tone={first ? 'forest950' : 'cream'}>{note}</Label>
          </View>
          <Label variant="caption" tone="sage" numberOfLines={1} style={styles.breakable}>{season}</Label>
        </View>
        {!!family && (
          <View style={styles.familyTag}>
            <Label variant="label" tone="sage" numberOfLines={1}>{family}</Label>
          </View>
        )}
      </View>

      <View style={styles.timelineMainRow}>
        <Label variant="cardTitle" tone={first ? 'accent' : 'cream'} style={styles.timelineCropName}>
          {crop}
        </Label>
        {!!summary && (
          <View style={styles.durationPill}>
            <Label variant="smallBold" tone="cream">{summary}</Label>
          </View>
        )}
      </View>

      {(!!dateSpan || !!harvestWindow) && (
        <View style={styles.dateRangeBar}>
          {!!dateSpan && (
            <View style={styles.dateRangeRow}>
              <Icon name="calendar" size={icons.badge} color={colors.accent} />
              <Label variant="caption" tone="cream" style={styles.breakable}>{dateSpan}</Label>
            </View>
          )}
          {!!harvestWindow && (
            <View style={styles.harvestBadge}>
              <Label variant="label" tone="sage" numberOfLines={1}>Harvest: {harvestWindow}</Label>
            </View>
          )}
        </View>
      )}

      {!!stages?.length && (
        <View style={styles.stagesBlock}>
          <View style={styles.stageBar}>
            {stages.map((item, idx) => {
              const flexWeight = item.percent ?? (totalDays > 0 ? Math.max(8, Math.round((item.durationDays / totalDays) * 100)) : 25);
              return (
                <View
                  key={`${item.stage}-${idx}`}
                  style={[
                    styles.stageSegment,
                    { flex: flexWeight, backgroundColor: STAGE_COLORS[idx % STAGE_COLORS.length] },
                  ]}
                />
              );
            })}
          </View>
          <View style={styles.stageLegend}>
            {stages.map((item, idx) => (
              <View key={`${item.stage}-legend-${idx}`} style={styles.stageCol}>
                <View style={styles.stageTitleRow}>
                  <View style={[styles.stageDot, { backgroundColor: STAGE_COLORS[idx % STAGE_COLORS.length] }]} />
                  <Label variant="label" tone="sage" numberOfLines={1} style={styles.breakable}>
                    {shortStageLabel(item.stage, item.label)}
                  </Label>
                </View>
                <Label variant="smallBold" tone="cream">{item.durationDays}d</Label>
              </View>
            ))}
          </View>
        </View>
      )}

      {hasUncertaintyRange && (
        <View style={styles.uncertaintyBox}>
          <View style={styles.uncertaintyHeader}>
            <Label variant="label" tone="sage">HARVEST UNCERTAINTY</Label>
            <Label variant="smallBold" tone="accent">
              {uncertaintyCone?.spanDays != null ? `${uncertaintyCone.spanDays}d spread` : 'Maturity range'}
            </Label>
          </View>
          <View style={styles.uncertaintyTrack}>
            <View
              style={[
                styles.uncertaintySpan,
                { left: `${earlyPct}%`, width: `${Math.max(8, latePct - earlyPct)}%` },
              ]}
            />
            <View style={[styles.uncertaintyNominalDot, { left: `${nominalPct}%` }]} />
          </View>
          <View style={styles.uncertaintyLabelsRow}>
            <View style={styles.uncertaintyCol}>
              <Label variant="label" tone="muted">Early</Label>
              <Label variant="caption" tone="cream" numberOfLines={1}>
                {uncertaintyCone?.earlyEndDate ?? strings.noValue}
              </Label>
            </View>
            <View style={[styles.uncertaintyCol, styles.uncertaintyColCenter]}>
              <Label variant="label" tone="accent">Nominal</Label>
              <Label variant="caption" tone="accent" numberOfLines={1}>
                {uncertaintyCone?.nominalEndDate ?? strings.noValue}
              </Label>
            </View>
            <View style={[styles.uncertaintyCol, styles.uncertaintyColEnd]}>
              <Label variant="label" tone="muted">Late</Label>
              <Label variant="caption" tone="cream" numberOfLines={1}>
                {uncertaintyCone?.lateEndDate ?? strings.noValue}
              </Label>
            </View>
          </View>
        </View>
      )}

      {hasExpiryPills && (
        <View style={styles.expiryPillsWrap}>
          {!!safeExpiryDate && (
            <View
              style={[
                styles.expiryPill,
                urgency === 'tight' && styles.expiryPillTight,
                urgency === 'critical' && styles.expiryPillCritical,
                (!urgency || urgency === 'safe') && styles.expiryPillSafe,
              ]}
            >
              <Label variant="label" tone="sage">Safe Expiry</Label>
              <Label variant="smallBold" tone="cream">
                {safeExpiryDate}
                {safeCountdownLabel ? ` · ${safeCountdownLabel}` : ''}
              </Label>
            </View>
          )}
          {!!hardExpiryDate && (
            <View
              style={[
                styles.expiryPill,
                urgency === 'critical' ? styles.expiryPillCritical : styles.expiryPillNeutral,
              ]}
            >
              <Label variant="label" tone="sage">Hard Expiry</Label>
              <Label variant="smallBold" tone={urgency === 'critical' ? 'danger' : 'cream'}>
                {hardExpiryDate}
                {hardCountdownLabel ? ` · ${hardCountdownLabel}` : ''}
              </Label>
            </View>
          )}
          {!safeExpiryDate && !hardExpiryDate && !!expiry && (
            <View style={[styles.expiryPill, styles.expiryPillNeutral]}>
              <Label variant="label" tone="sage">Expiry</Label>
              <Label variant="smallBold" tone="cream">{expiry}</Label>
            </View>
          )}
          {delaySlackDays != null && (
            <View style={[styles.expiryPill, styles.expiryPillNeutral]}>
              <Label variant="label" tone="sage">Slack</Label>
              <Label variant="smallBold" tone="cream">{Math.round(delaySlackDays)}d</Label>
            </View>
          )}
          {collisionPct != null && (
            <View
              style={[
                styles.expiryPill,
                urgency === 'critical'
                  ? styles.expiryPillCritical
                  : urgency === 'tight'
                    ? styles.expiryPillTight
                    : styles.expiryPillSafe,
              ]}
            >
              <Label variant="label" tone="sage">Collision</Label>
              <Label
                variant="smallBold"
                tone={urgency === 'critical' ? 'danger' : urgency === 'safe' ? 'accent' : 'cream'}
              >
                {Math.round(collisionPct)}%
              </Label>
            </View>
          )}
          {!!turnaround && (
            <View style={[styles.expiryPill, styles.expiryPillNeutral]}>
              <Label variant="label" tone="sage">Turnaround</Label>
              <Label variant="smallBold" tone="cream">{turnaround}</Label>
            </View>
          )}
        </View>
      )}

      {!!explanation && (
        <View
          style={[
            styles.explanationBox,
            urgency === 'critical'
              ? styles.explanationCritical
              : urgency === 'tight'
                ? styles.explanationTight
                : styles.explanationSafe,
          ]}
        >
          <View style={[styles.explanationDot, { backgroundColor: urgencyDotColor(urgency) }]} />
          <Label variant="caption" tone="cream" style={styles.explanationText}>
            {explanation}
          </Label>
        </View>
      )}
    </Surface>
  );
}

export function ActionCard({ label, prefix, action, season }: { label: string; prefix: string; action: string; season: string }) {
  return (
    <Surface kind="highlight" rounding={radius.tile} style={styles.action}>
      <Label variant="caption" tone="sage">{label}</Label>
      <Label variant="action">{prefix}<Label variant="action" tone="accent">{action}</Label></Label>
      <Label variant="caption" tone="sage">{season}</Label>
    </Surface>
  );
}

const styles = StyleSheet.create({
  line: { flexDirection: 'row', alignItems: 'center', gap: space.snug },
  logoIcon: { width: size.touch, height: size.touch, alignItems: 'center', justifyContent: 'center' },
  tag: { marginTop: space.xs },
  season: { minHeight: size.touch, paddingHorizontal: space.lg, paddingVertical: space.sm, flexDirection: 'row', alignItems: 'center', gap: space.sm, flexShrink: 1 },
  breakable: { flexShrink: 1 },
  dot: { height: size.dot, width: size.dot, backgroundColor: colors.accent, borderRadius: radius.pill },
  workflow: { flexDirection: 'row', alignItems: 'center', padding: space.lg },
  workflowItem: { flexDirection: 'row', alignItems: 'center' },
  workflowStretch: { flex: 1 },
  workflowStep: { alignItems: 'center', gap: space.sm, width: size.workflow, flexShrink: 1 },
  workflowIcon: { width: size.control, height: size.control, borderRadius: radius.pill, backgroundColor: colors.innerDark, alignItems: 'center', justifyContent: 'center' },
  centerText: { textAlign: 'center' },
  connector: { flex: 1, height: size.hairline, backgroundColor: colors.segment, marginTop: -space.gutter },
  selection: { flexDirection: 'row', alignItems: 'flex-start', gap: space.md, padding: space.lg },
  strategy: { alignItems: 'center', paddingHorizontal: space.gutter, paddingVertical: space.gutter + space.xxs },
  selectionBody: { flex: 1, minWidth: 0 },
  tagRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: space.sm },
  suitabilityBadge: { paddingHorizontal: space.sm, paddingVertical: space.xxs, borderRadius: radius.pill, borderWidth: size.hairline },
  suitabilityOptimal: { backgroundColor: colors.highlight, borderColor: colors.accentBorder },
  suitabilityCheck: { backgroundColor: colors.chip, borderColor: colors.border },
  selectIcon: { width: size.touch, height: size.touch, borderRadius: radius.pill, backgroundColor: colors.chip, justifyContent: 'center', alignItems: 'center' },
  largeSelectIcon: { width: size.control, height: size.control },
  selectedIcon: { backgroundColor: colors.accent },
  pressed: { transform: [{ scale: motion.pressScale }] },
  cropFacts: { flexDirection: 'row', flexWrap: 'wrap', gap: space.lg, marginTop: space.sm, marginBottom: space.sm },
  cropFactsCompact: { marginBottom: 0 },
  cropReason: { marginBottom: space.xs },
  fact: { flexDirection: 'row', alignItems: 'center', gap: space.tight, flexShrink: 1 },
  timeline: { flexDirection: 'row', alignItems: 'center', gap: space.md, padding: space.lg },
  richTimeline: { padding: space.lg, gap: space.md },
  timelineTopRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: space.sm },
  timelineMetaLeft: { flexDirection: 'row', alignItems: 'center', gap: space.sm, flex: 1, minWidth: 0 },
  stagePill: { paddingHorizontal: space.md, paddingVertical: space.xxs, borderRadius: radius.pill },
  stagePillFirst: { backgroundColor: colors.accent },
  stagePillNext: { backgroundColor: colors.chip, borderWidth: size.hairline, borderColor: colors.border },
  familyTag: { paddingHorizontal: space.sm, paddingVertical: space.xxs, borderRadius: radius.pill, backgroundColor: colors.innerDark, borderWidth: size.hairline, borderColor: colors.border, maxWidth: '45%' },
  timelineMainRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: space.sm, flexWrap: 'wrap' },
  timelineCropName: { flex: 1, minWidth: 120 },
  durationPill: { paddingHorizontal: space.md, paddingVertical: space.xs, borderRadius: radius.pill, backgroundColor: colors.innerDark, borderWidth: size.hairline, borderColor: colors.border },
  dateRangeBar: { flexDirection: 'row', flexWrap: 'wrap', alignItems: 'center', justifyContent: 'space-between', gap: space.sm, paddingHorizontal: space.md, paddingVertical: space.sm, borderRadius: radius.tile, backgroundColor: colors.innerDark, borderWidth: size.hairline, borderColor: colors.border },
  dateRangeRow: { flexDirection: 'row', alignItems: 'center', gap: space.tight, flexShrink: 1 },
  harvestBadge: { paddingHorizontal: space.sm, paddingVertical: space.xxs, borderRadius: radius.pill, backgroundColor: colors.chip },
  timelineNote: { maxWidth: '50%' },
  stagesBlock: { gap: space.sm, paddingTop: space.xxs },
  stageBar: { flexDirection: 'row', height: size.dot, borderRadius: radius.pill, overflow: 'hidden', gap: space.xxs },
  stageSegment: { height: '100%', borderRadius: radius.pill },
  stageLegend: { flexDirection: 'row', gap: space.xs },
  stageCol: { flex: 1, minWidth: 0, gap: space.xxs, paddingHorizontal: space.xs, paddingVertical: space.xs, borderRadius: space.md, backgroundColor: colors.innerDark },
  stageTitleRow: { flexDirection: 'row', alignItems: 'center', gap: space.xs },
  stageDot: { width: size.indicator, height: size.indicator, borderRadius: radius.pill },
  uncertaintyBox: {
    padding: space.md,
    borderRadius: radius.tile,
    backgroundColor: colors.innerDark,
    borderWidth: size.hairline,
    borderColor: colors.border,
    gap: space.sm,
  },
  uncertaintyHeader: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: space.sm },
  uncertaintyTrack: {
    height: 8,
    borderRadius: radius.pill,
    backgroundColor: colors.chip,
    position: 'relative',
    justifyContent: 'center',
  },
  uncertaintySpan: {
    position: 'absolute',
    height: 8,
    borderRadius: radius.pill,
    backgroundColor: colors.accentBorder,
    borderWidth: size.hairline,
    borderColor: colors.accent,
  },
  uncertaintyNominalDot: {
    position: 'absolute',
    width: 10,
    height: 10,
    marginLeft: -5,
    borderRadius: radius.pill,
    backgroundColor: colors.accent,
  },
  uncertaintyLabelsRow: { flexDirection: 'row', justifyContent: 'space-between', gap: space.xs },
  uncertaintyCol: { flex: 1, minWidth: 0, gap: 1 },
  uncertaintyColCenter: { alignItems: 'center' },
  uncertaintyColEnd: { alignItems: 'flex-end' },
  expiryPillsWrap: { flexDirection: 'row', flexWrap: 'wrap', gap: space.xs },
  expiryPill: {
    paddingHorizontal: space.sm,
    paddingVertical: space.xs,
    borderRadius: radius.pill,
    borderWidth: size.hairline,
    flexDirection: 'row',
    alignItems: 'center',
    gap: space.tight,
  },
  expiryPillSafe: { backgroundColor: colors.highlight, borderColor: colors.accentBorder },
  expiryPillTight: { backgroundColor: AMBER_FILL, borderColor: AMBER_BORDER },
  expiryPillCritical: { backgroundColor: colors.dangerFill, borderColor: colors.dangerBorder },
  expiryPillNeutral: { backgroundColor: colors.innerDark, borderColor: colors.border },
  explanationBox: {
    flexDirection: 'row',
    alignItems: 'flex-start',
    gap: space.sm,
    padding: space.md,
    borderRadius: radius.tile,
    borderWidth: size.hairline,
  },
  explanationSafe: { backgroundColor: colors.innerDark, borderColor: colors.accentBorder },
  explanationTight: { backgroundColor: AMBER_FILL, borderColor: AMBER_BORDER },
  explanationCritical: { backgroundColor: colors.dangerFill, borderColor: colors.dangerBorder },
  explanationDot: { width: 7, height: 7, borderRadius: 4, marginTop: 5, flexShrink: 0 },
  explanationText: { flex: 1 },
  action: { padding: space.lg, gap: space.xs },
});
