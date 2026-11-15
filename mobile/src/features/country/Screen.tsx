import { useEffect, useRef, useState, type ComponentRef } from 'react';
import { RefreshControl, StyleSheet, View, type ScrollView } from 'react-native';
import { useOffline, viewState } from '@/api/query';
import { Logo, SeasonBadge, Workflow } from '@/components/cards';
import { Backdrop } from '@/components/FieldMap';
import { Feedback } from '@/components/feedback';
import { ErrorCard, Label, SearchField, Stat } from '@/components/primitives';
import { Suggestions } from '@/components/Suggestions';
import { useSearchFocus } from '@/hooks/useSearchFocus';
import { strings } from '@/i18n/strings';
import { usePlanner } from '@/state/usePlanner';
import { pictures } from '@/theme/images';
import { colors, size, space } from '@/theme/tokens';
import { useTheme } from '@/theme/useTheme';
import { formatNumber } from '@/utils/format';
import { FlowScreen, go, routes, ScreenScroll } from '../planner/FlowScreen';
import { useCountryData } from './hooks';
import type { Country } from './model';

const workflow = [
  { label: strings.workflow[0], icon: 'layers' },
  { label: strings.workflow[1], icon: 'sprout' },
  { label: strings.workflow[2], icon: 'redo' },
] as const;

export default function CountryScreen() {
  const query = useCountryData();
  const data = query.data;
  const offline = useOffline();
  const state = viewState(query, offline, !!data?.defaultCountry);
  const defaultCountry = data?.defaultCountry;
  const multipleSupported = data?.countries.some((item) => item.supported && item.id !== defaultCountry?.id);
  const chooseCountry = usePlanner((draft) => draft.chooseCountry);
  const [search, setSearch] = useState('');
  const [unavailable, setUnavailable] = useState('');
  const { dismiss, focused, open, panelProps } = useSearchFocus();
  const { reducedMotion } = useTheme();
  const scroll = useRef<ComponentRef<typeof ScrollView>>(null);
  const [viewportHeight, setViewportHeight] = useState(0);
  const [searchTop, setSearchTop] = useState(0);

  useEffect(() => {
    const resultsBottom = searchTop + size.primary + space.sm + size.searchResults;
    if (focused && viewportHeight > 0 && resultsBottom > viewportHeight) {
      scroll.current?.scrollTo({ y: Math.max(0, searchTop - space.gutter), animated: !reducedMotion });
    }
  }, [focused, reducedMotion, searchTop, viewportHeight]);

  const select = (country: Country) => {
    dismiss();
    if (!country.supported) {
      setSearch(country.name);
      setUnavailable(country.name);
      return;
    }
    setUnavailable('');
    setSearch('');
    chooseCountry(country.id);
    go(2);
  };
  const term = search.trim().toLocaleLowerCase();
  const results = data?.countries.filter((country) => country.name.toLocaleLowerCase().includes(term)) ?? [];
  const submit = () => {
    const match = results.find((country) => country.name.toLocaleLowerCase() === term)
      ?? (results.length === 1 ? results[0] : undefined);
    if (match) select(match);
  };

  return (
    <FlowScreen step={1} action={defaultCountry ? strings.begin(defaultCountry.name) : strings.next}
      disabled={state !== 'ready'} onNext={() => { if (defaultCountry) select(defaultCountry); }}>
      {(inset) => <>
        <Backdrop image={pictures.hero} kind="country" />
        <ScreenScroll inset={inset} contentContainerStyle={styles.content} scrollRef={scroll}
          onLayout={(event) => setViewportHeight(event.nativeEvent.layout.height)}
          refreshControl={<RefreshControl refreshing={query.isRefetching} onRefresh={() => void query.refetch()} tintColor={colors.accent} colors={[colors.accent]} />}>
          <View style={styles.top}>
            <Logo />
            {!!data?.season && <SeasonBadge label={strings.season(data.season)} />}
          </View>
          <View style={styles.hero}>
            <Label variant="hero" accessibilityRole="header">{strings.heroPrimary}{'\n'}<Label variant="hero" tone="accent">{strings.heroAccent}</Label></Label>
            <Label tone="secondary" style={styles.subtitle}>{strings.heroDescription}</Label>
          </View>
          <Feedback state={state} layout="country" onRetry={() => void query.refetch()}>
            <View {...panelProps} style={styles.searchSection} onLayout={(event) => setSearchTop(event.nativeEvent.layout.y)}>
              <SearchField glassy focused={focused} invalid={!!unavailable} accessibilityLabel={strings.country}
                placeholder={strings.countryPlaceholder} value={search} onFocus={open} onPressIn={open}
                returnKeyType="search" submitBehavior="submit" onSubmitEditing={submit}
                onChangeText={(text) => { setSearch(text); setUnavailable(''); }} />
              {!!unavailable && defaultCountry && (
                <ErrorCard title={strings.unsupportedCountry(unavailable)} hint={multipleSupported ? strings.chooseSupportedCountry : strings.supportedCountry(defaultCountry.name)} />
              )}
              {focused && (
                <Suggestions items={results.map((country) => ({
                  id: country.id, label: country.name, detail: country.supported ? strings.ready : strings.unavailable, accent: country.supported,
                }))} message={!results.length ? strings.noMatch : undefined}
                onSelect={(id) => { const country = results.find((item) => item.id === id); if (country) select(country); }} />
              )}
            </View>
            {data && <>
              <View style={styles.tiles}>
                <Stat label={strings.crops} value={data.crops} tile accent large style={styles.tile} />
                <Stat label={strings.seasons} value={data.seasons} tile accent large style={styles.tile} />
                <Stat label={strings.steps} value={formatNumber(routes.length)} tile accent large style={styles.tile} />
              </View>
              <Workflow items={workflow} />
            </>}
          </Feedback>
        </ScreenScroll>
      </>}
    </FlowScreen>
  );
}

const styles = StyleSheet.create({
  content: { flexGrow: 1 },
  top: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: space.sm },
  hero: { marginTop: space.gutter, marginBottom: space.md },
  subtitle: { marginTop: space.md },
  searchSection: { gap: space.sm },
  tiles: { flexDirection: 'row', gap: space.snug, marginTop: space.sm },
  tile: { flex: 1, minWidth: 0 },
});
