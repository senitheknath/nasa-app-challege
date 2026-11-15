import DateTimePicker, { DateTimePickerAndroid } from '@react-native-community/datetimepicker';
import { useState } from 'react';
import { Platform, Pressable, StyleSheet, View } from 'react-native';
import { strings } from '@/i18n/strings';
import { colors, icons, radius, size, space } from '@/theme/tokens';
import { calendarDate, formatDate, parseCalendarDate } from '@/utils/format';
import { Icon } from './Icon';
import { Label } from './primitives';

export function DateField({ value, onChange }: { value: string; onChange: (value: string) => void }) {
  const [isOpen, setIsOpen] = useState(false);
  const date = parseCalendarDate(value) ?? new Date();
  const select = (chosen: Date) => {
    onChange(calendarDate(chosen));
    setIsOpen(false);
  };
  const open = () => {
    if (Platform.OS === 'android') {
      DateTimePickerAndroid.open({ value: date, mode: 'date', onValueChange: (_, chosen) => select(chosen) });
    } else {
      setIsOpen(!isOpen);
    }
  };

  return (
    <View>
      <View style={styles.label}><Icon name="calendar" size={icons.small} color={colors.sage} /><Label variant="label" tone="sage">{strings.sowingDate}</Label></View>
      <Pressable accessibilityRole="button" accessibilityLabel={strings.sowingDate} accessibilityValue={{ text: formatDate(value) }}
        onPress={open} style={styles.field}>
        <Label variant="chip" style={styles.value}>{formatDate(value)}</Label><Icon name="calendar" size={icons.small} />
      </Pressable>
      {isOpen && <DateTimePicker value={date} mode="date" display="inline" themeVariant="dark"
        onValueChange={(_, chosen) => select(chosen)} onDismiss={() => setIsOpen(false)} />}
    </View>
  );
}

const styles = StyleSheet.create({
  label: { flexDirection: 'row', alignItems: 'center', gap: space.sm },
  field: { minHeight: size.dateField, borderRadius: radius.pill, borderWidth: size.hairline, borderColor: colors.border,
    paddingHorizontal: space.lg, flexDirection: 'row', alignItems: 'center', marginTop: space.sm, backgroundColor: colors.innerDark, gap: space.sm },
  value: { flex: 1 },
});
