import type { CSSProperties } from 'react';
import { StyleSheet, View } from 'react-native';
import { strings } from '@/i18n/strings';
import { colors, icons, radius, size, space } from '@/theme/tokens';
import { typography } from '@/theme/typography';
import { parseCalendarDate } from '@/utils/format';
import { Icon } from './Icon';
import { Label } from './primitives';

export function DateField({ value, onChange }: { value: string; onChange: (value: string) => void }) {
  return (
    <View>
      <View style={styles.label}>
        <Icon name="calendar" size={icons.small} color={colors.sage} />
        <Label variant="label" tone="sage">{strings.sowingDate}</Label>
      </View>
      <input type="date" aria-label={strings.sowingDate} value={value}
        onChange={(event) => { if (parseCalendarDate(event.currentTarget.value)) onChange(event.currentTarget.value); }}
        style={inputStyle} />
    </View>
  );
}

const styles = StyleSheet.create({
  label: { flexDirection: 'row', alignItems: 'center', gap: space.sm },
});

const inputStyle: CSSProperties = {
  fontFamily: typography.chip.fontFamily,
  fontSize: '0.875rem',
  color: colors.cream,
  colorScheme: 'dark',
  minHeight: size.dateField,
  minWidth: 0,
  width: '100%',
  boxSizing: 'border-box',
  marginTop: space.sm,
  padding: space.sm + 'px ' + space.lg + 'px',
  borderRadius: radius.pill,
  border: size.hairline + 'px solid ' + colors.border,
  backgroundColor: colors.innerDark,
};
