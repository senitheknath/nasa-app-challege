import { router } from 'expo-router';
import { useEffect, useState } from 'react';
import { KeyboardAvoidingView, Platform, Pressable, ScrollView, StyleSheet, TextInput, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useQueryClient } from '@tanstack/react-query';
import { baseUrl, serverStore } from '@/api/config';
import { ApiError } from '@/api/errors';
import { Logo } from '@/components/cards';
import { Chip, ErrorCard, IconButton, Label, Message, PrimaryButton, Segmented, Surface } from '@/components/primitives';
import { explainThresholdsPreview } from '@/features/plan/expiryExplain';
import { strings } from '@/i18n/strings';
import { usePlanner, type UncertaintyPreset } from '@/state/usePlanner';
import { colors, motion, radius, size, space } from '@/theme/tokens';
import { typography } from '@/theme/typography';
import { formatNumber } from '@/utils/format';
import { useAuthMe, useAuthSubmit, useDeleteFarm, useSavedFarms, useSaveFarm, useSignOut } from './hooks';
import type { SavedFarm } from './model';

type UncertaintyPresetChoice = Exclude<UncertaintyPreset, 'custom'>;
type ThresholdOption = { value: number; label: string };

const PRESET_CHOICES = [
  { id: 'conservative', label: strings.presetLabels.conservative },
  { id: 'balanced', label: strings.presetLabels.balanced },
  { id: 'flexible', label: strings.presetLabels.flexible },
] as const;

const PRESET_DESCRIPTIONS: Record<UncertaintyPreset, string> = {
  conservative: 'Wide 14d buffer, strict 10% risk alerts, and high σ 0.28 weather cone.',
  balanced: 'Default 7d safety buffer, 25% risk threshold, and σ 0.18 forecast cone.',
  flexible: 'Tight 3d turnaround, 40% risk threshold, and narrow σ 0.10 weather cone.',
  custom: 'Custom thresholds active — adjust any control or reset to Balanced.',
};

const SAFETY_DAY_OPTIONS: readonly ThresholdOption[] = [
  { value: 3, label: '3d' },
  { value: 7, label: '7d' },
  { value: 14, label: '14d' },
  { value: 21, label: '21d' },
];

const COLLISION_PCT_OPTIONS: readonly ThresholdOption[] = [
  { value: 10, label: '10%' },
  { value: 25, label: '25%' },
  { value: 40, label: '40%' },
];

const VOLATILITY_OPTIONS: readonly ThresholdOption[] = [
  { value: 0.1, label: '0.10 Low' },
  { value: 0.18, label: '0.18 Standard' },
  { value: 0.28, label: '0.28 High' },
];

function clampThreshold(value: number, min: number, max: number, decimals = 0): number {
  const clamped = Math.min(max, Math.max(min, value));
  return Number(clamped.toFixed(decimals));
}

function ThresholdControl({
  title,
  valueLabel,
  value,
  min,
  max,
  step,
  decimals = 0,
  options,
  onChange,
  decrementLabel,
  incrementLabel,
}: {
  title: string;
  valueLabel: string;
  value: number;
  min: number;
  max: number;
  step: number;
  decimals?: number;
  options: readonly ThresholdOption[];
  onChange: (next: number) => void;
  decrementLabel: string;
  incrementLabel: string;
}) {
  const epsilon = decimals > 0 ? 0.005 : 0.5;
  const atMin = value <= min + (decimals > 0 ? 0.001 : 0);
  const atMax = value >= max - (decimals > 0 ? 0.001 : 0);

  return (
    <View style={styles.thresholdGroup}>
      <View style={styles.thresholdHeader}>
        <Label variant="caption" tone="sage" style={styles.flex}>{title}</Label>
        <View style={styles.valueBadge}>
          <Label variant="smallBold" tone="accent">{valueLabel}</Label>
        </View>
      </View>

      <View style={styles.thresholdControlsRow}>
        <View style={styles.optionChipsWrap}>
          {options.map((option) => {
            const active = Math.abs(value - option.value) < epsilon;
            return (
              <Pressable
                key={option.label}
                accessibilityRole="button"
                accessibilityState={{ selected: active }}
                onPress={() => onChange(clampThreshold(option.value, min, max, decimals))}
                style={({ pressed }) => [
                  styles.optionChip,
                  active && styles.optionChipActive,
                  pressed && styles.pressed,
                ]}
              >
                <Label variant="chip" tone={active ? 'forest950' : 'cream'}>
                  {option.label}
                </Label>
              </Pressable>
            );
          })}
        </View>

        <View style={styles.stepper}>
          <Pressable
            accessibilityRole="button"
            accessibilityLabel={decrementLabel}
            accessibilityState={{ disabled: atMin }}
            disabled={atMin}
            onPress={() => onChange(clampThreshold(value - step, min, max, decimals))}
            style={({ pressed }) => [
              styles.stepBtn,
              atMin && styles.stepBtnDisabled,
              pressed && !atMin && styles.pressed,
            ]}
          >
            <Label variant="button" tone="cream">−</Label>
          </Pressable>
          <View style={styles.stepDivider} />
          <Pressable
            accessibilityRole="button"
            accessibilityLabel={incrementLabel}
            accessibilityState={{ disabled: atMax }}
            disabled={atMax}
            onPress={() => onChange(clampThreshold(value + step, min, max, decimals))}
            style={({ pressed }) => [
              styles.stepBtn,
              atMax && styles.stepBtnDisabled,
              pressed && !atMax && styles.pressed,
            ]}
          >
            <Label variant="button" tone="cream">+</Label>
          </Pressable>
        </View>
      </View>
    </View>
  );
}

