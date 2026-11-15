import { BlurView } from 'expo-blur';
import { useState, type ReactNode } from 'react';
import {
  ActivityIndicator, Platform, Pressable, ScrollView, StyleSheet, Text, TextInput, View,
  type TextInputProps, type TextProps, type TextStyle, type ViewStyle, type StyleProp,
} from 'react-native';
import Animated, { useAnimatedStyle, withTiming } from 'react-native-reanimated';
import { strings } from '@/i18n/strings';
import { colors, glass, icons, motion, radius, size, space } from '@/theme/tokens';
import { typography } from '@/theme/typography';
import { useTheme } from '@/theme/useTheme';
import { Icon, type IconName } from './Icon';

type Tone = keyof typeof colors;
type TextTone = { [K in Tone]: (typeof colors)[K] extends string ? K : never }[Tone];
type Variant = keyof typeof typography;
export function Label({ variant = 'body', tone = 'cream', style, ...props }: TextProps & { variant?: Variant; tone?: TextTone }) {
  return <Text {...props} style={[typography[variant], { color: colors[tone] }, style]} />;
}

type SurfaceKind = 'glass' | 'strong' | 'card' | 'selected' | 'highlight' | 'danger';
export function Surface({ kind = 'card', rounding = radius.card, style, children }: {
  kind?: SurfaceKind; rounding?: number; style?: StyleProp<ViewStyle>; children: ReactNode;
}) {
  const frosted = kind === 'glass' || kind === 'strong';
  const tint = {
    glass: colors.glass, strong: colors.strongGlass, card: colors.card, selected: colors.selectedCard,
    highlight: colors.highlight, danger: colors.dangerFill,
  }[kind];
  const border = {
    glass: colors.glassBorder, strong: colors.strongBorder, card: colors.border, selected: colors.accent,
    highlight: colors.accentBorder, danger: colors.dangerBorder,
  }[kind];
  const androidFallback = frosted && Platform.OS === 'android';
  const webBlur: ViewStyle & { backdropFilter?: string } = frosted && Platform.OS === 'web'
    ? { backdropFilter: 'blur(' + (kind === 'strong' ? glass.strongBlur : glass.blur) + 'px) saturate(' + glass.saturation + '%)' }
    : {};

  return (
    <View style={[styles.surface, { borderRadius: rounding, borderColor: border, backgroundColor: androidFallback ? colors.opaqueGlass : tint },
      frosted && glass.shadow, webBlur, style]}>
      {frosted && Platform.OS === 'ios' && (
        <View pointerEvents="none" style={StyleSheet.absoluteFill}>
          <BlurView tint="dark" intensity={kind === 'strong' ? glass.strongBlur : glass.blur} style={StyleSheet.absoluteFill} />
        </View>
      )}
      {children}
    </View>
  );
}

export function IconButton({ name, label, onPress, tone = 'glass', disabled, color }: {
  name: IconName; label: string; onPress: () => void; tone?: 'glass' | 'accent' | 'dark'; disabled?: boolean; color?: string;
}) {
  const { reducedMotion } = useTheme();
  return (
    <Pressable accessibilityRole="button" accessibilityLabel={label} accessibilityState={{ disabled }}
      disabled={disabled} onPress={onPress}
      style={({ pressed }) => [styles.iconButton, {
        backgroundColor: { glass: colors.iconGlass, dark: colors.iconDark, accent: colors.accent }[tone],
        borderColor: tone === 'accent' ? colors.transparent : colors.border,
      }, disabled && styles.disabled, pressed && !reducedMotion && styles.pressed]}>
      <Icon name={name} color={color ?? (tone === 'accent' ? colors.forest950 : colors.cream)} />
    </Pressable>
  );
}

export function PrimaryButton({ label, onPress, disabled, busy }: { label: string; onPress: () => void; disabled?: boolean; busy?: boolean }) {
  const { reducedMotion } = useTheme();
  const inactive = disabled || busy;
  return (
    <Pressable accessibilityRole="button" accessibilityState={{ disabled: inactive, busy }}
      disabled={inactive} onPress={onPress}
      style={({ pressed }) => [styles.primary, inactive ? styles.disabled : glass.actionShadow, pressed && !reducedMotion && styles.pressed]}>
      <Label tone="forest950" variant="button" style={styles.grow}>{label}</Label>
      <View style={styles.arrow}>
        {busy ? <ActivityIndicator color={colors.accent} /> : <Icon name="arrow" color={colors.accent} />}
      </View>
    </Pressable>
  );
}

