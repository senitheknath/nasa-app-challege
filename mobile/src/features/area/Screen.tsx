import { router } from 'expo-router';
import { useEffect, useMemo, useState } from 'react';
import { RefreshControl, StyleSheet, View } from 'react-native';
import { useOffline, viewState } from '@/api/query';
import { FieldMap } from '@/components/FieldMap';
import { Feedback } from '@/components/feedback';
import { Chip, Label, SearchField, Stat, Surface } from '@/components/primitives';
import { Suggestions } from '@/components/Suggestions';
import { useDebouncedValue } from '@/hooks/useDebouncedValue';
import { useSearchFocus } from '@/hooks/useSearchFocus';
import { strings } from '@/i18n/strings';
import { usePlanner } from '@/state/usePlanner';
import { colors, radius, size, space } from '@/theme/tokens';
import { formatNumber } from '@/utils/format';
import { tap } from '@/utils/haptics';
import { continueTo, FlowScreen, ScreenScroll } from '../planner/FlowScreen';
import { useFieldMap, useMeasurement, usePlaces } from './hooks';
import { isValidBoundary } from './model';

export default function AreaScreen() {
  const country = usePlanner((draft) => draft.countryId);
  const latitude = usePlanner((draft) => draft.latitude);
  const longitude = usePlanner((draft) => draft.longitude);
  const zoom = usePlanner((draft) => draft.zoom);
  const points = usePlanner((draft) => draft.points);
  const boundary = usePlanner((draft) => draft.boundary);
  const closed = usePlanner((draft) => draft.closed);
  const { addPoint, addGeoCorner, close, clearField, setCenter, setAreaHa } = usePlanner.getState();
  const field = useMemo(
    () => (closed ? { countryId: country, points, latitude, longitude, boundary } : null),
    [boundary, closed, country, latitude, longitude, points],
  );
  const map = useFieldMap(country);
  const measurement = useMeasurement(field);
  const offline = useOffline();
  const state = viewState(map, offline, !!map.data);
  const measureState = viewState(measurement, offline, !!measurement.data);
  const [place, setPlace] = useState('');
  const focus = useSearchFocus();
  const placeQuery = useDebouncedValue(place.trim());
  const placeSettled = place.trim() === placeQuery;
  const places = usePlaces(country, placeQuery, focus.focused && placeSettled);
  const results = placeSettled ? places.data ?? [] : [];

  useEffect(() => {
    if (map.data && !closed && points.length === 0) {
      setCenter(map.data.latitude, map.data.longitude, Math.max(map.data.zoom, 12));
    }
  }, [closed, map.data, points.length, setCenter]);

  useEffect(() => {
    if (measurement.data) {
      setAreaHa(measurement.data.rawHectares);
    }
  }, [measurement.data, setAreaHa]);

  const selectPlace = (id: string) => {
    const match = results.find((item) => item.id === id);
    if (match) {
      setPlace(match.name);
      if (match.latitude !== undefined && match.longitude !== undefined) {
        setCenter(match.latitude, match.longitude, 15);
      }
      focus.dismiss();
    }
  };
  const valid = useMemo(() => isValidBoundary(points), [points]);
  const canClose = !closed && valid;
  const refreshing = map.isRefetching || (closed && measurement.isRefetching);
  const refresh = () => {
    void map.refetch();
    if (field) void measurement.refetch();
  };
  const hasTelemetry = !!(measurement.data?.ph || measurement.data?.rainfall || measurement.data?.drainage);

  return (
    <FlowScreen step={2} action={strings.next} disabled={state !== 'ready' || !closed || measureState !== 'ready'}
      busy={closed && measureState === 'loading'} onNext={() => continueTo(3)}>
      {(inset) => state === 'ready' && map.data ?
        <FieldMap image={map.data.image} points={points} boundary={boundary} center={{ latitude, longitude }} zoom={zoom}
          closed={closed} canClose={canClose} invalidBoundary={!closed && points.length >= 3 && !valid} top={inset.top} bottom={inset.bottom}
          onPoint={(point) => {
            if (focus.focused) { focus.dismiss(); return; }
            if (!closed) { tap(); addPoint(point); }
          }}
          onGeoPoint={(point, geo) => {
            if (focus.focused) { focus.dismiss(); return; }
            if (!closed) { tap(); addGeoCorner(point, geo); }
          }}
          onCenterChange={(lat, lon, z) => setCenter(lat, lon, z)}
          onClose={() => { tap(); close(); }} onReset={() => { tap(); clearField(); }}
          onRefresh={focus.focused ? focus.dismiss : refresh}
          search={<View {...focus.panelProps}>
            <SearchField glassy compact accessibilityLabel={strings.place} placeholder="Search place, address, or lat, lon" value={place}
              onFocus={focus.open} onPressIn={focus.open} onChangeText={setPlace}
              returnKeyType="search" submitBehavior="submit" onSubmitEditing={() => { if (results.length > 0) selectPlace(results[0].id); }} />
            {focus.focused && <View style={styles.results}>
              {placeSettled && places.isError && !results.length ? <Feedback state="error" layout="map" onRetry={() => void places.refetch()} /> :
                <Suggestions items={results.map((item) => ({ id: item.id, label: item.name, detail: item.detail }))}
                  message={!placeSettled || places.isPending ? strings.loading : results.length ? undefined : strings.noMatch}
                  onSelect={selectPlace} />}
            </View>}
          </View>}
          metrics={closed && measureState !== 'ready' ?
            <Feedback state={measureState} layout="metrics" onRetry={() => void measurement.refetch()} /> :
            <View style={styles.metricsWrap}>
              <View style={styles.metrics}>
                <Stat label={strings.hectares} value={measurement.data?.hectares ?? '0'} tile large accent={closed} muted={!closed} style={styles.largeTile} />
                <Stat label={strings.acres} value={measurement.data?.acres ?? '0'} tile style={styles.tile} />
                <Stat label={strings.km} value={measurement.data?.perimeter ?? '0'} tile style={styles.tile} />
              </View>
              {closed && hasTelemetry && (
                <Surface kind="glass" rounding={radius.tile} style={styles.telemetry}>
                  <View style={styles.telemetryInfo}>
                    {!!measurement.data?.ph && <Label variant="caption" tone="cream">pH {measurement.data.ph}</Label>}
                    {!!measurement.data?.drainage && <Label variant="caption" tone="sage">{measurement.data.drainage}</Label>}
                    {!!measurement.data?.rainfall && <Label variant="caption" tone="accent">{measurement.data.rainfall}</Label>}
                    <Label variant="caption" tone="sage">{formatNumber(latitude, 2)}, {formatNumber(longitude, 2)}</Label>
                  </View>
                  <Chip label={strings.saveFarm} onPress={() => router.push('/login')} />
                </Surface>
              )}
            </View>} /> :
        <ScreenScroll inset={inset} refreshControl={<RefreshControl refreshing={refreshing} onRefresh={refresh} tintColor={colors.accent} colors={[colors.accent]} />}>
          <Feedback state={state} layout="map" onRetry={refresh} />
        </ScreenScroll>}
    </FlowScreen>
  );
}

const styles = StyleSheet.create({
  results: { position: 'absolute', start: 0, end: 0, top: size.control + space.sm },
  metricsWrap: { gap: space.snug },
  metrics: { flexDirection: 'row', gap: space.snug },
  telemetry: {
    paddingHorizontal: space.md,
    paddingVertical: space.sm,
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: space.sm,
  },
  telemetryInfo: { flex: 1, flexDirection: 'row', flexWrap: 'wrap', alignItems: 'center', gap: space.sm },
  tile: { flex: 1, minWidth: 0 },
  largeTile: { flex: 1.3, minWidth: 0 },
});
