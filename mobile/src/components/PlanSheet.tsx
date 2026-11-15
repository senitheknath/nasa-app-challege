import type { ReactNode } from 'react';
import { StyleSheet, View } from 'react-native';
import { colors, size, space } from '@/theme/tokens';
import { Label, Segmented, Surface, type Choice } from './primitives';

export type PlanSheetProps = {
  subtitle?: string;
  titleOverride?: string;
  tabs: readonly Choice[];
  active: string;
  onTab: (id: string) => void;
  onResetWidget?: () => void;
  headerActions?: ReactNode;
  children: ReactNode;
  bottom?: number;
  top?: number;
};

export function PlanSheet({
  subtitle,
  tabs,
  active,
  onTab,
  children,
  top = 0,
}: PlanSheetProps) {
  return (
    <View style={[styles.sheet, { top }]}>
      <Surface kind="strong" rounding={0} style={styles.surface}>
        <View style={styles.header}>
          {!!subtitle && (
            <Label variant="label" tone="sage" style={styles.subtitle}>
              {subtitle}
            </Label>
          )}
          <Segmented items={tabs} value={active} onChange={onTab} />
        </View>
        <View style={styles.body}>{children}</View>
      </Surface>
    </View>
  );
}

const styles = StyleSheet.create({
  sheet: {
    position: 'absolute',
    bottom: 0,
    start: 0,
    end: 0,
  },
  surface: {
    flex: 1,
    backgroundColor: colors.forest900,
    borderWidth: 0,
    borderTopWidth: size.hairline,
    borderTopColor: colors.border,
  },
  header: {
    paddingHorizontal: space.gutter,
    paddingTop: space.md,
    paddingBottom: space.sm,
    gap: space.sm,
  },
  subtitle: {
    paddingHorizontal: space.xs,
  },
  body: {
    flex: 1,
    minHeight: 0,
  },
});
