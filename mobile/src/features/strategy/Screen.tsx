import { useMemo } from 'react';
import { RefreshControl, StyleSheet, View } from 'react-native';
import { useOffline, viewState } from '@/api/query';
import { StrategyCard } from '@/components/cards';
import { Feedback } from '@/components/feedback';
import { Backdrop } from '@/components/FieldMap';
import { Label, Stat, Surface } from '@/components/primitives';
import { strings } from '@/i18n/strings';
import { usePlanner } from '@/state/usePlanner';
import { pictures } from '@/theme/images';
import { colors, space } from '@/theme/tokens';
import { tap } from '@/utils/haptics';
import { useMeasurement } from '../area/hooks';
import { useCountryData } from '../country/hooks';
import { continueTo, FlowScreen, ScreenScroll } from '../planner/FlowScreen';
import { useStrategies } from './hooks';
import { getSelectedStrategy } from './model';

export default function StrategyScreen() {
  const countryId = usePlanner((draft) => draft.countryId);
  const latitude = usePlanner((draft) => draft.latitude);
  const longitude = usePlanner((draft) => draft.longitude);
  const points = usePlanner((draft) => draft.points);
  const boundary = usePlanner((draft) => draft.boundary);
  const closed = usePlanner((draft) => draft.closed);
  const chosen = usePlanner((draft) => draft.strategyId);
  const choose = usePlanner((draft) => draft.chooseStrategy);
  const country = useCountryData();
  const strategies = useStrategies(countryId);
  const field = useMemo(
    () => (closed ? { countryId, points, latitude, longitude, boundary } : null),
    [boundary, closed, countryId, latitude, longitude, points],
  );
  const measurement = useMeasurement(field);
  const selected = getSelectedStrategy(strategies.data, chosen, country.data?.defaultStrategyId);
  const offline = useOffline();
  const state = viewState({
    isPending: country.isPending || strategies.isPending || measurement.isPending,
    isError: country.isError || strategies.isError || measurement.isError,
    isPaused: country.isPaused || strategies.isPaused || measurement.isPaused,
  }, offline, !!selected && !!measurement.data);
  const refreshing = country.isRefetching || strategies.isRefetching || measurement.isRefetching;
  const refresh = () => {
    void country.refetch();
    void strategies.refetch();
    if (field) void measurement.refetch();
  };

  return (
    <FlowScreen step={3} action={strings.next} disabled={state !== 'ready'} onNext={() => {
      if (selected) {
        choose(selected.id);
        continueTo(selected.requiresCrop ? 4 : 5);
      }
    }}>
      {(inset) => <>
        <Backdrop image={pictures.field} kind="field" />
        <ScreenScroll inset={inset} refreshControl={<RefreshControl refreshing={refreshing} onRefresh={refresh} tintColor={colors.accent} colors={[colors.accent]} />}>
          <Feedback state={state} layout="strategy" onRetry={refresh}>
            <Surface style={styles.summary}>
              <View style={styles.area}>
                <Label variant="label" tone="sage">{strings.yourField}</Label>
                <Label variant="metric" tone="accent" style={styles.metric}>{measurement.data?.hectares} <Label variant="unit">{strings.units.hectares}</Label></Label>
              </View>
              <Label variant="caption" tone="sage">{strings.pickStatus}</Label>
            </Surface>
            {!!(measurement.data?.ph || measurement.data?.drainage || measurement.data?.rainfall || measurement.data?.temperature) && (
              <View style={styles.autofill}>
                <Stat label="Soil pH" value={measurement.data?.ph ?? strings.noValue} tile compact style={styles.statTile} />
                <Stat label="Drainage" value={measurement.data?.drainage ?? strings.noValue} tile compact style={styles.statTile} />
                <Stat label="Rainfall" value={measurement.data?.rainfall ?? strings.noValue} tile compact style={styles.statTile} />
                <Stat label="Mean Temp" value={measurement.data?.temperature ?? strings.noValue} tile compact style={styles.statTile} />
              </View>
            )}
            {strategies.data?.map((item) => (
              <StrategyCard key={item.id} selected={selected?.id === item.id} tag={item.tag} title={item.title} description={item.description}
                onPress={() => { tap(); choose(item.id); }} />
            ))}
          </Feedback>
        </ScreenScroll>
      </>}
    </FlowScreen>
  );
}

const styles = StyleSheet.create({
  summary: { padding: space.lg, flexDirection: 'row', alignItems: 'flex-end', gap: space.sm },
  area: { flex: 1 },
  metric: { marginTop: space.xs },
  autofill: { flexDirection: 'row', flexWrap: 'wrap', gap: space.snug },
  statTile: { flex: 1, minWidth: '45%' },
});
