import { useEffect, useRef, useState, type ComponentRef } from 'react';
import {
  ActivityIndicator,
  Keyboard,
  Platform,
  Pressable,
  ScrollView,
  Share,
  StyleSheet,
  TextInput,
  View,
  useWindowDimensions,
} from 'react-native';
import { Icon } from '@/components/Icon';
import { Chip, ErrorCard, Label, Surface } from '@/components/primitives';
import { colors, radius, size, space } from '@/theme/tokens';
import { typography } from '@/theme/typography';
import {
  CRESCO_DEFAULT_MODEL,
  CRESCO_STARTER_PROMPTS,
  type CrescoChatMessage,
} from '../model';
import { MarkdownContent } from './MarkdownContent';

async function copyResponseText(text: string): Promise<boolean> {
  try {
    if (
      Platform.OS === 'web' &&
      typeof navigator !== 'undefined' &&
      navigator.clipboard &&
      typeof navigator.clipboard.writeText === 'function'
    ) {
      await navigator.clipboard.writeText(text);
      return true;
    }
    await Share.share({ message: text });
    return true;
  } catch {
    return false;
  }
}

export function ChatView({
  farmLabel,
  model,
  messages,
  sending,
  clearing,
  disconnecting,
  errorText,
  justConnected,
  onSend,
  onClear,
  onDisconnect,
  onDismissError,
  onOpenFarms,
}: {
  farmLabel: string;
  model: string;
  messages: CrescoChatMessage[];
  sending: boolean;
  clearing: boolean;
  disconnecting: boolean;
  errorText: string | null;
  justConnected: boolean;
  onSend: (text: string) => void;
  onClear: () => void;
  onDisconnect: () => void;
  onDismissError: () => void;
  onOpenFarms: () => void;
}) {
  const [draft, setDraft] = useState('');
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [keyboardOpen, setKeyboardOpen] = useState(false);
  const scrollRef = useRef<ComponentRef<typeof ScrollView>>(null);
  const { width, height } = useWindowDimensions();
  const compactHeader = keyboardOpen && height < 760;

  useEffect(() => {
    const showEvent = Platform.OS === 'ios' ? 'keyboardWillShow' : 'keyboardDidShow';
    const hideEvent = Platform.OS === 'ios' ? 'keyboardWillHide' : 'keyboardDidHide';
    const showSub = Keyboard.addListener(showEvent, () => {
      setKeyboardOpen(true);
      setTimeout(() => scrollRef.current?.scrollToEnd({ animated: true }), 80);
    });
    const hideSub = Keyboard.addListener(hideEvent, () => setKeyboardOpen(false));
    return () => {
      showSub.remove();
      hideSub.remove();
    };
  }, []);

  const handleSend = () => {
    const trimmed = draft.trim();
    if (!trimmed || sending) return;
    setDraft('');
    onSend(trimmed);
  };

  const handleCopy = async (id: string, content: string) => {
    const ok = await copyResponseText(content);
    if (ok) {
      setCopiedId(id);
      setTimeout(() => {
        setCopiedId((prev) => (prev === id ? null : prev));
      }, 2000);
    }
  };

  return (
    <View style={styles.root}>
      {/* Active farm & model bar */}
      <Surface kind="glass" style={styles.statusBar}>
        <View style={styles.statusTopRow}>
          <Pressable
            accessibilityRole="button"
            onPress={onOpenFarms}
            style={({ pressed }) => [styles.farmIndicator, pressed && styles.pressed]}
          >
            <View style={styles.liveDot} />
            <Label variant="smallBold" tone="cream" numberOfLines={1} style={styles.flex}>
              Using data from {farmLabel}
            </Label>
          </Pressable>
          <View style={styles.modelBadge}>
            <Label variant="label" tone="accent">{model || CRESCO_DEFAULT_MODEL}</Label>
          </View>
        </View>

        {!compactHeader && (
          <View style={[styles.controlsRow, width < 360 && styles.controlsRowWrap]}>
          <Pressable
            accessibilityRole="button"
            disabled={clearing || sending || messages.length === 0}
            onPress={onClear}
            style={({ pressed }) => [
              styles.controlBtn,
              (clearing || sending || messages.length === 0) && styles.disabled,
              pressed && styles.pressed,
            ]}
          >
            <Icon name="trash" size={14} color={colors.sage} />
            <Label variant="label" tone="sage">{clearing ? 'Clearing...' : 'Clear Chat'}</Label>
          </Pressable>

          <Pressable
            accessibilityRole="button"
            disabled={disconnecting}
            onPress={onDisconnect}
            style={({ pressed }) => [
              styles.controlBtn,
              styles.disconnectBtn,
              disconnecting && styles.disabled,
              pressed && styles.pressed,
            ]}
          >
            <Label variant="label" tone="danger">
              {disconnecting ? 'Disconnecting...' : 'Disconnect / Replace Key'}
            </Label>
          </Pressable>
        </View>
        )}
      </Surface>

      {justConnected && messages.length === 0 && (
        <Surface kind="highlight" rounding={radius.tile} style={styles.successBanner}>
          <Icon name="check" size={16} color={colors.accent} />
          <Label variant="caption" tone="cream" style={styles.flex}>
            Connected to {model || CRESCO_DEFAULT_MODEL}. Ask anything about your farm.
          </Label>
        </Surface>
      )}

      {/* Scrollable transcript + starter chips */}
      <ScrollView
        ref={scrollRef}
        style={styles.messagesScroll}
        contentContainerStyle={styles.messagesContent}
        showsVerticalScrollIndicator={false}
        keyboardShouldPersistTaps="handled"
        keyboardDismissMode="interactive"
        onContentSizeChange={() => scrollRef.current?.scrollToEnd({ animated: true })}
      >
        {messages.length === 0 ? (
          <View style={styles.emptyState}>
            <Surface kind="card" style={styles.welcomeCard}>
              <Label variant="action" tone="cream">Ask Cresco AI</Label>
              <Label variant="caption" tone="sage" style={styles.welcomeText}>
                Cresco combines your field boundary, 3D soil horizons, NASA POWER climate,
                crop knowledge base, and rotation scores. Try a starter prompt below:
              </Label>
            </Surface>

            <View style={styles.chipsWrap}>
              {CRESCO_STARTER_PROMPTS.map((prompt) => (
                <Chip
                  key={prompt}
                  label={prompt}
                  onPress={() => {
                    if (!sending) onSend(prompt);
                  }}
                />
              ))}
            </View>
          </View>
        ) : (
          messages.map((msg) => {
            const isUser = msg.role === 'user';
            return (
              <View
                key={msg.id}
                style={[styles.messageRow, isUser ? styles.userRow : styles.assistantRow]}
              >
                <Surface
                  kind={isUser ? 'highlight' : 'card'}
                  rounding={radius.tile}
                  style={[styles.bubble, isUser ? styles.userBubble : styles.assistantBubble]}
                >
                  <View style={styles.bubbleHeader}>
                    <Label variant="label" tone={isUser ? 'accent' : 'sage'}>
                      {isUser ? 'You' : 'Cresco AI'}
                    </Label>
                    {!isUser && (
                      <Pressable
                        accessibilityRole="button"
                        accessibilityLabel="Copy response"
                        onPress={() => void handleCopy(msg.id, msg.content)}
                        style={({ pressed }) => [styles.copyBtn, pressed && styles.pressed]}
                      >
                        <Label variant="label" tone={copiedId === msg.id ? 'accent' : 'sage'}>
                          {copiedId === msg.id ? 'Copied!' : 'Copy response'}
                        </Label>
                      </Pressable>
                    )}
                  </View>

                  {isUser ? (
                    <Label variant="caption" tone="cream" style={styles.userText}>
                      {msg.content}
                    </Label>
                  ) : (
                    <MarkdownContent content={msg.content} />
                  )}
                </Surface>
              </View>
            );
          })
        )}

        {sending && (
          <View style={[styles.messageRow, styles.assistantRow]}>
            <Surface kind="card" rounding={radius.tile} style={styles.typingBubble}>
              <ActivityIndicator size="small" color={colors.accent} />
              <Label variant="caption" tone="sage">Cresco is analyzing your farm data...</Label>
            </Surface>
          </View>
        )}
      </ScrollView>

      {errorText && (
        <View style={styles.errorWrap}>
          <ErrorCard title="Request failed" hint={errorText} />
          <Pressable
            accessibilityRole="button"
            onPress={onDismissError}
            style={styles.dismissErrorBtn}
          >
            <Label variant="label" tone="sage">Dismiss</Label>
          </Pressable>
        </View>
      )}

      {/* Input bar */}
      <Surface kind="strong" rounding={radius.card} style={styles.inputBar}>
        <TextInput
          value={draft}
          onChangeText={setDraft}
          placeholder="Ask about crops, soil, climate, or rotations..."
          placeholderTextColor={colors.muted}
          multiline
          maxLength={2000}
          editable={!sending}
          returnKeyType="send"
          onFocus={() => setTimeout(() => scrollRef.current?.scrollToEnd({ animated: true }), 100)}
          onSubmitEditing={handleSend}
          accessibilityLabel="Message Cresco AI"
          style={[styles.textInput, Platform.OS === 'web' && webInputStyle]}
        />
        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Send message"
          disabled={sending || !draft.trim()}
          onPress={handleSend}
          style={({ pressed }) => [
            styles.sendBtn,
            (sending || !draft.trim()) && styles.disabled,
            pressed && styles.pressed,
          ]}
        >
          {sending ? (
            <ActivityIndicator size="small" color={colors.forest950} />
          ) : (
            <Icon name="arrow" size={18} color={colors.forest950} />
          )}
        </Pressable>
      </Surface>
    </View>
  );
}

