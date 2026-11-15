import * as Haptics from 'expo-haptics';
import { router, usePathname } from 'expo-router';
import { useEffect, useMemo, useRef, useState } from 'react';
import {
  Animated,
  PanResponder,
  Platform,
  StyleSheet,
  View,
  useWindowDimensions,
  type GestureResponderHandlers,
} from 'react-native';
import { useSafeAreaInsets } from 'react-native-safe-area-context';
import { Icon } from '@/components/Icon';
import { Label } from '@/components/primitives';
import {
  findClearBubblePosition,
  useAvoidanceStore,
  type BubbleBounds,
  type BubblePoint,
} from '@/features/cresco/avoidance';
import { getCrescoSessionToken } from '@/features/cresco/session';
import { colors, radius } from '@/theme/tokens';
import { useTheme } from '@/theme/useTheme';

const BUBBLE_SIZE = 56;
const EDGE_MARGIN = 14;
const DRAG_THRESHOLD_SQ = 36; // 6px

function clamp(value: number, min: number, max: number): number {
  if (max <= min) return min;
  return Math.min(Math.max(value, min), max);
}

function triggerLightHaptic() {
  if (Platform.OS === 'web') return;
  try {
    void Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
  } catch {
    // Ignore haptic errors on unsupported devices/simulators.
  }
}

export function CrescoBubble() {
  const pathname = usePathname();
  const safe = useSafeAreaInsets();
  const { width, height } = useWindowDimensions();
  const { reducedMotion } = useTheme();
  const zones = useAvoidanceStore((s) => s.zones);

  const hidden = pathname === '/cresco' || pathname === '/login';
  const connected = Boolean(getCrescoSessionToken());

  const bounds: BubbleBounds = useMemo(
    () => ({
      minX: safe.left + EDGE_MARGIN,
      maxX: Math.max(safe.left + EDGE_MARGIN, width - safe.right - BUBBLE_SIZE - EDGE_MARGIN),
      minY: safe.top + 8,
      maxY: Math.max(safe.top + 8, height - safe.bottom - BUBBLE_SIZE - 16),
    }),
    [height, safe.bottom, safe.left, safe.right, safe.top, width],
  );

  const defaultTarget: BubblePoint = useMemo(
    () => ({
      x: bounds.maxX,
      y: clamp(Math.round(height * 0.62), bounds.minY, bounds.maxY),
    }),
    [bounds.maxX, bounds.maxY, bounds.minY, height],
  );

  const preferredRef = useRef<BubblePoint>(defaultTarget);
  const hasUserMovedRef = useRef(false);
  const currentPosRef = useRef<BubblePoint>(defaultTarget);
  const dragStartRef = useRef<BubblePoint>(defaultTarget);
  const isDraggingRef = useRef(false);
  const [dragging, setDragging] = useState(false);

  const [position] = useState(() => new Animated.ValueXY(defaultTarget));
  const [scaleAnim] = useState(() => new Animated.Value(1));
  const [pulseAnim] = useState(() => new Animated.Value(0));

  const useNative = Platform.OS !== 'web';

  // Keep latest bounds and zones accessible inside PanResponder callbacks.
  const latestRef = useRef({ bounds, zones, reducedMotion });
  useEffect(() => {
    latestRef.current = { bounds, zones, reducedMotion };
  }, [bounds, zones, reducedMotion]);

  // Subtle dynamic breathing ring animation.
  useEffect(() => {
    if (hidden || reducedMotion) {
      pulseAnim.setValue(0);
      return;
    }
    const loop = Animated.loop(
      Animated.sequence([
        Animated.timing(pulseAnim, {
          toValue: 1,
          duration: 1800,
          useNativeDriver: useNative,
        }),
        Animated.timing(pulseAnim, {
          toValue: 0,
          duration: 1800,
          useNativeDriver: useNative,
        }),
      ]),
    );
    loop.start();
    return () => loop.stop();
  }, [hidden, pulseAnim, reducedMotion, useNative]);

  // Intentionally move away whenever buttons/texts/chrome change or screen resizes.
  useEffect(() => {
    if (hidden || isDraggingRef.current) return;
    if (!hasUserMovedRef.current) {
      preferredRef.current = defaultTarget;
    }
    const clearPos = findClearBubblePosition(
      preferredRef.current,
      BUBBLE_SIZE,
      bounds,
      zones,
      true,
    );
    const dx = Math.abs(clearPos.x - currentPosRef.current.x);
    const dy = Math.abs(clearPos.y - currentPosRef.current.y);
    if (dx < 1 && dy < 1) return;

    currentPosRef.current = clearPos;
    if (reducedMotion) {
      position.setValue(clearPos);
    } else {
      Animated.spring(position, {
        toValue: clearPos,
        tension: 90,
        friction: 11,
        useNativeDriver: useNative,
      }).start();
    }
  }, [bounds, defaultTarget, hidden, position, reducedMotion, useNative, zones]);

  const [panHandlers, setPanHandlers] = useState<GestureResponderHandlers>({});

  useEffect(() => {
    const responder = PanResponder.create({
      onStartShouldSetPanResponder: () => true,
      onMoveShouldSetPanResponder: () => true,
      onPanResponderGrant: () => {
        isDraggingRef.current = false;
        dragStartRef.current = { ...currentPosRef.current };
        Animated.spring(scaleAnim, {
          toValue: 0.94,
          tension: 180,
          friction: 14,
          useNativeDriver: useNative,
        }).start();
      },
      onPanResponderMove: (_, gesture) => {
        const distSq = gesture.dx * gesture.dx + gesture.dy * gesture.dy;
        if (!isDraggingRef.current && distSq > DRAG_THRESHOLD_SQ) {
          isDraggingRef.current = true;
          setDragging(true);
          triggerLightHaptic();
          Animated.spring(scaleAnim, {
            toValue: 1.08,
            tension: 180,
            friction: 12,
            useNativeDriver: useNative,
          }).start();
        }
        if (!isDraggingRef.current) return;

        const { bounds: b } = latestRef.current;
        const next = {
          x: clamp(dragStartRef.current.x + gesture.dx, b.minX, b.maxX),
          y: clamp(dragStartRef.current.y + gesture.dy, b.minY, b.maxY),
        };
        currentPosRef.current = next;
        position.setValue(next);
      },
      onPanResponderRelease: (_, gesture) => {
        const wasDragging = isDraggingRef.current;
        isDraggingRef.current = false;
        setDragging(false);

        Animated.spring(scaleAnim, {
          toValue: 1,
          tension: 160,
          friction: 12,
          useNativeDriver: useNative,
        }).start();

        if (!wasDragging) {
          triggerLightHaptic();
          router.push('/cresco');
          return;
        }

        const { bounds: b, zones: z, reducedMotion: rm } = latestRef.current;
        const released: BubblePoint = {
          x: clamp(dragStartRef.current.x + gesture.dx, b.minX, b.maxX),
          y: clamp(dragStartRef.current.y + gesture.dy, b.minY, b.maxY),
        };
        hasUserMovedRef.current = true;
        preferredRef.current = released;

        const clearPos = findClearBubblePosition(released, BUBBLE_SIZE, b, z, true);
        currentPosRef.current = clearPos;
        if (rm) {
          position.setValue(clearPos);
        } else {
          Animated.spring(position, {
            toValue: clearPos,
            tension: 95,
            friction: 11,
            useNativeDriver: useNative,
          }).start();
        }
      },
      onPanResponderTerminate: () => {
        isDraggingRef.current = false;
        setDragging(false);
        Animated.spring(scaleAnim, {
          toValue: 1,
          tension: 160,
          friction: 12,
          useNativeDriver: useNative,
        }).start();
      },
    });
    setPanHandlers(responder.panHandlers);
  }, [position, scaleAnim, useNative]);

  if (hidden) return null;

  const pulseScale = pulseAnim.interpolate({
    inputRange: [0, 1],
    outputRange: [1, 1.18],
  });
  const pulseOpacity = pulseAnim.interpolate({
    inputRange: [0, 1],
    outputRange: [0.35, 0],
  });

  return (
    <View pointerEvents="box-none" style={StyleSheet.absoluteFill}>
      <Animated.View
        accessibilityRole="button"
        accessibilityLabel="Open Cresco AI chatbot. Drag to move."
        testID="cresco-floating-bubble"
        {...panHandlers}
        style={[
          styles.bubbleHost,
          {
            transform: [
              { translateX: position.x },
              { translateY: position.y },
              { scale: scaleAnim },
            ],
          },
        ]}
      >
        {!reducedMotion && !dragging && (
          <Animated.View
            pointerEvents="none"
            style={[
              styles.pulseRing,
              {
                opacity: pulseOpacity,
                transform: [{ scale: pulseScale }],
              },
            ]}
          />
        )}
        <View style={[styles.bubble, dragging && styles.bubbleDragging]}>
          <Icon name="bot" size={25} color={colors.accent} />
          <View style={styles.badge}>
            <Label variant="smallBold" tone="forest950" style={styles.badgeText}>
              AI
            </Label>
          </View>
          <View style={[styles.statusDot, connected ? styles.dotLive : styles.dotIdle]} />
        </View>
      </Animated.View>
    </View>
  );
}

