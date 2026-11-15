import { type ReactNode } from 'react';
import { Pressable, StyleSheet, View } from 'react-native';
import { strings } from '@/i18n/strings';
import { colors, icons, motion, radius, size, space } from '@/theme/tokens';
import { useTheme } from '@/theme/useTheme';
import { Icon, type IconName } from './Icon';
import { Chip, Label, Progress, Surface } from './primitives';

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
  coverageValue,
  coverageLabel,
  cropYield,
  growthDays,
  suitability,
  reason,
  water,
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
  const progressValue = coverageValue ?? water;
  const metricPrefix = coverageLabel ? strings.modelCoverage : strings.water;
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
          <View style={styles.cropFacts}>
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
          <Progress value={progressValue} label={metricPrefix} />
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
}) {
  const hasRichDetails = Boolean(
    dateSpan || harvestWindow || family || growthDays || stages?.length || turnaround || expiry || collisionPct != null,
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

  return (
    <Surface kind={first ? 'selected' : 'card'} rounding={radius.tile} style={styles.richTimeline}>
      <View style={styles.timelineHeader}>
        <View style={styles.selectionBody}>
          <Label variant="label" tone="sage">{family ? `${season} · ${family}` : season}</Label>
          <Label variant="action" tone={first ? 'accent' : 'cream'}>{crop}</Label>
          {!!dateSpan && <Label variant="caption" tone="cream">{dateSpan}</Label>}
          <Label variant="caption" tone="sage">{growthDays ? `${summary} · ${growthDays}` : summary}</Label>
          {!!harvestWindow && <Label variant="caption" tone="muted">Harvest: {harvestWindow}</Label>}
        </View>
        <View style={styles.timelineNote}><Chip label={note} accent={first} /></View>
      </View>

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
              <View key={`${item.stage}-legend-${idx}`} style={styles.stageItem}>
                <View style={styles.stageTitleRow}>
                  <View style={[styles.stageDot, { backgroundColor: STAGE_COLORS[idx % STAGE_COLORS.length] }]} />
                  <Label variant="smallBold" tone="cream">{item.label} ({item.durationDays}d)</Label>
                </View>
                <Label variant="caption" tone="sage">{item.startDate} – {item.endDate}</Label>
              </View>
            ))}
          </View>
        </View>
      )}

      {(!!turnaround || !!expiry || collisionPct != null) && (
        <View style={styles.timelineChips}>
          {!!turnaround && <Chip label={turnaround} />}
          {!!expiry && <Chip label={expiry} />}
          {collisionPct != null && (
            <View style={[styles.riskBadge, collisionPct > 25 && styles.riskBadgeDanger]}>
              <Label variant="smallBold" tone={collisionPct > 25 ? 'danger' : 'accent'}>
                {collisionPct}% risk
              </Label>
            </View>
          )}
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
  cropFacts: { flexDirection: 'row', flexWrap: 'wrap', gap: space.lg, marginTop: space.sm, marginBottom: space.md },
  cropReason: { marginBottom: space.sm },
  fact: { flexDirection: 'row', alignItems: 'center', gap: space.tight, flexShrink: 1 },
  timeline: { flexDirection: 'row', alignItems: 'center', gap: space.md, padding: space.lg },
  richTimeline: { padding: space.lg, gap: space.md },
  timelineHeader: { flexDirection: 'row', alignItems: 'flex-start', gap: space.md },
  timelineNote: { maxWidth: '50%' },
  stagesBlock: { gap: space.sm, paddingTop: space.xs },
  stageBar: { flexDirection: 'row', height: size.dot, borderRadius: radius.pill, overflow: 'hidden', gap: space.xxs },
  stageSegment: { height: '100%', borderRadius: radius.pill },
  stageLegend: { flexDirection: 'row', flexWrap: 'wrap', gap: space.sm },
  stageItem: { width: '48%', gap: space.xxs },
  stageTitleRow: { flexDirection: 'row', alignItems: 'center', gap: space.tight },
  stageDot: { width: size.dot, height: size.dot, borderRadius: radius.pill },
  timelineChips: { flexDirection: 'row', flexWrap: 'wrap', alignItems: 'center', gap: space.sm },
  riskBadge: { paddingHorizontal: space.md, paddingVertical: space.xs, borderRadius: radius.pill, backgroundColor: colors.highlight, borderWidth: size.hairline, borderColor: colors.accentBorder },
  riskBadgeDanger: { backgroundColor: colors.dangerFill, borderColor: colors.dangerBorder },
  action: { padding: space.lg, gap: space.xs },
});
