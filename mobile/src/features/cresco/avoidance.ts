import { useCallback, useEffect, useId, useRef, type ComponentRef } from 'react';
import type { View } from 'react-native';
import { create } from 'zustand';

export type AvoidanceKind = 'button' | 'text' | 'chrome';

export type AvoidanceRect = {
  x: number;
  y: number;
  width: number;
  height: number;
  padding?: number;
  kind?: AvoidanceKind;
};

export type BubblePoint = { x: number; y: number };

export type BubbleBounds = {
  minX: number;
  maxX: number;
  minY: number;
  maxY: number;
};

type AvoidanceState = {
  zones: Record<string, AvoidanceRect>;
  registerZone: (id: string, rect: AvoidanceRect) => void;
  unregisterZone: (id: string) => void;
};

const DEFAULT_PADDING = 10;

function sameRect(a: AvoidanceRect | undefined, b: AvoidanceRect): boolean {
  if (!a) return false;
  return (
    Math.abs(a.x - b.x) < 1 &&
    Math.abs(a.y - b.y) < 1 &&
    Math.abs(a.width - b.width) < 1 &&
    Math.abs(a.height - b.height) < 1 &&
    (a.padding ?? DEFAULT_PADDING) === (b.padding ?? DEFAULT_PADDING) &&
    a.kind === b.kind
  );
}

export const useAvoidanceStore = create<AvoidanceState>((set) => ({
  zones: {},
  registerZone: (id, rect) =>
    set((state) => {
      if (rect.width <= 0 || rect.height <= 0) return state;
      if (sameRect(state.zones[id], rect)) return state;
      return { zones: { ...state.zones, [id]: rect } };
    }),
  unregisterZone: (id) =>
    set((state) => {
      if (!(id in state.zones)) return state;
      const next = { ...state.zones };
      delete next[id];
      return { zones: next };
    }),
}));

/**
 * Registers a View's window-space bounding box so the floating Cresco bubble
 * intentionally moves away from buttons, headers, footers, and key text blocks.
 */
export function useAvoidanceZone(
  customId?: string,
  enabled = true,
  kind: AvoidanceKind = 'button',
  padding = DEFAULT_PADDING,
) {
  const autoId = useId();
  const id = customId ?? autoId;
  const nodeRef = useRef<ComponentRef<typeof View> | null>(null);
  const registerZone = useAvoidanceStore((s) => s.registerZone);
  const unregisterZone = useAvoidanceStore((s) => s.unregisterZone);

  const setRef = useCallback((node: ComponentRef<typeof View> | null) => {
    nodeRef.current = node;
  }, []);

  const measure = useCallback(() => {
    if (!enabled) return;
    const node = nodeRef.current;
    if (!node || typeof node.measureInWindow !== 'function') return;
    node.measureInWindow((x, y, width, height) => {
      if (
        Number.isFinite(x) &&
        Number.isFinite(y) &&
        Number.isFinite(width) &&
        Number.isFinite(height) &&
        width > 0 &&
        height > 0
      ) {
        registerZone(id, { x, y, width, height, padding, kind });
      }
    });
  }, [enabled, id, kind, padding, registerZone]);

  useEffect(() => {
    if (!enabled) {
      unregisterZone(id);
      return;
    }
    const timer = setTimeout(measure, 32);
    return () => {
      clearTimeout(timer);
      unregisterZone(id);
    };
  }, [enabled, id, measure, unregisterZone]);

  return [setRef, measure] as const;
}

function clamp(value: number, min: number, max: number): number {
  if (max <= min) return min;
  return Math.min(Math.max(value, min), max);
}

function expandRect(z: AvoidanceRect): { left: number; top: number; right: number; bottom: number } {
  const pad = z.padding ?? DEFAULT_PADDING;
  return {
    left: z.x - pad,
    top: z.y - pad,
    right: z.x + z.width + pad,
    bottom: z.y + z.height + pad,
  };
}

export function overlapArea(
  point: BubblePoint,
  bubbleSize: number,
  zones: readonly AvoidanceRect[],
): number {
  const bLeft = point.x;
  const bTop = point.y;
  const bRight = point.x + bubbleSize;
  const bBottom = point.y + bubbleSize;
  let total = 0;

  for (const zone of zones) {
    const r = expandRect(zone);
    const ix = Math.max(0, Math.min(bRight, r.right) - Math.max(bLeft, r.left));
    const iy = Math.max(0, Math.min(bBottom, r.bottom) - Math.max(bTop, r.top));
    total += ix * iy;
  }
  return total;
}