const styles = StyleSheet.create({
  bubbleHost: {
    position: 'absolute',
    top: 0,
    left: 0,
    width: BUBBLE_SIZE,
    height: BUBBLE_SIZE,
    zIndex: 90,
  },
  pulseRing: {
    position: 'absolute',
    inset: 0,
    borderRadius: radius.pill,
    borderWidth: 2,
    borderColor: colors.accent,
  },
  bubble: {
    width: BUBBLE_SIZE,
    height: BUBBLE_SIZE,
    borderRadius: radius.pill,
    backgroundColor: colors.forest900,
    borderWidth: 1.5,
    borderColor: colors.accentBorder,
    alignItems: 'center',
    justifyContent: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 6 },
    shadowOpacity: 0.36,
    shadowRadius: 12,
    elevation: 8,
  },
  bubbleDragging: {
    borderColor: colors.accent,
    backgroundColor: colors.forest800,
    shadowOpacity: 0.5,
  },
  badge: {
    position: 'absolute',
    bottom: -2,
    right: -2,
    backgroundColor: colors.accent,
    borderRadius: radius.pill,
    paddingHorizontal: 5,
    paddingVertical: 1,
    borderWidth: 1.5,
    borderColor: colors.forest950,
  },
  badgeText: {
    fontSize: 9,
    lineHeight: 11,
  },
  statusDot: {
    position: 'absolute',
    top: 4,
    right: 4,
    width: 8,
    height: 8,
    borderRadius: 4,
    borderWidth: 1,
    borderColor: colors.forest950,
  },
  dotLive: {
    backgroundColor: colors.accent,
  },
  dotIdle: {
    backgroundColor: colors.sage,
  },
});