export type Choice = { id: string; label: string };
export function Segmented({ items, value, onChange, scroll = false }: {
  items: readonly Choice[]; value: string; onChange: (id: string) => void; scroll?: boolean;
}) {
  const choices = items.map((item) => (
    <Pressable key={item.id} accessibilityRole="tab" accessibilityState={{ selected: item.id === value }} aria-selected={item.id === value}
      onPress={() => onChange(item.id)} style={[styles.segmentControl, !scroll && styles.grow]}>
      <View style={[styles.segment, item.id === value && styles.segmentActive]}>
        <Label variant="chip" tone={item.id === value ? 'cream' : 'sage'}>{item.label}</Label>
      </View>
    </Pressable>
  ));
  return (
    <Surface rounding={radius.pill}>
      {scroll ? <ScrollView horizontal showsHorizontalScrollIndicator={false} role="tablist" contentContainerStyle={styles.segmentRow}>{choices}</ScrollView>
        : <View role="tablist" style={styles.segmentRow}>{choices}</View>}
    </Surface>
  );
}

export function Chip({ label, onPress, accent }: { label: string; onPress?: () => void; accent?: boolean }) {
  const content = <Label variant={onPress ? 'chip' : 'smallBold'} tone={accent ? 'forest950' : 'cream'}>{label}</Label>;
  return onPress
    ? <Pressable accessibilityRole="button" onPress={onPress} style={({ pressed }) => [styles.chip, styles.chipControl, pressed && styles.disabled]}>{content}</Pressable>
    : <View style={[styles.chip, accent && styles.chipAccent]}>{content}</View>;
}

export function SearchField({ glassy, compact, invalid, focused, style, onFocus, onBlur, ...props }: TextInputProps & { glassy?: boolean; compact?: boolean; invalid?: boolean; focused?: boolean }) {
  const [hasFocus, setHasFocus] = useState(false);
  return (
    <Surface kind={glassy ? 'glass' : 'card'} rounding={radius.pill}
      style={[styles.search, glassy && !compact && styles.largeSearch, invalid ? styles.invalid : (focused || hasFocus) && styles.focused]}>
      <Icon name="search" size={glassy && !compact ? icons.regular : icons.small} color={colors.sage} />
      <TextInput {...props} aria-invalid={invalid || undefined} placeholderTextColor={colors.sage} autoCorrect={false}
        onFocus={(event) => { setHasFocus(true); onFocus?.(event); }}
        onBlur={(event) => { setHasFocus(false); onBlur?.(event); }}
        autoCapitalize="none" style={[styles.input, Platform.OS === 'web' && webSearchInput, style]} />
    </Surface>
  );
}

export function Progress({ value, label }: { value: number; label: string }) {
  const { reducedMotion } = useTheme();

  const percent = Math.min(100, Math.max(0, value));
  const fill = useAnimatedStyle(() => ({ width: (reducedMotion ? percent : withTiming(percent, { duration: motion.progress })) + '%' }));
  return (
    <View accessibilityRole="progressbar" accessibilityLabel={label} accessibilityValue={{ min: 0, max: 100, now: percent }} style={styles.track}>
      <Animated.View style={[styles.fill, fill]} />
    </View>
  );
}

export function Stat({ label, value, accent, large, muted, tile, compact, style }: {
  label: string; value: ReactNode; accent?: boolean; large?: boolean; muted?: boolean; tile?: boolean; compact?: boolean; style?: StyleProp<ViewStyle>;
}) {
  const content = <>
    <Label variant="label" tone="sage">{label}</Label>
    <Label variant={large ? 'value' : tile ? 'action' : 'button'} tone={accent ? 'accent' : muted ? 'muted' : 'cream'} numberOfLines={compact ? 1 : undefined} style={styles.statValue}>{value}</Label>
  </>;
  return tile ? <Surface kind="glass" rounding={radius.tile} style={[styles.statTile, style]}>{content}</Surface> :
    <View style={style}>{content}</View>;
}

