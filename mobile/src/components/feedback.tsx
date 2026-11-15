import type { ReactNode } from 'react';
import { StyleSheet, View } from 'react-native';
import Animated, { FadeIn } from 'react-native-reanimated';
import { strings } from '@/i18n/strings';
import { colors, motion, radius, size, space } from '@/theme/tokens';
import { useTheme } from '@/theme/useTheme';
import { Message } from './primitives';

export type LoadState = 'loading' | 'empty' | 'error' | 'offline' | 'ready';
export type SkeletonLayout = 'country' | 'map' | 'metrics' | 'strategy' | 'crop' | 'plan';

const layouts = {
  country: [size.primary, size.skeletonLine, size.skeletonAction],
  map: [size.control, size.skeletonMap, size.skeletonLine],
  metrics: [size.skeletonLine, size.skeletonLine, size.skeletonLine],
  strategy: [size.skeletonLine, size.skeletonList, size.skeletonList],
  crop: [size.skeletonMap, size.control, size.control, size.skeletonList, size.skeletonList],
  plan: [size.skeletonAction, size.skeletonLine, size.skeletonLine],
} satisfies Record<SkeletonLayout, readonly number[]>;

export function Skeleton({ layout }: { layout: SkeletonLayout }) {
  const { reducedMotion } = useTheme();
  return (
    <Animated.View entering={reducedMotion ? undefined : FadeIn.duration(motion.enter)}
      accessible accessibilityLabel={layout === 'plan' ? strings.buildingPlan : strings.loading} accessibilityState={{ busy: true }} style={[styles.stack, layout === 'metrics' && styles.metricRow]}>
      {layouts[layout].map((height, index) => <View key={index} style={[styles.block, { height }, layout === 'metrics' && styles.metric]} />)}
    </Animated.View>
  );
}

export function Feedback({ state, layout, onRetry, emptyTitle, emptyHint, children }: {
  state: LoadState; layout: SkeletonLayout; onRetry?: () => void; emptyTitle?: string; emptyHint?: string; children?: ReactNode;
}) {
  if (state === 'ready') return children;
  if (state === 'loading') return <Skeleton layout={layout} />;
  if (state === 'offline') return <Message title={strings.offline} hint={strings.offlineHint} icon="globe" onRetry={onRetry} />;
  if (state === 'error') return <Message title={strings.failed} hint={strings.failureHint} onRetry={onRetry} />;
  return <Message title={emptyTitle ?? strings.empty} hint={emptyHint ?? strings.emptyHint} onRetry={onRetry} />;
}

const styles = StyleSheet.create({
  stack: { gap: space.md },
  block: { backgroundColor: colors.skeleton, borderRadius: radius.tile },
  metricRow: { flexDirection: 'row' },
  metric: { flex: 1 },
});
