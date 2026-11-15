import { useState, type ReactNode } from 'react';
import { Platform, StyleSheet, View, type ViewProps } from 'react-native';
import { GestureDetector, useCompetingGestures, usePanGesture, useTapGesture } from 'react-native-gesture-handler';
import Animated, { useAnimatedStyle, useSharedValue, withSpring } from 'react-native-reanimated';
import { strings } from '@/i18n/strings';
import { colors, motion, radius, size, space } from '@/theme/tokens';
import { useTheme } from '@/theme/useTheme';
import { Icon } from './Icon';
import { Label, Segmented, Surface, type Choice } from './primitives';

export function PlanSheet({ subtitle, tabs, active, onTab, children, bottom = 0 }: {
  subtitle?: string; tabs: readonly Choice[]; active: string; onTab: (id: string) => void; children: ReactNode; bottom?: number;
}) {
  const [height, setHeight] = useState(0);
  const { reducedMotion } = useTheme();
  const maxOffset = Math.max(0, Math.min(size.planPeek, height - bottom - size.touch));
  const offset = useSharedValue(0);
  const start = useSharedValue(0);
  const snapTo = (position: number) => {
    'worklet';
    offset.set(reducedMotion ? position : withSpring(position, { duration: motion.enter, dampingRatio: .92 }));
  };
  const toggle = () => {
    'worklet';
    snapTo(offset.get() > maxOffset / 2 ? 0 : maxOffset);
  };
  const pan = usePanGesture({
    runOnJS: Platform.OS === 'web',
    minDistance: space.xs,
    onActivate: () => { start.set(Math.min(offset.get(), maxOffset)); },
    onUpdate: (event) => { offset.set(Math.max(0, Math.min(maxOffset, start.get() + event.translationY))); },
    onDeactivate: () => { snapTo(offset.get() > maxOffset / 2 ? maxOffset : 0); },
  });
  const tap = useTapGesture({ runOnJS: Platform.OS === 'web', onActivate: toggle });
  const gesture = useCompetingGestures(pan, tap);
  const onKeyDown: ViewProps['onKeyDown'] = (event) => {
    const key = 'key' in event ? event.key : event.nativeEvent.key;
    if (key === 'Enter' || key === ' ') {
      event.preventDefault();
      toggle();
    }
  };
  const position = useAnimatedStyle(() => ({ transform: [{ translateY: Math.min(offset.get(), maxOffset) }] }));

  return (
    <Animated.View onLayout={(event) => setHeight(event.nativeEvent.layout.height)} style={[styles.sheet, position]}>
      <Surface kind="strong" rounding={radius.sheet} style={styles.surface}>
        <GestureDetector gesture={gesture} touchAction={Platform.OS === 'web' ? 'none' : undefined}>
          <View tabIndex={Platform.OS === 'web' ? 0 : undefined}
            onKeyDown={Platform.OS === 'web' ? onKeyDown : undefined} accessible accessibilityRole="button" accessibilityLabel={strings.sheet}
            accessibilityActions={[{ name: 'activate' }]} onAccessibilityAction={toggle} style={styles.handleTarget}>
            <View style={styles.handle} />
          </View>
        </GestureDetector>
        <View style={styles.heading}>
          <View style={styles.flex}>
            {!!subtitle && <Label variant="label" tone="sage">{subtitle}</Label>}
            <Label variant="heading" accessibilityRole="header">{strings.planTitle}</Label>
          </View>
          <View style={styles.icon}><Icon name="redo" color={colors.forest950} /></View>
        </View>
        <View style={styles.segments}><Segmented items={tabs} value={active} onChange={onTab} /></View>
        {children}
      </Surface>
    </Animated.View>
  );
}

const styles = StyleSheet.create({
  sheet: { position: 'absolute', bottom: 0, start: 0, end: 0, height: size.planSheet },
  surface: { flex: 1, borderBottomLeftRadius: 0, borderBottomRightRadius: 0, borderBottomWidth: 0 },
  flex: { flex: 1 },
  handleTarget: { minHeight: size.touch, marginBottom: -space.lg, justifyContent: 'flex-start', alignItems: 'center', paddingTop: space.md, zIndex: 1 },
  handle: { width: size.sheetHandleWidth, height: size.indicator, backgroundColor: colors.handle, borderRadius: radius.pill },
  heading: { flexDirection: 'row', alignItems: 'center', gap: space.md, paddingHorizontal: space.gutter },
  icon: { width: size.touch, height: size.touch, borderRadius: radius.pill, backgroundColor: colors.accent, alignItems: 'center', justifyContent: 'center' },
  segments: { marginTop: space.md, paddingHorizontal: space.gutter },
});
