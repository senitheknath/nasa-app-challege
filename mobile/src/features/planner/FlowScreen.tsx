import { Redirect, router } from 'expo-router';
import { useEffect, useState, type ComponentRef, type ReactNode, type Ref } from 'react';
import {
  Keyboard, KeyboardAvoidingView, Platform, ScrollView, StyleSheet, View, type ScrollViewProps,
} from 'react-native';
import Animated, { FadeInDown } from 'react-native-reanimated';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { ScreenFooter, ScreenHeader } from '@/components/navigation';
import { strings } from '@/i18n/strings';
import { usePlanner } from '@/state/usePlanner';
import { colors, motion, size, space } from '@/theme/tokens';
import { useTheme } from '@/theme/useTheme';
import { tap } from '@/utils/haptics';
import { useCountryData } from '../country/hooks';
import { useStrategies } from '../strategy/hooks';
import { getSelectedStrategy } from '../strategy/model';

export const routes = ['/', '/area', '/strategy', '/crop', '/plan'] as const;
export type Step = 1 | 2 | 3 | 4 | 5;
const titles = ['', strings.areaTitle, strings.strategyTitle, strings.cropTitle, strings.planTitle];

export function go(step: Step) {
  Keyboard.dismiss();
  tap();
  router.navigate(routes[step - 1]);
}

export function continueTo(step: Step) {
  usePlanner.getState().unlock(step);
  go(step);
}

export type Clearance = { top: number; bottom: number };

export function FlowScreen({ step, action, onNext, disabled, busy, children }: {
  step: Step; action: string; onNext: () => void; disabled?: boolean; busy?: boolean;
  children: (inset: Clearance) => ReactNode;
}) {
  const { reducedMotion } = useTheme();
  const countryId = usePlanner((draft) => draft.countryId);
  const chosenStrategy = usePlanner((draft) => draft.strategyId);
  const reached = usePlanner((draft) => draft.reached);
  const country = useCountryData();
  const strategies = useStrategies(step > 2 ? countryId : '');
  const selected = getSelectedStrategy(strategies.data, chosenStrategy, country.data?.defaultStrategyId);
  const skipCrop = selected?.requiresCrop === false;

  const safe = useSafeAreaInsets();
  const top = Platform.OS === 'web' ? Math.max(safe.top, size.webTop) : safe.top + space.md;
  const [header, setHeader] = useState(top + size.touch + space.xl);
  const [footer, setFooter] = useState(size.navigation + safe.bottom);
  const [editing, setEditing] = useState(false);

  useEffect(() => {
    const show = Keyboard.addListener('keyboardDidShow', () => setEditing(true));
    const hide = Keyboard.addListener('keyboardDidHide', () => setEditing(false));
    return () => { show.remove(); hide.remove(); };
  }, []);

  if (step > 1 && !countryId) return <Redirect href="/" />;
  if (step > reached) return <Redirect href={routes[reached - 1]} />;
  if (step === 4 && skipCrop) return <Redirect href="/strategy" />;

  const label = country.data?.countries.find((item) => item.id === countryId)?.name ?? '';
  const back = () => go(step === 5 && skipCrop ? 3 : Math.max(1, step - 1) as Step);

  return (
    <KeyboardAvoidingView behavior={Platform.OS === 'ios' ? 'padding' : undefined} style={styles.viewport}>
      <View style={styles.frame}>
        <Animated.View entering={reducedMotion ? undefined : FadeInDown.duration(motion.enter).withInitialValues({ transform: [{ translateY: motion.rise }] })}
          style={styles.viewport}>
          {children({ top: step === 1 ? top : header + space.md, bottom: editing ? size.keyboardClearance : Math.max(size.navigation, footer) })}
        </Animated.View>
        {step > 1 && (
          <View pointerEvents="box-none" style={styles.header} onLayout={(event) => setHeader(event.nativeEvent.layout.height)}>
            <ScreenHeader title={titles[step - 1]} subtitle={strings.stepSubtitle(label, step, routes.length)}
              top={top} onBack={back} onCountry={() => go(1)} />
          </View>
        )}
        {!editing && (
          <View pointerEvents="box-none" style={styles.footer} onLayout={(event) => {
            // The gradient begins above the buttons. Content may scroll through the gradient.
            setFooter(event.nativeEvent.layout.height - space.fade + space.lg);
          }}>
            <ScreenFooter label={action} current={step} reached={reached} skipped={skipCrop ? 4 : undefined}
              disabled={disabled} busy={busy} onNext={onNext} onStep={(next) => go(next as Step)} bottom={safe.bottom} />
          </View>
        )}
      </View>
    </KeyboardAvoidingView>
  );
}

export function ScrollFrame({ bottom, children }: { bottom: number; children: ReactNode }) {
  // Reserve footer space on the wrapper. Web ScrollView forwards margins to two DOM nodes.
  return <View style={[styles.flex, { marginBottom: Math.max(0, bottom - space.lg) }]}>{children}</View>;
}

export function ScreenScroll({ inset, style, contentContainerStyle, scrollRef, ...props }: ScrollViewProps & {
  inset: Clearance;
  scrollRef?: Ref<ComponentRef<typeof ScrollView>>;
}) {
  return (
    <ScrollFrame bottom={inset.bottom}>
      <ScrollView {...props} ref={scrollRef} style={[styles.flex, style]} showsVerticalScrollIndicator={false} keyboardShouldPersistTaps="handled"
        contentContainerStyle={[styles.scroll, { paddingTop: inset.top, paddingBottom: space.lg }, contentContainerStyle]} />
    </ScrollFrame>
  );
}

const styles = StyleSheet.create({
  viewport: { flex: 1, backgroundColor: colors.forest950 },
  flex: { flex: 1 },
  frame: { flex: 1, width: '100%', maxWidth: size.maxContent, alignSelf: 'center', overflow: 'hidden', backgroundColor: colors.forest950 },
  scroll: { paddingHorizontal: space.gutter, gap: space.md },
  header: { position: 'absolute', top: 0, start: 0, end: 0 },
  footer: { position: 'absolute', bottom: 0, start: 0, end: 0 },
});
