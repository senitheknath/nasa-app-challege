import { router } from 'expo-router';
import { useMemo, useState } from 'react';
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  ScrollView,
  StyleSheet,
  View,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { IconButton, Label, Message } from '@/components/primitives';
import { usePlanner } from '@/state/usePlanner';
import { colors, size, space } from '@/theme/tokens';
import { ChatView } from './components/ChatView';
import { ConnectCard } from './components/ConnectCard';
import {
  useCrescoChat,
  useCrescoClear,
  useCrescoConnect,
  useCrescoDisconnect,
  useCrescoStatus,
} from './hooks';
import {
  CRESCO_DEFAULT_MODEL,
  formatCrescoError,
  type CrescoChatMessage,
  type CrescoInlineFarm,
} from './model';

function makeMessageId(prefix: string): string {
  return `${prefix}-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
}

export default function CrescoScreen() {
  const farmId = usePlanner((s) => s.farmId);
  const farmName = usePlanner((s) => s.farmName);
  const countryId = usePlanner((s) => s.countryId);
  const latitude = usePlanner((s) => s.latitude);
  const longitude = usePlanner((s) => s.longitude);
  const areaHa = usePlanner((s) => s.areaHa);
  const boundary = usePlanner((s) => s.boundary);
  const irrigation = usePlanner((s) => s.irrigation);
  const cropId = usePlanner((s) => s.cropId);
  const sowingDate = usePlanner((s) => s.sowingDate);
  const closed = usePlanner((s) => s.closed);

  const farmScopeKey = farmId !== null ? String(farmId) : 'draft';
  const farmLabel = farmName
    ? farmName
    : closed && countryId
      ? `Current Field (${countryId})`
      : countryId
        ? `Draft Field (${countryId})`
        : 'General Agronomy Mode';

  const inlineFarm: CrescoInlineFarm | undefined = useMemo(() => {
    if (farmId !== null) return undefined;
    if (!countryId && !closed && boundary.length === 0) return undefined;
    return {
      name: farmName || undefined,
      country: countryId || undefined,
      latitude,
      longitude,
      area_ha: areaHa,
      irrigation,
      crop_id: cropId,
      sowing_date: sowingDate,
      boundary: boundary.length >= 3 ? boundary : undefined,
    };
  }, [areaHa, boundary, closed, countryId, cropId, farmId, farmName, irrigation, latitude, longitude, sowingDate]);

  const statusQuery = useCrescoStatus(farmId);
  const connectMutation = useCrescoConnect(farmId);
  const chatMutation = useCrescoChat(farmId);
  const clearMutation = useCrescoClear(farmId);
  const disconnectMutation = useCrescoDisconnect(farmId);

  const [messagesByFarm, setMessagesByFarm] = useState<Record<string, CrescoChatMessage[]>>({});
  const [chatErrorState, setChatErrorState] = useState<{ scope: string; text: string } | null>(null);
  const [justConnected, setJustConnected] = useState(false);

  const connected = statusQuery.data?.connected ?? false;
  const activeModel = statusQuery.data?.model ?? CRESCO_DEFAULT_MODEL;
  const chatError = chatErrorState?.scope === farmScopeKey ? chatErrorState.text : null;

  const messages = useMemo(() => {
    const local = messagesByFarm[farmScopeKey] ?? [];
    const serverHistory = connected ? statusQuery.data?.history : undefined;
    if (serverHistory && serverHistory.length > local.length) {
      return serverHistory.map((item, idx) => ({
        id: `srv-${farmScopeKey}-${idx}`,
        role: item.role,
        content: item.content,
      }));
    }
    return local;
  }, [connected, farmScopeKey, messagesByFarm, statusQuery.data?.history]);

  const handleConnect = async (apiKey: string) => {
    await connectMutation.mutateAsync(apiKey);
    setJustConnected(true);
    setChatErrorState(null);
  };

  const handleSend = (text: string) => {
    const userMsg: CrescoChatMessage = {
      id: makeMessageId('usr'),
      role: 'user',
      content: text,
    };
    setJustConnected(false);
    setChatErrorState(null);
    setMessagesByFarm((prev) => ({
      ...prev,
      [farmScopeKey]: [...messages, userMsg],
    }));

    chatMutation.mutate(
      { message: text, farm: inlineFarm },
      {
        onSuccess: (res) => {
          const assistantMsg: CrescoChatMessage = {
            id: makeMessageId('ast'),
            role: 'assistant',
            content: res.reply,
            provenanceSummary: res.provenance_summary,
            language: res.language,
          };
          setMessagesByFarm((prev) => ({
            ...prev,
            [farmScopeKey]: [...(prev[farmScopeKey] ?? [userMsg]), assistantMsg],
          }));
        },
        onError: (err) => {
          setChatErrorState({ scope: farmScopeKey, text: formatCrescoError(err) });
        },
      },
    );
  };

  const handleClear = () => {
    setChatErrorState(null);
    clearMutation.mutate(undefined, {
      onSuccess: () => {
        setMessagesByFarm((prev) => ({
          ...prev,
          [farmScopeKey]: [],
        }));
      },
      onError: (err) => {
        setChatErrorState({ scope: farmScopeKey, text: formatCrescoError(err) });
      },
    });
  };

  const handleDisconnect = () => {
    setChatErrorState(null);
    setJustConnected(false);
    disconnectMutation.mutate(undefined, {
      onSettled: () => {
        setMessagesByFarm({});
      },
    });
  };

  const handleBack = () => {
    if (router.canGoBack()) router.back();
    else router.replace('/');
  };

  return (
    <SafeAreaView style={styles.safe} edges={['top', 'bottom']}>
      <KeyboardAvoidingView
        behavior={Platform.OS === 'web' ? undefined : 'padding'}
        keyboardVerticalOffset={Platform.OS === 'ios' ? 0 : 8}
        style={styles.flex}
      >
        <View style={styles.frame}>
          <View style={styles.header}>
            <IconButton name="back" label="Back" onPress={handleBack} />
            <View style={styles.headerTitle}>
              <Label variant="title" accessibilityRole="header">Cresco AI</Label>
              <Label variant="caption" tone="sage" numberOfLines={1}>
                {farmLabel}
              </Label>
            </View>
            <IconButton name="user" label="Account and farms" onPress={() => router.push('/login')} />
          </View>

          {statusQuery.isLoading && !statusQuery.data ? (
            <View style={styles.centerState}>
              <ActivityIndicator size="large" color={colors.accent} />
              <Label variant="caption" tone="sage">Checking Cresco AI session...</Label>
            </View>
          ) : statusQuery.isError && !statusQuery.data ? (
            <View style={styles.centerState}>
              <Message
                title="Unable to reach Cresco AI"
                hint={formatCrescoError(statusQuery.error)}
                icon="sprout"
                onRetry={() => void statusQuery.refetch()}
              />
            </View>
          ) : connected ? (
            <View style={styles.chatBody}>
              <ChatView
                farmLabel={farmLabel}
                model={activeModel}
                messages={messages}
                sending={chatMutation.isPending}
                clearing={clearMutation.isPending}
                disconnecting={disconnectMutation.isPending}
                errorText={chatError}
                justConnected={justConnected}
                onSend={handleSend}
                onClear={handleClear}
                onDisconnect={handleDisconnect}
                onDismissError={() => setChatErrorState(null)}
                onOpenFarms={() => router.push('/login')}
              />
            </View>
          ) : (
            <ScrollView
              style={styles.flex}
              contentContainerStyle={styles.connectScroll}
              showsVerticalScrollIndicator={false}
              keyboardShouldPersistTaps="handled"
            >
              <ConnectCard
                farmLabel={farmLabel}
                busy={connectMutation.isPending}
                error={connectMutation.error}
                onConnect={handleConnect}
              />
            </ScrollView>
          )}
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.forest950 },
  flex: { flex: 1 },
  frame: {
    flex: 1,
    width: '100%',
    maxWidth: size.maxContent,
    alignSelf: 'center',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: space.md,
    paddingHorizontal: space.gutter,
    paddingTop: space.sm,
    paddingBottom: space.md,
  },
  headerTitle: { flex: 1, minWidth: 0 },
  centerState: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: space.gutter,
    gap: space.md,
  },
  connectScroll: {
    paddingHorizontal: space.gutter,
    paddingBottom: space.xl,
  },
  chatBody: {
    flex: 1,
    paddingHorizontal: space.gutter,
    paddingBottom: space.md,
  },
});
