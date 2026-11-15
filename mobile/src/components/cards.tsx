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

export function ChoiceCard({ selected, onPress, tag, title, details, kind = 'strategy' }: {
  selected: boolean; onPress: () => void; tag: string; title: string; details: ReactNode; kind?: 'strategy' | 'crop';
}) {
  const { reducedMotion } = useTheme();
  return (
    <Pressable accessibilityRole="button" accessibilityState={{ selected }} aria-pressed={selected} onPress={onPress}
      style={({ pressed }) => pressed && !reducedMotion && styles.pressed}>
      <Surface kind={selected ? 'selected' : 'card'} style={[styles.selection, kind === 'strategy' && styles.strategy]}>
        <View style={styles.selectionBody}>
          <Label variant="tag" tone="sage">{tag}</Label>
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

export function CropCard({ selected, onPress, category, name, cropYield, water, waterLabel }: {
  selected: boolean; onPress: () => void; category: string; name: string; cropYield: string; water: number; waterLabel: string;
}) {
  return (
    <ChoiceCard kind="crop" selected={selected} onPress={onPress} tag={category} title={name} details={
      <>
        <View style={styles.cropFacts}>
          <View style={styles.fact}><Icon name="sprout" size={icons.small} color={colors.sage} /><Label variant="caption" tone="sage">{cropYield}</Label></View>
          <View style={styles.fact}>
            <Icon name="drop" size={icons.small} color={colors.sage} />
            <Label variant="caption" tone="sage">{strings.water} <Label variant="badge" tone={selected ? 'accent' : 'cream'}>{waterLabel}</Label></Label>
          </View>
        </View>
        <Progress value={water} label={strings.waterNeed} />
      </>
    } />
  );
}

export function TimelineCard({ season, crop, summary, note, first }: {
  season: string; crop: string; summary: string; note: string; first: boolean;
}) {
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
  selectIcon: { width: size.touch, height: size.touch, borderRadius: radius.pill, backgroundColor: colors.chip, justifyContent: 'center', alignItems: 'center' },
  largeSelectIcon: { width: size.control, height: size.control },
  selectedIcon: { backgroundColor: colors.accent },
  pressed: { transform: [{ scale: motion.pressScale }] },
  cropFacts: { flexDirection: 'row', flexWrap: 'wrap', gap: space.lg, marginTop: space.sm, marginBottom: space.md },
  fact: { flexDirection: 'row', alignItems: 'center', gap: space.tight, flexShrink: 1 },
  timeline: { flexDirection: 'row', alignItems: 'center', gap: space.md, padding: space.lg },
  timelineNote: { maxWidth: '50%' },
  action: { padding: space.lg, gap: space.xs },
});
