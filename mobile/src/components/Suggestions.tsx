import { Pressable, ScrollView, StyleSheet } from 'react-native';
import { radius, colors, size, space } from '@/theme/tokens';
import { Label, Surface } from './primitives';

export type Suggestion = { id: string; label: string; detail?: string; accent?: boolean };
export function Suggestions({ items, onSelect, message }: { items: readonly Suggestion[]; onSelect: (id: string) => void; message?: string }) {
  return (
    <Surface kind="strong" rounding={radius.card}>
      <ScrollView keyboardShouldPersistTaps="handled" nestedScrollEnabled showsVerticalScrollIndicator={false} style={styles.list}>
        {!!message && <Label tone="sage" style={styles.message}>{message}</Label>}
        {items.map((item) => (
          <Pressable key={item.id} accessibilityRole="button" onPress={() => onSelect(item.id)} style={styles.item}>
            <Label variant="input" style={styles.name}>{item.label}</Label>
            {!!item.detail && <Label variant="label" tone={item.accent ? 'accent' : 'sage'}>{item.detail}</Label>}
          </Pressable>
        ))}
      </ScrollView>
    </Surface>
  );
}

const styles = StyleSheet.create({
  list: { maxHeight: size.searchResults },
  item: {
    minHeight: size.control, paddingHorizontal: space.gutter, paddingVertical: space.sm, gap: space.sm, borderBottomColor: colors.border,
    borderBottomWidth: size.hairline, flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between',
  },
  name: { flex: 1 },
  message: { padding: space.gutter },
});