const webInputStyle = { outlineStyle: 'none' } as unknown as object;

const styles = StyleSheet.create({
  root: { flex: 1, gap: space.sm },
  flex: { flex: 1, minWidth: 0 },
  statusBar: { padding: space.md, gap: space.sm },
  statusTopRow: { flexDirection: 'row', alignItems: 'center', gap: space.sm },
  farmIndicator: { flex: 1, flexDirection: 'row', alignItems: 'center', gap: space.sm, minWidth: 0 },
  liveDot: {
    width: size.dot,
    height: size.dot,
    borderRadius: radius.pill,
    backgroundColor: colors.accent,
  },
  modelBadge: {
    paddingHorizontal: space.sm,
    paddingVertical: space.xs,
    borderRadius: radius.pill,
    backgroundColor: colors.highlight,
    borderWidth: size.hairline,
    borderColor: colors.accentBorder,
  },
  controlsRow: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', gap: space.sm },
  controlsRowWrap: { flexWrap: 'wrap' },
  controlBtn: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: space.xs,
    paddingHorizontal: space.md,
    paddingVertical: space.xs,
    borderRadius: radius.pill,
    backgroundColor: colors.chip,
    borderWidth: size.hairline,
    borderColor: colors.border,
  },
  disconnectBtn: {
    backgroundColor: colors.dangerFill,
    borderColor: colors.dangerBorder,
  },
  successBanner: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: space.sm,
    paddingHorizontal: space.md,
    paddingVertical: space.sm,
  },
  messagesScroll: { flex: 1 },
  messagesContent: { gap: space.md, paddingBottom: space.md },
  emptyState: { gap: space.md },
  welcomeCard: { padding: space.lg, gap: space.xs },
  welcomeText: { lineHeight: 20 },
  chipsWrap: { flexDirection: 'row', flexWrap: 'wrap', gap: space.sm },
  messageRow: { width: '100%' },
  userRow: { alignItems: 'flex-end' },
  assistantRow: { alignItems: 'flex-start' },
  bubble: { padding: space.md, gap: space.xs, maxWidth: '94%' },
  userBubble: { minWidth: 120 },
  assistantBubble: { width: '100%' },
  bubbleHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: space.md,
  },
  copyBtn: {
    paddingHorizontal: space.sm,
    paddingVertical: space.xxs,
    borderRadius: radius.pill,
    backgroundColor: colors.chip,
  },
  userText: { lineHeight: 20 },
  typingBubble: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: space.sm,
    paddingHorizontal: space.md,
    paddingVertical: space.sm,
  },
  errorWrap: { gap: space.xs },
  dismissErrorBtn: { alignSelf: 'flex-end', paddingHorizontal: space.sm },
  inputBar: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    gap: space.sm,
    paddingLeft: space.lg,
    paddingRight: space.sm,
    paddingVertical: space.sm,
  },
  textInput: {
    ...typography.caption,
    color: colors.cream,
    flex: 1,
    minHeight: 36,
    maxHeight: 110,
    paddingVertical: space.xs,
  },
  sendBtn: {
    width: 40,
    height: 40,
    borderRadius: radius.pill,
    backgroundColor: colors.accent,
    alignItems: 'center',
    justifyContent: 'center',
  },
  disabled: { opacity: 0.45 },
  pressed: { opacity: 0.78 },
});
