import { useMemo, useState } from 'react';
import { RefreshControl, ScrollView, StyleSheet, View, useWindowDimensions } from 'react-native';
import { useOffline, viewState } from '@/api/query';
import { ActionCard, TimelineCard } from '@/components/cards';
import { Feedback } from '@/components/feedback';
import { Backdrop, FieldOverlay } from '@/components/FieldMap';
import { PlanSheet } from '@/components/PlanSheet';
import { Label, Progress, Stat } from '@/components/primitives';
import { strings } from '@/i18n/strings';
import { usePlanner } from '@/state/usePlanner';
import { colors, size, space } from '@/theme/tokens';
import { formatNumber } from '@/utils/format';
import { tap } from '@/utils/haptics';
import { useFieldMap } from '../area/hooks';
import { useCountryData } from '../country/hooks';
import { FlowScreen, go, ScrollFrame } from '../planner/FlowScreen';
import { useStrategies } from '../strategy/hooks';
import { getSelectedStrategy } from '../strategy/model';
import { usePlan } from './hooks';
import type { Plan } from './model';

const tabs = [{ id: 'overview', label: strings.overview }, { id: 'timeline', label: strings.timeline }];

function Overview({ plan }: { plan: Plan }) {
  const { fontScale, width } = useWindowDimensions();
  const wrap = fontScale > 1.2 || width < 360;
  const stats = [
    [strings.type, plan.crop.category], [strings.area, plan.area], [strings.yield, plan.crop.cropYield, true],
    [strings.seasons, formatNumber(plan.timeline.length), true], [strings.status, plan.strategy],
    [strings.starts, plan.first.season], [strings.water, plan.crop.waterLabel, true], [strings.nextCrop, plan.nextCrop ?? strings.noValue],
  ] as const;
  return (
    <>
      <ActionCard label={strings.nextStep} prefix={strings.action} action={strings.sow(plan.first.crop.name)} season={plan.first.label} />
      <View style={styles.grid}>
        {stats.map(([label, value, accent]) => <Stat label={label} value={value} accent={accent} key={label} compact={!wrap}
          style={wrap ? styles.wideStat : styles.smallStat} />)}
      </View>
      <View>
        <View style={styles.water}>
          <Label variant="label" tone="sage">{strings.waterNeed}</Label>
          <Label variant="smallBold" tone="accent">{plan.crop.waterLabel}</Label>
        </View>
        <Progress value={plan.crop.water} label={strings.waterNeed} />
      </View>
    </>
  );
}

export default function PlanScreen() {
  const countryId = usePlanner((draft) => draft.countryId);
  const points = usePlanner((draft) => draft.points);
  const closed = usePlanner((draft) => draft.closed);
  const reached = usePlanner((draft) => draft.reached);
  const strategyId = usePlanner((draft) => draft.strategyId);
  const cropId = usePlanner((draft) => draft.cropId);
  const sowingDate = usePlanner((draft) => draft.sowingDate);
  const reset = usePlanner((draft) => draft.reset);
  const bootstrap = useCountryData();
  const strategies = useStrategies(countryId);
  const selected = getSelectedStrategy(strategies.data, strategyId, bootstrap.data?.defaultStrategyId);
  const map = useFieldMap(countryId);
  const draft = useMemo(() => reached >= 5 && countryId && closed && selected ? {
    countryId, points, strategyId: selected.id, cropId: selected.requiresCrop ? cropId ?? bootstrap.data?.defaultCropId : undefined, sowingDate,
  } : null, [reached, countryId, closed, selected, points, cropId, bootstrap.data?.defaultCropId, sowingDate]);
  const query = usePlan(draft);
  const offline = useOffline();
  const state = viewState({
    isPaused: query.isPaused || strategies.isPaused || bootstrap.isPaused,
    isPending: strategies.isPending || bootstrap.isPending || (!!draft && query.isPending),
    isError: query.isError || strategies.isError || bootstrap.isError,
  }, offline, !!query.data);
  const [active, setActive] = useState(tabs[0].id);
  const refresh = () => {
    void strategies.refetch();
    void bootstrap.refetch();
    void map.refetch();
    if (draft) void query.refetch();
  };
  const plan = query.data;

  return (
    <FlowScreen step={5} action={strings.restart} onNext={() => { reset(); go(1); }}>
      {(inset) => <>
        <View style={styles.planBase} />
        {map.data && <Backdrop image={map.data.image} kind="parcel" />}
        <View pointerEvents="none" style={styles.parcel}><FieldOverlay points={points} closed fit /></View>
        <PlanSheet subtitle={plan ? strings.planSubtitle(plan.area, plan.timeline.length) : undefined}
          tabs={tabs} active={active} bottom={inset.bottom} onTab={(id) => { tap(); setActive(id); }}>
          <ScrollFrame bottom={inset.bottom}>
            <ScrollView showsVerticalScrollIndicator={false}
              refreshControl={<RefreshControl refreshing={query.isRefetching || strategies.isRefetching} onRefresh={refresh} colors={[colors.accent]} tintColor={colors.accent} />}
              contentContainerStyle={styles.content}>
              <Feedback state={state} layout="plan" onRetry={refresh}>
                {plan && (active === 'overview' ? <Overview plan={plan} /> : plan.timeline.map((item, index) =>
                  <TimelineCard key={item.id} season={item.label} crop={item.crop.name} summary={item.summary} note={item.note} first={index === 0} />))}
              </Feedback>
            </ScrollView>
          </ScrollFrame>
        </PlanSheet>
      </>}
    </FlowScreen>
  );
}

const styles = StyleSheet.create({
  planBase: { ...StyleSheet.absoluteFill, backgroundColor: colors.forest900 },
  parcel: { position: 'absolute', start: 0, end: 0, top: size.parcelTop, height: size.parcelHeight },
  content: { paddingHorizontal: space.gutter, paddingVertical: space.lg, gap: space.md },
  grid: { flexDirection: 'row', flexWrap: 'wrap', rowGap: space.lg, marginTop: space.xs },
  smallStat: { flexBasis: '25%', paddingEnd: space.sm },
  wideStat: { flexBasis: '50%', paddingEnd: space.sm },
  water: { flexDirection: 'row', justifyContent: 'space-between', marginBottom: space.tight },
});