export function Message({ title, hint, icon = 'calendar', onRetry }: { title: string; hint?: string; icon?: IconName; onRetry?: () => void }) {
  return (
    <Surface style={styles.message}>
      <View style={styles.messageIcon}><Icon name={icon} color={colors.sage} /></View>
      <Label variant="button" accessibilityRole="alert" style={styles.center}>{title}</Label>
      {!!hint && <Label variant="caption" tone="sage" style={styles.center}>{hint}</Label>}
      {!!onRetry && <Chip label={strings.tryAgain} onPress={onRetry} />}
    </Surface>
  );
}

export function ErrorCard({ title, hint }: { title: string; hint: string }) {
  return (
    <Surface kind="danger" rounding={radius.tile} style={styles.error}>
      <View style={styles.errorIcon}><Label variant="smallBold" tone="forest950">{strings.alertMark}</Label></View>
      <View style={styles.grow}>
        <Label accessibilityRole="alert" variant="chip">{title}</Label>
        <Label variant="detail" tone="secondary">{hint}</Label>
      </View>
    </Surface>
  );
}

const webSearchInput: TextStyle = { outlineStyle: 'solid', outlineWidth: 0 };

const styles = StyleSheet.create({
  surface: { borderWidth: size.hairline, overflow: 'hidden' },
  iconButton: { width: size.touch, height: size.touch, borderRadius: radius.pill, borderWidth: size.hairline, alignItems: 'center', justifyContent: 'center' },
  pressed: { transform: [{ scale: motion.pressScale }] },
  disabled: { opacity: motion.disabledOpacity },
  primary: { minHeight: size.primary, paddingStart: space.xl, paddingEnd: space.tight, paddingVertical: space.tight, gap: space.sm,
    backgroundColor: colors.accent, borderRadius: radius.pill, flexDirection: 'row', alignItems: 'center' },
  arrow: { width: size.touch, height: size.touch, borderRadius: radius.pill, backgroundColor: colors.forest950, alignItems: 'center', justifyContent: 'center' },
  grow: { flex: 1, minWidth: 0 },
  segmentRow: { flexDirection: 'row', gap: space.xs, paddingHorizontal: space.xs },
  segmentControl: { minHeight: size.touch, justifyContent: 'center' },
  segment: { paddingHorizontal: space.lg, paddingVertical: space.sm, alignItems: 'center', borderRadius: radius.pill },
  segmentActive: { backgroundColor: colors.segment },
  chip: { backgroundColor: colors.chip, paddingHorizontal: space.md, paddingVertical: space.sm, borderRadius: radius.pill, justifyContent: 'center' },
  chipControl: { minHeight: size.touch, paddingHorizontal: space.lg },
  chipAccent: { backgroundColor: colors.accent },
  search: { minHeight: size.control, paddingHorizontal: space.lg, flexDirection: 'row', alignItems: 'center', gap: space.sm },
  largeSearch: { minHeight: size.primary, paddingHorizontal: space.gutter, gap: space.md },
  focused: { borderColor: colors.focus },
  invalid: { borderColor: colors.danger },
  input: { ...typography.input, minHeight: size.touch, flex: 1, minWidth: 0, paddingVertical: space.sm, color: colors.cream },
  track: { height: size.indicator, backgroundColor: colors.chip, borderRadius: radius.pill, overflow: 'hidden' },
  fill: { height: '100%', borderRadius: radius.pill, backgroundColor: colors.accent },
  statTile: { paddingHorizontal: space.lg, paddingVertical: space.tile },
  statValue: { marginTop: space.xxs },
  message: { padding: space.xl, alignItems: 'center', gap: space.sm },
  messageIcon: { width: size.control, height: size.control, borderRadius: radius.pill, backgroundColor: colors.chip, alignItems: 'center', justifyContent: 'center' },
  center: { textAlign: 'center' },
  error: { paddingHorizontal: space.lg, paddingVertical: space.md, flexDirection: 'row', gap: space.md },
  errorIcon: { width: space.xl, height: space.xl, alignItems: 'center', justifyContent: 'center', borderRadius: radius.pill, backgroundColor: colors.danger },
});
