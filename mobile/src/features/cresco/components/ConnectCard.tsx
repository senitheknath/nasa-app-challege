import { useEffect, useState } from 'react';
import { Linking, Platform, Pressable, StyleSheet, TextInput, View } from 'react-native';
import { Icon } from '@/components/Icon';
import { Chip, ErrorCard, Label, PrimaryButton, Surface } from '@/components/primitives';
import { colors, radius, size, space } from '@/theme/tokens';
import { typography } from '@/theme/typography';
import {
  CRESCO_DEFAULT_MODEL,
  GOOGLE_AI_STUDIO_API_KEY_URL,
  formatCrescoError,
} from '../model';

export function ConnectCard({
  farmLabel,
  busy,
  error,
  onConnect,
}: {
  farmLabel: string;
  busy: boolean;
  error: unknown;
  onConnect: (apiKey: string) => Promise<void>;
}) {
  // Ephemeral local state only — cleared immediately on connect success or unmount.
  const [apiKey, setApiKey] = useState('');
  const [showKey, setShowKey] = useState(false);
  const [localError, setLocalError] = useState<string | null>(null);

  useEffect(() => {
    return () => {
      setApiKey('');
    };
  }, []);

  const handleConnect = async () => {
    const trimmed = apiKey.trim();
    if (!trimmed) {
      setLocalError('Please enter your Google Gemini API key.');
      return;
    }
    setLocalError(null);
    try {
      await onConnect(trimmed);
      setApiKey('');
      setShowKey(false);
    } catch {
      // Error is surfaced via `error` prop from mutation state.
    }
  };

  const displayError = localError ?? (error ? formatCrescoError(error) : null);

  return (
    <View style={styles.container}>
      <Surface kind="glass" style={styles.heroCard}>
        <View style={styles.badgeRow}>
          <Surface kind="highlight" rounding={radius.pill} style={styles.iconCircle}>
            <Icon name="sprout" color={colors.accent} size={24} />
          </Surface>
          <View style={styles.titleBlock}>
            <Label variant="title" accessibilityRole="header">Cresco AI</Label>
            <Label variant="caption" tone="sage">Agronomy Advisor · {CRESCO_DEFAULT_MODEL}</Label>
          </View>
          <Chip label={farmLabel} />
        </View>

        <Label variant="caption" tone="secondary" style={styles.description}>
          Connect your Google Gemini API key to unlock farm-aware crop, soil, 3D moisture,
          NASA climate, and rotation planning guidance.
        </Label>

        <Surface kind="card" rounding={radius.tile} style={styles.securityNote}>
          <Label variant="label" tone="sage" style={styles.securityText}>
            Your key is verified directly with Gemini and kept only in temporary server session memory.
            It is never saved to device storage, disk, URLs, or logs.
          </Label>
        </Surface>
      </Surface>

      <Surface kind="card" style={styles.formCard}>
        <View style={styles.inputHeader}>
          <Label variant="smallBold" tone="cream">Gemini API Key</Label>
          <Pressable
            accessibilityRole="button"
            accessibilityLabel={showKey ? 'Hide API key' : 'Show API key'}
            onPress={() => setShowKey((prev) => !prev)}
            style={({ pressed }) => [styles.toggleBtn, pressed && styles.pressed]}
          >
            <Label variant="label" tone="accent">{showKey ? 'Hide' : 'Show'}</Label>
          </Pressable>
        </View>

        <Surface kind="strong" rounding={radius.pill} style={styles.inputShell}>
          <TextInput
            value={apiKey}
            onChangeText={(text) => {
              setApiKey(text);
              if (localError) setLocalError(null);
            }}
            placeholder="AIza..."
            placeholderTextColor={colors.muted}
            secureTextEntry={!showKey}
            autoCapitalize="none"
            autoCorrect={false}
            autoComplete="off"
            textContentType="none"
            editable={!busy}
            returnKeyType="go"
            onSubmitEditing={() => void handleConnect()}
            accessibilityLabel="Gemini API Key"
            style={[styles.input, Platform.OS === 'web' && webInputStyle]}
          />
        </Surface>

        {displayError && <ErrorCard title="Connection failed" hint={displayError} />}

        <PrimaryButton
          label={busy ? 'Verifying key...' : 'Verify & Connect'}
          onPress={() => void handleConnect()}
          busy={busy}
          disabled={busy || !apiKey.trim()}
        />

        <Pressable
          accessibilityRole="link"
          onPress={() => void Linking.openURL(GOOGLE_AI_STUDIO_API_KEY_URL)}
          style={({ pressed }) => [styles.studioLink, pressed && styles.pressed]}
        >
          <Icon name="diagonal" size={16} color={colors.accent} />
          <Label variant="caption" tone="accent">Get a Gemini API key in Google AI Studio</Label>
        </Pressable>
      </Surface>
    </View>
  );
}

const webInputStyle = { outlineStyle: 'none' } as unknown as object;

const styles = StyleSheet.create({
  container: { gap: space.md },
  heroCard: { padding: space.lg, gap: space.md },
  badgeRow: { flexDirection: 'row', alignItems: 'center', gap: space.md, flexWrap: 'wrap' },
  iconCircle: {
    width: size.control,
    height: size.control,
    alignItems: 'center',
    justifyContent: 'center',
  },
  titleBlock: { flex: 1, minWidth: 140 },
  description: { lineHeight: 20 },
  securityNote: { padding: space.md },
  securityText: { lineHeight: 18 },
  formCard: { padding: space.lg, gap: space.md },
  inputHeader: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between' },
  toggleBtn: {
    paddingHorizontal: space.md,
    paddingVertical: space.xs,
    borderRadius: radius.pill,
    backgroundColor: colors.highlight,
    borderWidth: size.hairline,
    borderColor: colors.accentBorder,
  },
  inputShell: {
    height: size.control,
    paddingHorizontal: space.lg,
    justifyContent: 'center',
  },
  input: {
    ...typography.caption,
    color: colors.cream,
    width: '100%',
  },
  studioLink: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: space.sm,
    paddingVertical: space.sm,
  },
  pressed: { opacity: 0.75 },
});
