import { QueryClientProvider } from '@tanstack/react-query';
import { useFonts } from 'expo-font';
import { Stack, router, type ErrorBoundaryProps } from 'expo-router';
import { StatusBar } from 'expo-status-bar';
import { useEffect, useState } from 'react';
import { StyleSheet, View } from 'react-native';
import { GestureHandlerRootView } from 'react-native-gesture-handler';
import { SafeAreaProvider } from 'react-native-safe-area-context';
import { createQueryClient, connectQueryLifecycle } from '@/api/query';
import { onSessionExpired } from '@/api/session';
import { Message } from '@/components/primitives';
import { strings } from '@/i18n/strings';
import { usePlanner } from '@/state/usePlanner';
import { colors, space } from '@/theme/tokens';
import { fonts } from '@/theme/typography';

export function ErrorBoundary({ retry }: ErrorBoundaryProps) {
  return (
    <View style={styles.recovery}>
      <Message title={strings.failed} hint={strings.failureHint} onRetry={() => void retry()} />
    </View>
  );
}

export default function RootLayout() {
  const [client] = useState(createQueryClient);
  const [loaded, fontError] = useFonts(fonts);
  useEffect(connectQueryLifecycle, []);
  useEffect(() => onSessionExpired(() => {
    void client.cancelQueries();
    client.clear();
    usePlanner.getState().reset();
    router.replace('/login');
  }), [client]);

  if (!loaded && !fontError) return <View style={styles.root} />;
  return (
    <GestureHandlerRootView style={styles.root}>
      <SafeAreaProvider>
        <QueryClientProvider client={client}>
          <StatusBar style="light" />
          <Stack screenOptions={{ headerShown: false, animation: 'none', contentStyle: styles.root }} />
        </QueryClientProvider>
      </SafeAreaProvider>
    </GestureHandlerRootView>
  );
}

const styles = StyleSheet.create({
  root: { flex: 1, backgroundColor: colors.forest950 },
  recovery: { flex: 1, backgroundColor: colors.forest950, padding: space.gutter, justifyContent: 'center' },
});
