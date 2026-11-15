import { LinearGradient } from 'expo-linear-gradient';
import { Pressable, StyleSheet, View } from 'react-native';
import { strings } from '@/i18n/strings';
import { colors, icons, motion, radius, size, space } from '@/theme/tokens';
import { useTheme } from '@/theme/useTheme';
import { Icon, type IconName } from './Icon';
import { IconButton, Label, PrimaryButton, Surface } from './primitives';

const steps = [
  [strings.country, 'globe'], [strings.area, 'map'], [strings.strategy, 'layers'],
  [strings.crop, 'sprout'], [strings.plan, 'redo'],
] as const satisfies readonly (readonly [string, IconName])[];

export function StepBar({ current, reached, skipped, onStep }: {
  current: number; reached: number; skipped?: number; onStep: (step: number) => void;
}) {
  const { reducedMotion } = useTheme();
  return (
    <Surface kind="strong" rounding={radius.pill} style={styles.tabBar}>
      {steps.map(([label, icon], index) => {
        const step = index + 1;
        const active = step === current;
        const locked = step > reached || step === skipped;
        return (
          <Pressable key={label} accessibilityRole="tab" accessibilityLabel={label}
            accessibilityState={{ selected: active, disabled: locked }} aria-selected={active} disabled={locked} onPress={() => onStep(step)}
            style={({ pressed }) => [styles.tab, !locked && styles.available, active && styles.active,
              pressed && !reducedMotion && styles.pressed]}>
            <View>
              <Icon name={icon} color={active ? colors.accent : locked ? colors.locked : colors.cream} />
              {step < current && !locked && <View style={styles.check}><Icon name="check" color={colors.accent} size={icons.badge} /></View>}
            </View>
          </Pressable>
        );
      })}
    </Surface>
  );
}

export function ScreenHeader({ title, subtitle, top, onBack, onCountry, onAccount }: {
  title: string; subtitle: string; top: number; onBack: () => void; onCountry: () => void; onAccount?: () => void;
}) {
  return (
    <View style={[styles.header, { paddingTop: top }]} pointerEvents="box-none">
      <LinearGradient pointerEvents="none" colors={[colors.topScrim, colors.middleScrim, colors.transparent]} style={StyleSheet.absoluteFill} />
      <IconButton name="back" label={strings.back} onPress={onBack} />
      <View style={styles.headerText} pointerEvents="none">
        <Label variant="title" accessibilityRole="header">{title}</Label>
        <Label variant="caption" tone="sage" style={styles.subtitle}>{subtitle}</Label>
      </View>
      {onAccount && <IconButton name="user" label={strings.account} onPress={onAccount} />}
      <IconButton name="pin" label={strings.changeCountry} onPress={onCountry} />
    </View>
  );
}

export function ScreenFooter({ label, current, reached, skipped, disabled, busy, onNext, onStep, onMonitor, monitorActive, monitorDisabled, bottom }: {
  label: string; current: number; reached: number; skipped?: number; disabled?: boolean; busy?: boolean;
  onNext: () => void; onStep: (step: number) => void; onMonitor?: () => void; monitorActive?: boolean; monitorDisabled?: boolean; bottom: number;
}) {
  const { reducedMotion } = useTheme();
  return (
    <View style={[styles.footer, { paddingBottom: bottom + space.gutter }]} pointerEvents="box-none">
      <LinearGradient pointerEvents="none" colors={[colors.transparent, colors.middleScrim, colors.bottomScrim]} style={StyleSheet.absoluteFill} />
      {!monitorActive && <PrimaryButton label={label} onPress={onNext} disabled={disabled} busy={busy} />}
      <View style={styles.footerBar}>
        <View style={styles.stepWrap}>
          <StepBar current={monitorActive ? 0 : current} reached={reached} skipped={skipped} onStep={onStep} />
        </View>
        {onMonitor && (
          <Surface kind="strong" rounding={radius.pill} style={styles.monitorPill}>
            <Pressable
              accessibilityRole="button"
              accessibilityLabel={strings.monitor}
              accessibilityState={{ selected: !!monitorActive, disabled: !!monitorDisabled }}
              disabled={monitorDisabled}
              onPress={onMonitor}
              style={({ pressed }) => [
                styles.tab,
                !monitorDisabled && styles.available,
                monitorActive && styles.active,
                pressed && !reducedMotion && styles.pressed,
              ]}
            >
              <Icon name="cube" color={monitorActive ? colors.accent : monitorDisabled ? colors.locked : colors.cream} />
            </Pressable>
          </Surface>
        )}
      </View>
    </View>
  );
}

const styles = StyleSheet.create({
  header: { flexDirection: 'row', alignItems: 'center', paddingHorizontal: space.gutter, paddingBottom: space.md, gap: space.md },
  headerText: { flex: 1, minWidth: 0 },
  subtitle: { marginTop: space.xs },
  footer: { paddingHorizontal: space.gutter, paddingTop: space.fade, gap: space.md },
  footerBar: { flexDirection: 'row', alignItems: 'center', gap: space.sm },
  stepWrap: { flex: 1, minWidth: 0 },
  monitorPill: { padding: space.sm },
  tabBar: { flexDirection: 'row', justifyContent: 'space-between', padding: space.sm },
  tab: { width: size.control, height: size.control, alignItems: 'center', justifyContent: 'center', borderRadius: radius.pill, borderWidth: size.hairline, borderColor: colors.transparent },
  available: { backgroundColor: colors.reached },
  active: { backgroundColor: colors.forest950, borderColor: colors.accentBorder },
  pressed: { transform: [{ scale: motion.pressScale }] },
  check: { position: 'absolute', top: -space.tight, end: -space.tight },
});