function distanceSq(a: BubblePoint, b: BubblePoint): number {
  const dx = a.x - b.x;
  const dy = a.y - b.y;
  return dx * dx + dy * dy;
}

/**
 * Computes the nearest edge-snapped (or free) bubble position within `bounds`
 * that does not overlap any registered button/text avoidance zone.
 */
export function findClearBubblePosition(
  target: BubblePoint,
  bubbleSize: number,
  bounds: BubbleBounds,
  zonesMap: Record<string, AvoidanceRect>,
  snapToEdge = true,
): BubblePoint {
  const zones = Object.values(zonesMap);
  const clampedY = clamp(target.y, bounds.minY, bounds.maxY);
  const clampedX = clamp(target.x, bounds.minX, bounds.maxX);

  const midX = (bounds.minX + bounds.maxX) / 2;
  const primaryEdgeX = clampedX <= midX ? bounds.minX : bounds.maxX;
  const secondaryEdgeX = primaryEdgeX === bounds.minX ? bounds.maxX : bounds.minX;
  const initialPoint: BubblePoint = {
    x: snapToEdge ? primaryEdgeX : clampedX,
    y: clampedY,
  };

  if (zones.length === 0 || overlapArea(initialPoint, bubbleSize, zones) === 0) {
    return initialPoint;
  }

  const candidateYs = new Set<number>([clampedY, bounds.minY, bounds.maxY]);
  for (const z of zones) {
    const r = expandRect(z);
    candidateYs.add(clamp(r.top - bubbleSize - 2, bounds.minY, bounds.maxY));
    candidateYs.add(clamp(r.bottom + 2, bounds.minY, bounds.maxY));
  }

  const spanY = Math.max(1, bounds.maxY - bounds.minY);
  const stepY = Math.max(24, Math.floor(bubbleSize * 0.6));
  for (let y = bounds.minY; y <= bounds.maxY; y += stepY) {
    candidateYs.add(y);
  }
  if (spanY > 0) candidateYs.add(bounds.maxY);

  const candidateXs = snapToEdge
    ? [primaryEdgeX, secondaryEdgeX]
    : [clampedX, primaryEdgeX, secondaryEdgeX, (bounds.minX + bounds.maxX) / 2];

  const edgeCandidates: BubblePoint[] = [];
  for (const x of candidateXs) {
    for (const y of candidateYs) {
      edgeCandidates.push({ x: clamp(x, bounds.minX, bounds.maxX), y });
    }
  }

  let bestClear: BubblePoint | null = null;
  let bestClearScore = Number.POSITIVE_INFINITY;

  let bestFallback = initialPoint;
  let bestFallbackOverlap = overlapArea(initialPoint, bubbleSize, zones);
  let bestFallbackDist = 0;

  const evaluate = (pts: readonly BubblePoint[]) => {
    for (const pt of pts) {
      const overlap = overlapArea(pt, bubbleSize, zones);
      const sidePenalty = pt.x === secondaryEdgeX ? 400 : 0;
      const dist = distanceSq(pt, initialPoint) + sidePenalty;

      if (overlap === 0) {
        if (dist < bestClearScore) {
          bestClearScore = dist;
          bestClear = pt;
        }
      } else if (
        overlap < bestFallbackOverlap ||
        (overlap === bestFallbackOverlap && dist < bestFallbackDist)
      ) {
        bestFallbackOverlap = overlap;
        bestFallbackDist = dist;
        bestFallback = pt;
      }
    }
  };

  evaluate(edgeCandidates);

  // Only sample interior columns if both edges are completely blocked at every height.
  if (!bestClear) {
    const interiorCandidates: BubblePoint[] = [];
    const midCols = 4;
    for (let i = 1; i < midCols; i += 1) {
      const x = bounds.minX + ((bounds.maxX - bounds.minX) * i) / midCols;
      for (const y of candidateYs) {
        interiorCandidates.push({ x, y });
      }
    }
    evaluate(interiorCandidates);
  }

  return bestClear ?? bestFallback;
}
