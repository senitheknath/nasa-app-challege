import { useState } from 'react';
import { ScrollView, StyleSheet, View } from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { ActionCard, CropCard, Logo, SeasonBadge, StrategyCard, TimelineCard, Workflow } from '@/components/cards';
import { DateField } from '@/components/DateField';
import { Feedback, type LoadState, type SkeletonLayout } from '@/components/feedback';
import { FieldMap } from '@/components/FieldMap';
import { ScreenFooter, ScreenHeader } from '@/components/navigation';
import { PlanSheet } from '@/components/PlanSheet';
import { Chip, ErrorCard, IconButton, Label, PrimaryButton, Progress, SearchField, Segmented, Stat } from '@/components/primitives';
import { Suggestions } from '@/components/Suggestions';
import { mapCrop } from '@/features/crop/model';
import { strings } from '@/i18n/strings';
import { countries, crops, strategies } from '@/mocks/catalog';
import { pictures } from '@/theme/images';
import { colors, size, space } from '@/theme/tokens';
import { calendarDate } from '@/utils/format';

const noop = () => undefined;
const tabs = [{ id: 'overview', label: strings.overview }, { id: 'timeline', label: strings.timeline }];
const states: LoadState[] = ['empty', 'error', 'offline'];
const layouts: SkeletonLayout[] = ['country', 'map', 'strategy', 'crop', 'plan'];
const points = [{ x: 15, y: 35 }, { x: 74, y: 30 }, { x: 70, y: 74 }];
const selectedCrop = mapCrop(crops[0]);
const workflow = [
  { label: strings.workflow[0], icon: 'layers' }, { label: strings.workflow[1], icon: 'sprout' }, { label: strings.workflow[2], icon: 'redo' },
] as const;

export default function Gallery() {
  const [active, setActive] = useState(tabs[0].id);
  const [date, setDate] = useState(calendarDate);
  const [search, setSearch] = useState('');
  const [closed, setClosed] = useState(false);

  return (
    <SafeAreaView style={styles.root}>
      <ScrollView keyboardShouldPersistTaps="handled" contentContainerStyle={styles.content}>
        <Label variant="heading">{strings.gallery}</Label>
        <Label variant="title">{strings.galleryLabels[0]}</Label>
        <View style={styles.row}>
          <IconButton name="check" label={strings.ready} onPress={noop} tone="accent" />
          <IconButton name="layers" label={strings.draw} onPress={noop} />
          <IconButton name="back" label={strings.back} onPress={noop} tone="dark" />
          <IconButton name="trash" label={strings.reset} onPress={noop} disabled />
        </View>
        <PrimaryButton label={strings.next} onPress={noop} />
        <PrimaryButton label={strings.next} onPress={noop} disabled />
        <PrimaryButton label={strings.generate} onPress={noop} busy />
        <Label variant="title">{strings.galleryLabels[1]}</Label>
        <ScreenHeader title={strings.strategyTitle} subtitle={strings.stepSubtitle(countries[10].name, 3, 5)} top={0} onBack={noop} onCountry={noop} />
        <ScreenFooter label={strings.next} current={3} reached={4} onNext={noop} onStep={noop} bottom={0} />
        <Label variant="title">{strings.galleryLabels[2]}</Label>
        <SearchField glassy accessibilityLabel={strings.country} placeholder={strings.countryPlaceholder} value={search} onChangeText={setSearch} />
        <SearchField glassy compact focused value={countries[10].name} editable={false} />
        <SearchField glassy invalid editable={false} value={countries[0].name} />
        <Suggestions items={[0, 10].map((index) => ({ id: countries[index].id, label: countries[index].name,
          accent: countries[index].supported, detail: countries[index].supported ? strings.ready : strings.unavailable }))} onSelect={noop} />
        <Suggestions items={[]} message={strings.noMatch} onSelect={noop} />
        <DateField value={date} onChange={setDate} />
        <Label variant="title">{strings.galleryLabels[3]}</Label>
        <View style={styles.row}><Logo /><SeasonBadge label={strings.season('Maha')} /></View>
        <Workflow items={workflow} />
        <Segmented items={tabs} value={active} onChange={setActive} />
        <View style={styles.row}>
          <Chip label={strings.presets[0]} onPress={noop} />
          <Chip label={strings.ready} accent />
          <Chip label={strings.unavailable} />
        </View>
        <View style={styles.row}>
          <Stat label={strings.hectares} value="42.1" tile accent large />
          <Stat label={strings.acres} value="104.0" tile />
          <Stat label={strings.km} value="0" tile muted />
        </View>
        {[0, selectedCrop.water, 100].map((value) => <Progress key={value} label={strings.waterNeed} value={value} />)}
        {strategies.map((strategy, index) => <StrategyCard key={strategy.id} {...strategy} selected={index === 2} onPress={noop} />)}
        {[true, false].map((selected) => <CropCard key={String(selected)} {...selectedCrop} selected={selected} onPress={noop} />)}
        <Label variant="title">{strings.galleryLabels[4]}</Label>
        <View style={styles.demoMap}>
          <FieldMap image={pictures.aerial} points={points} closed={closed} canClose={!closed} top={space.lg} bottom={space.lg}
            search={<SearchField glassy compact value={strings.place} editable={false} />}
            metrics={<Stat label={strings.hectares} value="42.1" tile accent large />}
            onPoint={noop} onClose={() => setClosed(true)} onReset={() => setClosed(false)} />
        </View>
        <View style={styles.demoSheet}>
          <PlanSheet subtitle={strings.planSubtitle('42.1 ha', 4)} tabs={tabs} active={active} onTab={setActive}>
            <View style={styles.sheetBody}>
              {active === 'overview'
                ? <ActionCard label={strings.nextStep} prefix={strings.action} action={strings.sow(selectedCrop.name)} season="Maha 2026" />
                : [true, false].map((first) => <TimelineCard key={String(first)} first={first} season="Maha 2026" crop={selectedCrop.name}
                  summary={strings.cropSubtitle(selectedCrop.category, selectedCrop.cropYield)} note={strings.ready} />)}
            </View>
          </PlanSheet>
        </View>
        <Label variant="title">{strings.galleryLabels[5]}</Label>
        <ErrorCard title={strings.unsupportedCountry(countries[0].name)} hint={strings.supportedCountry(countries[10].name)} />
        {states.map((state) => <Feedback key={state} state={state} layout="plan" onRetry={noop} />)}
        {layouts.map((layout) => <Feedback key={layout} state="loading" layout={layout} />)}
      </ScrollView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.forest950 },
  content: { width: '100%', maxWidth: size.maxContent, alignSelf: 'center', padding: space.gutter, gap: space.md },
  row: { flexDirection: 'row', flexWrap: 'wrap', alignItems: 'center', gap: space.sm },
  demoMap: { height: size.grid * 8, overflow: 'hidden' },
  demoSheet: { height: size.grid * 8, backgroundColor: colors.forest700, overflow: 'hidden' },
  sheetBody: { padding: space.lg, gap: space.sm },
});
