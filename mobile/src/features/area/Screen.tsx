import { useMemo, useState } from 'react';
import { RefreshControl, StyleSheet, View } from 'react-native';
import { useOffline, viewState } from '@/api/query';
import { FieldMap } from '@/components/FieldMap';
import { Feedback } from '@/components/feedback';
import { SearchField, Stat } from '@/components/primitives';
import { Suggestions } from '@/components/Suggestions';
import { useDebouncedValue } from '@/hooks/useDebouncedValue';
import { useSearchFocus } from '@/hooks/useSearchFocus';
import { strings } from '@/i18n/strings';
import { usePlanner } from '@/state/usePlanner';
import { colors, size, space } from '@/theme/tokens';
import { tap } from '@/utils/haptics';
import { continueTo, FlowScreen, ScreenScroll } from '../planner/FlowScreen';
import { useFieldMap, useMeasurement, usePlaces } from './hooks';
import { polygonArea } from './model';

export default function AreaScreen() {
  const country = usePlanner((draft) => draft.countryId);
  const points = usePlanner((draft) => draft.points);
  const closed = usePlanner((draft) => draft.closed);
  const { addPoint, close, clearField } = usePlanner.getState();
  const field = useMemo(() => closed ? { countryId: country, points } : null, [closed, country, points]);
  const map = useFieldMap(country);
  const measurement = useMeasurement(field);
  const offline = useOffline();
  const state = viewState(map, offline, !!map.data);
  const measureState = viewState(measurement, offline, !!measurement.data);
  const [place, setPlace] = useState('');
  const focus = useSearchFocus();
  const placeQuery = useDebouncedValue(place.trim());
  const places = usePlaces(country, placeQuery, focus.focused);
  const canClose = !closed && polygonArea(points) > 0;
  const refreshing = map.isRefetching || (closed && measurement.isRefetching);
  const refresh = () => {
    void map.refetch();
    if (field) void measurement.refetch();
  };

  return (
    <FlowScreen step={2} action={strings.next} disabled={state !== 'ready' || !closed || measureState !== 'ready'}
      busy={closed && measureState === 'loading'} onNext={() => continueTo(3)}>
      {(inset) => state === 'ready' && map.data ?
        <FieldMap image={map.data.image} points={points} closed={closed} canClose={canClose} top={inset.top} bottom={inset.bottom}
          onPoint={(point) => { tap(); addPoint(point); }}
          onClose={() => { tap(); close(); }} onReset={() => { tap(); clearField(); }}
          onRefresh={refresh}
          search={<>
            <SearchField glassy compact accessibilityLabel={strings.place} placeholder={strings.place} value={place}
              onFocus={focus.onFocus} onBlur={focus.onBlur} onChangeText={setPlace} />
            {focus.focused && place.trim() && <View style={styles.results}>
              {places.isError ? <Feedback state="error" layout="map" onRetry={() => void places.refetch()} /> :
                <Suggestions items={places.data?.map((item) => ({ id: item.id, label: item.name })) ?? []}
                  message={places.isPending || place.trim() !== placeQuery ? strings.loading : places.data?.length ? undefined : strings.noMatch}
                  onSelect={(id) => {
                    const match = places.data?.find((item) => item.id === id);
                    if (match) { setPlace(match.name); focus.dismiss(); }
                  }} />}
            </View>}
          </>}
          metrics={closed && measureState !== 'ready' ?
            <Feedback state={measureState} layout="plan" onRetry={() => void measurement.refetch()} /> :
            <View style={styles.metrics}>
              <Stat label={strings.hectares} value={measurement.data?.hectares ?? '0'} tile large accent={closed} muted={!closed} style={styles.largeTile} />
              <Stat label={strings.acres} value={measurement.data?.acres ?? '0'} tile style={styles.tile} />
              <Stat label={strings.km} value={measurement.data?.perimeter ?? '0'} tile style={styles.tile} />
            </View>} /> :
        <ScreenScroll inset={inset} refreshControl={<RefreshControl refreshing={refreshing} onRefresh={refresh} tintColor={colors.accent} colors={[colors.accent]} />}>
          <Feedback state={state} layout="map" onRetry={refresh} />
        </ScreenScroll>}
    </FlowScreen>
  );
}

const styles = StyleSheet.create({
  results: { position: 'absolute', start: 0, end: 0, top: size.control + space.sm },
  metrics: { flexDirection: 'row', gap: space.snug },
  tile: { flex: 1, minWidth: 0 },
  largeTile: { flex: 1.3, minWidth: 0 },
});
