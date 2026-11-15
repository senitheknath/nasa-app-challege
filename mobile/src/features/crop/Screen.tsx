import { useState } from 'react';
import { FlatList, RefreshControl, ScrollView, StyleSheet, View } from 'react-native';
import { useOffline, viewState } from '@/api/query';
import { CropCard } from '@/components/cards';
import { DateField } from '@/components/DateField';
import { Feedback } from '@/components/feedback';
import { Backdrop } from '@/components/FieldMap';
import { Chip, SearchField, Segmented, Surface } from '@/components/primitives';
import { useDebouncedValue } from '@/hooks/useDebouncedValue';
import { strings } from '@/i18n/strings';
import { usePlanner } from '@/state/usePlanner';
import { pictures } from '@/theme/images';
import { colors, space } from '@/theme/tokens';
import { calendarDate } from '@/utils/format';
import { tap } from '@/utils/haptics';
import { useCountryData } from '../country/hooks';
import { continueTo, FlowScreen } from '../planner/FlowScreen';
import { useCategories, useCrops } from './hooks';

const presets = [0, -30, -180];

export default function CropScreen() {
  const country = usePlanner((draft) => draft.countryId);
  const selected = usePlanner((draft) => draft.cropId);
  const date = usePlanner((draft) => draft.sowingDate);
  const { chooseCrop, setDate } = usePlanner.getState();
  const bootstrap = useCountryData();
  const categories = useCategories(country);
  const [choice, setChoice] = useState('');
  const [search, setSearch] = useState('');
  const query = useCrops(country, useDebouncedValue(search.trim()), choice);
  const offline = useOffline();
  const crops = query.data?.pages.flatMap((page) => page.items) ?? [];
  const state = viewState(query, offline, crops.length > 0);
  const categoryState = viewState(categories, offline, !!categories.data?.length);
  const cropId = selected ?? bootstrap.data?.defaultCropId ?? crops[0]?.id;
  const refresh = () => {
    void query.refetch();
    void categories.refetch();
    void bootstrap.refetch();
  };
  const more = () => {
    if (query.hasNextPage && !query.isFetching) void query.fetchNextPage();
  };

  return (
    <FlowScreen step={4} action={strings.generate} disabled={offline || !cropId || (state !== 'ready' && state !== 'empty')}
      onNext={() => { if (cropId) { chooseCrop(cropId); continueTo(5); } }}>
      {(inset) => <>
        <Backdrop image={pictures.field} kind="field" />
        <FlatList data={state === 'ready' ? crops : []} keyExtractor={(item) => item.id}
          contentContainerStyle={[styles.content, { paddingTop: inset.top, paddingBottom: inset.bottom }]}
          keyboardShouldPersistTaps="handled" showsVerticalScrollIndicator={false}
          refreshControl={<RefreshControl refreshing={query.isRefetching || categories.isRefetching} onRefresh={refresh} colors={[colors.accent]} tintColor={colors.accent} />}
          onEndReached={query.isFetchNextPageError ? undefined : more} onEndReachedThreshold={.35}
          ListHeaderComponent={<View style={styles.header}>
            <Surface style={styles.dates}>
              <DateField value={date} onChange={setDate} />
              <ScrollView horizontal showsHorizontalScrollIndicator={false} keyboardShouldPersistTaps="handled" contentContainerStyle={styles.presets}>
                {presets.map((offset, index) => <Chip key={offset} label={strings.presets[index]} onPress={() => { tap(); setDate(calendarDate(new Date(), offset)); }} />)}
              </ScrollView>
            </Surface>
            <Feedback state={categoryState} layout="map" onRetry={() => void categories.refetch()}>
              <Segmented scroll items={[{ id: '', label: strings.all }, ...(categories.data ?? [])]} value={choice}
                onChange={(id) => { tap(); setChoice(id); }} />
            </Feedback>
            <SearchField accessibilityLabel={strings.searchCrop} placeholder={strings.searchCrop} value={search} onChangeText={setSearch} />
          </View>}
          renderItem={({ item }) => (
            <CropCard category={item.category} name={item.name} cropYield={item.cropYield} water={item.water}
              waterLabel={item.waterLabel} selected={item.id === cropId} onPress={() => { tap(); chooseCrop(item.id); }} />
          )}
          ListEmptyComponent={<Feedback state={state} layout="crop" emptyTitle={strings.noCrop} emptyHint={strings.noCropHint}
            onRetry={state === 'empty' && (search || choice) ? undefined : refresh} />}
          ListFooterComponent={state === 'ready' && query.hasNextPage ? (
            query.isFetchingNextPage ? <Feedback state="loading" layout="crop" /> :
            <Chip label={query.isFetchNextPageError ? strings.tryAgain : strings.loadMore} onPress={more} />
          ) : undefined}
        />
      </>}
    </FlowScreen>
  );
}

const styles = StyleSheet.create({
  content: { paddingHorizontal: space.gutter, gap: space.md },
  header: { gap: space.md },
  dates: { padding: space.lg, gap: space.md },
  presets: { gap: space.sm },
});