function errorMessage(error: unknown): string {
  if (error instanceof ApiError) {
    return error.code || strings.failed;
  }
  if (error instanceof Error) return error.message;
  return strings.failed;
}

export default function AuthScreen() {
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [displayName, setDisplayName] = useState('');

  const planner = usePlanner();
  const [farmNameInput, setFarmNameInput] = useState<string | null>(null);
  const effectiveFarmName = farmNameInput ?? planner.farmName ?? '';
  const [savedBanner, setSavedBanner] = useState(false);

  const queryClient = useQueryClient();
  const [serverInput, setServerInput] = useState(baseUrl);
  const [activeServer, setActiveServer] = useState(baseUrl);
  const [serverStatus, setServerStatus] = useState<string | null>(null);
  const [serverError, setServerError] = useState<string | null>(null);

  useEffect(() => {
    void serverStore.get().then((url) => {
      setActiveServer(url);
      setServerInput(url);
    });
  }, []);

  const handleSaveServer = async () => {
    setServerError(null);
    setServerStatus(null);
    try {
      const nextUrl = await serverStore.set(serverInput);
      setActiveServer(nextUrl);
      setServerInput(nextUrl);
      setServerStatus(strings.serverSaved);
      void queryClient.invalidateQueries();
    } catch (err) {
      setServerError(err instanceof Error ? err.message : strings.failed);
    }
  };

  const handleResetServer = async () => {
    setServerError(null);
    setServerStatus(null);
    const nextUrl = await serverStore.reset();
    setActiveServer(nextUrl);
    setServerInput(nextUrl);
    setServerStatus(strings.serverSaved);
    void queryClient.invalidateQueries();
  };

  const authMe = useAuthMe();
  const user = authMe.data ?? null;
  const authSubmit = useAuthSubmit(mode);
  const signOut = useSignOut();
  const farmsQuery = useSavedFarms(Boolean(user));
  const saveFarm = useSaveFarm();
  const deleteFarm = useDeleteFarm();

  const canDraftSave = Boolean(planner.countryId && planner.closed);
  const goBack = () => {
    if (router.canGoBack()) router.back();
    else router.replace('/');
  };

  const handleAuth = () => {
    if (!email.trim() || !password) return;
    authSubmit.mutate({
      email,
      password,
      display_name: mode === 'register' ? displayName : undefined,
    });
  };

  const handleSaveFarm = () => {
    if (!canDraftSave) return;
    setSavedBanner(false);
    saveFarm.mutate(
      {
        id: planner.farmId,
        name: effectiveFarmName.trim() || `${planner.countryId} Parcel`,
        country: planner.countryId,
        latitude: planner.latitude,
        longitude: planner.longitude,
        area_ha: planner.areaHa,
        boundary: planner.boundary,
        irrigation: planner.irrigation,
        crop_id: planner.cropId,
        start_date: planner.sowingDate,
      },
      {
        onSuccess: () => setSavedBanner(true),
      },
    );
  };

  const handleLoadFarm = (farm: SavedFarm) => {
    planner.loadSavedFarm(farm);
    const cropId = farm.crop_id ?? (farm.farm?.crop_id as string | null | undefined);
    router.replace(cropId ? '/plan' : '/area');
  };

  const farms = farmsQuery.data?.farms ?? [];
  const uncertaintyPreset = planner.uncertaintyPreset;
  const expirySafetyDays = planner.expirySafetyDays;
  const collisionThresholdPct = planner.collisionThresholdPct;
  const weatherVolatility = planner.weatherVolatility;
  const thresholdPreview = explainThresholdsPreview({
    expirySafetyDays,
    collisionThresholdPct,
    weatherVolatility,
  });
  const thresholdExplanations = [
    thresholdPreview.bufferDetail,
    thresholdPreview.collisionDetail,
    thresholdPreview.volatilityDetail,
  ];
  const hasActivePlan = Boolean(planner.countryId && (planner.reached >= 5 || planner.selectedRotationId));
  const presetBadgeLabel = strings.presetLabels[uncertaintyPreset];

  return (
    <SafeAreaView style={styles.root}>
      <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={styles.flex}>
        <ScrollView contentContainerStyle={styles.scroll} keyboardShouldPersistTaps="handled">
          <View style={styles.container}>
            <View style={styles.header}>
              <IconButton name="back" label={strings.back} onPress={goBack} />
              <View style={styles.logoWrap}>
                <Logo />
              </View>
              <Chip label={user ? strings.ready : strings.account} accent={Boolean(user)} />
            </View>

            {!user ? (
              <View style={styles.section}>
                <Label variant="heading">{strings.account}</Label>
                <Segmented
                  items={[
                    { id: 'login', label: strings.signIn },
                    { id: 'register', label: strings.register },
                  ]}
                  value={mode}
                  onChange={(id) => {
                    setMode(id as 'login' | 'register');
                    authSubmit.reset();
                  }}
                />

                {authSubmit.isError && (
                  <ErrorCard title={errorMessage(authSubmit.error)} hint={strings.failureHint} />
                )}

                <Surface kind="card" style={styles.formCard}>
                  <View style={styles.field}>
                    <Label variant="caption" tone="sage">{strings.email}</Label>
                    <TextInput
                      value={email}
                      onChangeText={setEmail}
                      placeholder="farmer@cresco.ag"
                      placeholderTextColor={colors.sage}
                      keyboardType="email-address"
                      autoCapitalize="none"
                      autoCorrect={false}
                      style={styles.input}
                    />
                  </View>

                  <View style={styles.field}>
                    <Label variant="caption" tone="sage">{strings.password}</Label>
                    <TextInput
                      value={password}
                      onChangeText={setPassword}
                      placeholder="••••••••"
                      placeholderTextColor={colors.sage}
                      secureTextEntry
                      autoCapitalize="none"
                      autoCorrect={false}
                      style={styles.input}
                    />
                  </View>

                  {mode === 'register' && (
                    <View style={styles.field}>
                      <Label variant="caption" tone="sage">{strings.displayName}</Label>
                      <TextInput
                        value={displayName}
                        onChangeText={setDisplayName}
                        placeholder="Arjun Perera"
                        placeholderTextColor={colors.sage}
                        autoCorrect={false}
                        style={styles.input}
                      />
                    </View>
                  )}
                </Surface>

                <PrimaryButton
                  label={mode === 'login' ? strings.signIn : strings.register}
                  onPress={handleAuth}
                  disabled={!email.trim() || !password}
                  busy={authSubmit.isPending}
                />
              </View>
            ) : (
              <View style={styles.section}>
                <Surface kind="highlight" style={styles.profileCard}>
                  <View style={styles.profileRow}>
                    <View style={styles.flex}>
                      <Label variant="cardTitle">{user.display_name || user.email}</Label>
                      <Label variant="detail" tone="sage">{user.email}</Label>
                    </View>
                    <Chip label={strings.signOut} onPress={() => signOut.mutate()} />
                  </View>
                </Surface>

                {canDraftSave && (
                  <Surface kind="card" style={styles.formCard}>
                    <Label variant="tag" tone="accent">
                      {planner.farmId ? strings.updateFarm : strings.saveFarm}
                    </Label>
                    <View style={styles.field}>
                      <TextInput
                        value={effectiveFarmName}
                        onChangeText={setFarmNameInput}
                        placeholder={strings.farmNamePlaceholder}
                        placeholderTextColor={colors.sage}
                        style={styles.input}
                      />
                    </View>
                    <Label variant="caption" tone="sage">
                      {`${planner.countryId} · ${planner.latitude.toFixed(4)}, ${planner.longitude.toFixed(4)}${planner.areaHa != null ? ` · ${formatNumber(planner.areaHa, 1)} ${strings.units.hectares}` : ''}`}
                    </Label>
                    {saveFarm.isError && (
                      <ErrorCard title={errorMessage(saveFarm.error)} hint={strings.failureHint} />
                    )}
                    {savedBanner && (
                      <Label variant="caption" tone="accent">{strings.farmSaved}</Label>
                    )}
                    <PrimaryButton
                      label={planner.farmId ? strings.updateFarm : strings.saveFarm}
                      onPress={handleSaveFarm}
                      busy={saveFarm.isPending}
                    />
                  </Surface>
                )}

                <View style={styles.farmsHeader}>
                  <Label variant="title">{strings.savedFarms}</Label>
                  <Chip label={String(farms.length)} />
                </View>

                {farmsQuery.isError && (
                  <ErrorCard
                    title={errorMessage(farmsQuery.error)}
                    hint={strings.failureHint}
                  />
                )}

                {!farmsQuery.isLoading && farms.length === 0 ? (
                  <Message
                    title={strings.noSavedFarms}
                    hint={strings.noSavedFarmsHint}
                    icon="bookmark"
                  />
                ) : (
                  <View style={styles.farmList}>
                    {farms.map((farm) => (
                      <Surface key={farm.id} kind="card" style={styles.farmCard}>
                        <View style={styles.farmRow}>
                          <View style={styles.flex}>
                            <Label variant="cardTitle">{farm.name}</Label>
                            <Label variant="caption" tone="sage">
                              {`${farm.country} · ${farm.latitude.toFixed(3)}, ${farm.longitude.toFixed(3)}${farm.area_ha != null ? ` · ${formatNumber(farm.area_ha, 1)} ${strings.units.hectares}` : ''}`}
                            </Label>
                            {farm.updated_at && (
                              <Label variant="label" tone="sage">{farm.updated_at.slice(0, 10)}</Label>
                            )}
                          </View>
                          <IconButton
                            name="trash"
                            label={strings.deleteFarm}
                            tone="dark"
                            onPress={() => deleteFarm.mutate(farm.id)}
                          />
                        </View>
                        <View style={styles.farmActions}>
                          <Chip label={strings.loadFarm} onPress={() => handleLoadFarm(farm as SavedFarm)} />
                        </View>
                      </Surface>
                    ))}
                  </View>
                )}
              </View>
            )}

            <Surface kind="card" style={styles.formCard}>
              <View style={styles.thresholdCardHeader}>
                <View style={styles.flex}>
                  <Label variant="tag" tone="accent">{strings.uncertaintyPreset}</Label>
                  <Label variant="title">{strings.expiryThresholdsTitle}</Label>
                  <Label variant="caption" tone="sage">{strings.expiryThresholdsSubtitle}</Label>
                </View>
                <View style={[styles.presetBadge, uncertaintyPreset === 'custom' && styles.presetBadgeCustom]}>
                  <Label
                    variant="smallBold"
                    tone={uncertaintyPreset === 'custom' ? 'accent' : 'cream'}
                  >
                    {presetBadgeLabel}
                  </Label>
                </View>
              </View>

              <Segmented
                items={PRESET_CHOICES}
                value={uncertaintyPreset}
                onChange={(id) => planner.setUncertaintyPreset(id as UncertaintyPresetChoice)}
              />

              <Label variant="caption" tone="sage">
                {PRESET_DESCRIPTIONS[uncertaintyPreset]}
              </Label>

              <ThresholdControl
                title={strings.expirySafetyDaysLabel}
                valueLabel={`${expirySafetyDays}d`}
                value={expirySafetyDays}
                min={0}
                max={35}
                step={1}
                options={SAFETY_DAY_OPTIONS}
                decrementLabel="Decrease safety buffer margin"
                incrementLabel="Increase safety buffer margin"
                onChange={(next) => planner.setExpiryThresholds({ expirySafetyDays: next })}
              />

              <ThresholdControl
                title={strings.collisionThresholdLabel}
                valueLabel={`${collisionThresholdPct}%`}
                value={collisionThresholdPct}
                min={5}
                max={75}
                step={5}
                options={COLLISION_PCT_OPTIONS}
                decrementLabel="Decrease collision risk threshold"
                incrementLabel="Increase collision risk threshold"
                onChange={(next) => planner.setExpiryThresholds({ collisionThresholdPct: next })}
              />

              <ThresholdControl
                title={strings.weatherVolatilityLabel}
                valueLabel={`σ ${weatherVolatility.toFixed(2)}`}
                value={weatherVolatility}
                min={0.05}
                max={0.5}
                step={0.02}
                decimals={2}
                options={VOLATILITY_OPTIONS}
                decrementLabel="Decrease weather volatility"
                incrementLabel="Increase weather volatility"
                onChange={(next) => planner.setExpiryThresholds({ weatherVolatility: next })}
              />

              <Surface kind="highlight" rounding={radius.tile} style={styles.explainedBox}>
                <Label variant="tag" tone="accent">{`${strings.thresholdsExplainedTitle} · ${thresholdPreview.summary}`}</Label>
                {thresholdExplanations.map((line) => (
                  <View key={line} style={styles.explainedRow}>
                    <View style={styles.explainedDot} />
                    <Label variant="detail" tone="secondary" style={styles.flex}>
                      {line}
                    </Label>
                  </View>
                ))}
              </Surface>

              {uncertaintyPreset !== 'balanced' && (
                <View style={styles.farmActions}>
                  <Pressable
                    accessibilityRole="button"
                    onPress={() => planner.setUncertaintyPreset('balanced')}
                    style={({ pressed }) => [styles.optionChip, pressed && styles.pressed]}
                  >
                    <Label variant="chip" tone="cream">{strings.resetToBalanced}</Label>
                  </Pressable>
                </View>
              )}

              {hasActivePlan && (
                <View style={styles.activePlanHint}>
                  <Label variant="caption" tone="sage">
                    {strings.thresholdsActiveSyncHint}
                  </Label>
                  <View style={styles.farmActions}>
                    {planner.reached >= 5 && (
                      <Pressable
                        accessibilityRole="button"
                        onPress={() => router.navigate('/plan')}
                        style={({ pressed }) => [styles.linkPill, pressed && styles.pressed]}
                      >
                        <Label variant="smallBold" tone="accent">Rotation Plan →</Label>
                      </Pressable>
                    )}
                    <Pressable
                      accessibilityRole="button"
                      onPress={() => router.navigate('/monitor')}
                      style={({ pressed }) => [styles.linkPill, pressed && styles.pressed]}
                    >
                      <Label variant="smallBold" tone="accent">Live Monitor →</Label>
                    </Pressable>
                  </View>
                </View>
              )}
            </Surface>

            <Surface kind="card" style={styles.formCard}>
              <View style={styles.farmsHeader}>
                <Label variant="title">{strings.serverTitle}</Label>
                <Label variant="caption" tone="sage">{activeServer}</Label>
              </View>
              <View style={styles.field}>
                <Label variant="label" tone="sage">IP:PORT OR URL</Label>
                <TextInput
                  style={styles.input}
                  value={serverInput}
                  onChangeText={(text) => {
                    setServerInput(text);
                    setServerError(null);
                    setServerStatus(null);
                  }}
                  placeholder={strings.serverPlaceholder}
                  placeholderTextColor={colors.muted}
                  autoCapitalize="none"
                  autoCorrect={false}
                  keyboardType="url"
                />
              </View>
              {serverError && <Label variant="caption" tone="accent">{serverError}</Label>}
              {serverStatus && <Label variant="caption" tone="accent">{serverStatus}</Label>}
              <View style={styles.farmActions}>
                <Chip label={strings.saveServer} accent onPress={() => void handleSaveServer()} />
                <Chip label={strings.resetServer} onPress={() => void handleResetServer()} />
              </View>
            </Surface>
          </View>
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.forest950 },
  flex: { flex: 1 },
  scroll: { padding: space.gutter, paddingBottom: space.xl },
  container: { width: '100%', maxWidth: size.maxContent, alignSelf: 'center', gap: space.lg },
  header: { flexDirection: 'row', alignItems: 'center', gap: space.md },
  logoWrap: { flex: 1 },
  section: { gap: space.md },
  formCard: { padding: space.lg, gap: space.md },
  field: { gap: space.xs },
  input: {
    ...typography.input,
    color: colors.cream,
    backgroundColor: colors.forest900,
    borderWidth: size.hairline,
    borderColor: colors.border,
    borderRadius: radius.tile,
    paddingHorizontal: space.md,
    paddingVertical: space.sm + 2,
  },
  profileCard: { padding: space.lg },
  profileRow: { flexDirection: 'row', alignItems: 'center', gap: space.md },
  farmsHeader: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', marginTop: space.sm },
  farmList: { gap: space.md },
  farmCard: { padding: space.lg, gap: space.sm },
  farmRow: { flexDirection: 'row', alignItems: 'flex-start', gap: space.md },
  farmActions: { flexDirection: 'row', alignItems: 'center', flexWrap: 'wrap', gap: space.sm },
  thresholdCardHeader: { flexDirection: 'row', alignItems: 'flex-start', justifyContent: 'space-between', gap: space.md },
  presetBadge: {
    paddingHorizontal: space.md,
    paddingVertical: space.xs + 2,
    borderRadius: radius.pill,
    backgroundColor: colors.chip,
    borderWidth: size.hairline,
    borderColor: colors.border,
  },
  presetBadgeCustom: {
    backgroundColor: colors.highlight,
    borderColor: colors.accentBorder,
  },
  thresholdGroup: { gap: space.xs },
  thresholdHeader: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: space.sm },
  valueBadge: {
    paddingHorizontal: space.sm + 2,
    paddingVertical: space.xxs + 1,
    borderRadius: radius.pill,
    backgroundColor: colors.highlight,
    borderWidth: size.hairline,
    borderColor: colors.accentBorder,
  },
  thresholdControlsRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    flexWrap: 'wrap',
    gap: space.sm,
  },
  optionChipsWrap: { flexDirection: 'row', flexWrap: 'wrap', gap: space.xs, flex: 1, minWidth: 160 },
  optionChip: {
    minHeight: 36,
    paddingHorizontal: space.md,
    paddingVertical: space.xs + 2,
    borderRadius: radius.pill,
    backgroundColor: colors.chip,
    borderWidth: size.hairline,
    borderColor: colors.border,
    justifyContent: 'center',
    alignItems: 'center',
  },
  optionChipActive: {
    backgroundColor: colors.accent,
    borderColor: colors.accent,
  },
  pressed: { transform: [{ scale: motion.pressScale }] },
  stepper: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: colors.forest900,
    borderWidth: size.hairline,
    borderColor: colors.border,
    borderRadius: radius.pill,
    overflow: 'hidden',
  },
  stepBtn: {
    minWidth: size.touch,
    minHeight: 36,
    alignItems: 'center',
    justifyContent: 'center',
    paddingHorizontal: space.sm,
  },
  stepBtnDisabled: { opacity: motion.disabledOpacity },
  stepDivider: { width: size.hairline, height: 20, backgroundColor: colors.border },
  explainedBox: { padding: space.md, gap: space.xs + 2 },
  explainedRow: { flexDirection: 'row', alignItems: 'flex-start', gap: space.sm },
  explainedDot: {
    width: size.dot - 2,
    height: size.dot - 2,
    borderRadius: radius.pill,
    backgroundColor: colors.accent,
    marginTop: 6,
  },
  activePlanHint: {
    paddingTop: space.sm,
    borderTopWidth: size.hairline,
    borderTopColor: colors.border,
    gap: space.xs + 2,
  },
  linkPill: {
    paddingHorizontal: space.md,
    paddingVertical: space.xs + 2,
    borderRadius: radius.pill,
    backgroundColor: colors.highlight,
    borderWidth: size.hairline,
    borderColor: colors.accentBorder,
  },
});
