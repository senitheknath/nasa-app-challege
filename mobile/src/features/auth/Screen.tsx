import { router } from 'expo-router';
import { useState } from 'react';
import { KeyboardAvoidingView, Platform, ScrollView, StyleSheet, TextInput, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { ApiError } from '@/api/errors';
import { Logo } from '@/components/cards';
import { Chip, ErrorCard, IconButton, Label, Message, PrimaryButton, Segmented, Surface } from '@/components/primitives';
import { strings } from '@/i18n/strings';
import { usePlanner } from '@/state/usePlanner';
import { colors, radius, size, space } from '@/theme/tokens';
import { typography } from '@/theme/typography';
import { formatNumber } from '@/utils/format';
import { useAuthMe, useAuthSubmit, useDeleteFarm, useSavedFarms, useSaveFarm, useSignOut } from './hooks';
import type { SavedFarm } from './model';

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
    router.replace(farm.crop_id ? '/plan' : '/area');
  };

  const farms = farmsQuery.data?.farms ?? [];

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
  farmActions: { flexDirection: 'row', alignItems: 'center', gap: space.sm },
});
