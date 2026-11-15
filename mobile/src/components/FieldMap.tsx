import { Image } from 'expo-image';
import { LinearGradient } from 'expo-linear-gradient';
import { useMemo, useState, type ReactNode } from 'react';
import { Pressable, StyleSheet, View } from 'react-native';
import { GestureDetector, useCompetingGestures, usePanGesture, useTapGesture } from 'react-native-gesture-handler';
import Svg, { Line, Polygon, Polyline } from 'react-native-svg';
import type { Point } from '@/features/area/model';
import { strings } from '@/i18n/strings';
import type { Picture } from '@/theme/images';
import { colors, radius, size, space, wireframe } from '@/theme/tokens';
import { IconButton, Label, Surface } from './primitives';

export function Backdrop({ image, kind }: { image: Picture; kind: 'country' | 'field' | 'map' | 'parcel' }) {
  const field = kind === 'field';
  return (
    <View pointerEvents="none" style={[StyleSheet.absoluteFill, kind === 'parcel' && styles.parcelBackdrop]}>
      <Image source={image} contentFit="cover" style={StyleSheet.absoluteFill} />
      <View style={[StyleSheet.absoluteFill, field && styles.fieldTint, (kind === 'map' || kind === 'parcel') && styles.mapTint]} />
      {!field && <LinearGradient colors={kind === 'country' ? colors.heroScrim : kind === 'map' ? colors.mapScrim : colors.parcelScrim}
        style={StyleSheet.absoluteFill} locations={[0, .5, 1]} />}
    </View>
  );
}

export function FieldOverlay({ points, closed, fit = false }: { points: readonly Point[]; closed: boolean; fit?: boolean }) {
  if (points.length < 2) return null;
  const positions = points.map((point) => point.x + ',' + point.y).join(' ');
  const center = points.reduce((sum, point) => ({ x: sum.x + point.x / points.length, y: sum.y + point.y / points.length }), { x: 0, y: 0 });
  let viewBox = [0, 0, wireframe.bounds, wireframe.bounds].join(' ');
  if (fit) {
    const x = points.map((point) => point.x);
    const y = points.map((point) => point.y);
    const pad = wireframe.padding;
    const minX = Math.min(...x) - pad;
    const minY = Math.min(...y) - pad;
    const width = Math.max(...x) + pad - minX;
    const height = Math.max(...y) + pad - minY;
    const edge = Math.max(width, height * .9);
    viewBox = [minX - (edge - width) / 2, minY - (edge - height) / 2, edge, edge].join(' ');
  }
  return (
    <View style={StyleSheet.absoluteFill} pointerEvents="none">
      <Svg width="100%" height="100%" viewBox={viewBox} preserveAspectRatio={fit ? 'xMidYMid meet' : 'none'}>
        {closed ? <>
          <Polygon points={positions} fill={colors.parcel} stroke={colors.accent} strokeWidth={wireframe.stroke} strokeLinejoin="round" vectorEffect="non-scaling-stroke" />
          {points.map((point, index) => <Line key={index} x1={center.x} y1={center.y} x2={point.x} y2={point.y}
            stroke={colors.accent} strokeWidth={wireframe.fanStroke} strokeOpacity={wireframe.fanOpacity} vectorEffect="non-scaling-stroke" />)}
        </> : <Polyline points={positions} fill="none" stroke={colors.accent} strokeWidth={wireframe.stroke}
          strokeDasharray={wireframe.dash} vectorEffect="non-scaling-stroke" />}
      </Svg>
    </View>
  );
}

export function FieldMap({ image, points, closed, canClose, invalidBoundary, onPoint, onClose, onReset, top, bottom, search, metrics, onRefresh }: {
  image: Picture; points: readonly Point[]; closed: boolean; canClose: boolean; invalidBoundary?: boolean; onPoint: (point: Point) => void;
  onClose: () => void; onReset: () => void; top: number; bottom: number; search: ReactNode; metrics: ReactNode; onRefresh?: () => void;
}) {
  const [layout, setLayout] = useState({ width: 0, height: 0 });
  const grid = useMemo(() => ({
    columns: Array.from({ length: Math.floor(layout.width / size.grid) }, (_, i) => (i + 1) * size.grid),
    rows: Array.from({ length: Math.floor(layout.height / size.grid) }, (_, i) => (i + 1) * size.grid),
  }), [layout]);
  const refreshGesture = usePanGesture({
    runOnJS: true,
    activeOffsetY: space.fade,
    onDeactivate: (event) => { if (event.translationY >= size.primary) onRefresh?.(); },
  });

  const tapGesture = useTapGesture({
    runOnJS: true,
    onActivate: ({ x, y }) => {
      if (!layout.width || !layout.height || !Number.isFinite(x) || !Number.isFinite(y)) return;
      onPoint({ x: normalize(x, layout.width), y: normalize(y, layout.height) });
    },
  });
  const gestures = useCompetingGestures(refreshGesture, tapGesture);

  return (
    <View style={styles.flex} onLayout={(event) => setLayout(event.nativeEvent.layout)}>
      <Backdrop kind="map" image={image} />
      <View pointerEvents="none" style={StyleSheet.absoluteFill}>
        {grid.columns.map((left) => <View key={left} style={[styles.gridColumn, { left }]} />)}
        {grid.rows.map((top) => <View key={top} style={[styles.gridRow, { top }]} />)}
      </View>
      <View style={StyleSheet.absoluteFill}>
        <GestureDetector gesture={gestures} touchAction="none">
          <View testID="field-canvas" accessible accessibilityLabel={strings.map} style={styles.flex} />
        </GestureDetector>
      </View>
      <FieldOverlay points={points} closed={closed} />
      {points.map((point, index) => {
        const first = canClose && index === 0;
        const location = { left: ((point.x / 100) * layout.width) - size.touch / 2, top: ((point.y / 100) * layout.height) - size.touch / 2 };
        return first ? (
          <Pressable key={index} accessibilityRole="button" accessibilityLabel={strings.closeBoundary} onPress={onClose}
            style={[styles.vertexHit, location]}><View style={[styles.vertex, styles.firstVertex]} /></Pressable>
        ) : <View key={index} pointerEvents="none" style={[styles.vertexHit, location]}><View style={styles.vertex} /></View>;
      })}
      <View pointerEvents="box-none" style={[styles.mapLayout, { paddingTop: top, paddingBottom: bottom }]}>
        <View style={styles.searchWrap} pointerEvents="box-none">{search}</View>
        <View style={[styles.mapSpacer, layout.height >= size.roomyCanvas && styles.roomyMapSpacer]} pointerEvents="box-none">
          {(!points.length || invalidBoundary) && <View style={styles.hintWrap} pointerEvents="none">
            <Surface kind={invalidBoundary ? 'danger' : 'glass'} rounding={radius.tile} style={styles.hint}>
              <Label variant="detail" accessibilityLiveRegion="polite">{invalidBoundary ? strings.invalidBoundary : strings.drawHint}</Label>
            </Surface>
          </View>}
          <View style={styles.controls} pointerEvents="box-none">
            <IconButton label={strings.draw} name="layers" tone={closed ? 'glass' : 'accent'} onPress={closed ? onReset : () => undefined} />
            {canClose && <IconButton label={strings.closeBoundary} name="check" tone="dark" color={colors.accent} onPress={onClose} />}
            <IconButton label={strings.reset} name="trash" color={colors.danger} onPress={onReset} />
          </View>
        </View>
        {metrics}
      </View>
    </View>
  );
}

function normalize(offset: number, span: number) {
  return Math.min(wireframe.bounds, Math.max(0, offset / span * wireframe.bounds));
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  fieldTint: { backgroundColor: colors.imageTint },
  mapTint: { backgroundColor: colors.aerialTint },
  parcelBackdrop: { height: size.planHero, bottom: undefined },
  gridColumn: { position: 'absolute', width: size.hairline, top: 0, bottom: 0, backgroundColor: colors.grid },
  gridRow: { position: 'absolute', height: size.hairline, start: 0, end: 0, backgroundColor: colors.grid },
  vertexHit: { position: 'absolute', width: size.touch, height: size.touch, alignItems: 'center', justifyContent: 'center' },
  vertex: { width: size.vertex, height: size.vertex, borderRadius: radius.pill, borderWidth: size.outline, borderColor: colors.forest950, backgroundColor: colors.accent,
    shadowColor: colors.accent, shadowOpacity: .9, shadowRadius: space.snug },
  firstVertex: { width: size.activeVertex, height: size.activeVertex },
  mapLayout: { ...StyleSheet.absoluteFill, paddingHorizontal: space.gutter },
  searchWrap: { zIndex: 2 },
  mapSpacer: { flex: 1, flexDirection: 'row', alignItems: 'center', gap: space.md, justifyContent: 'flex-end' },
  roomyMapSpacer: { paddingTop: space.xxl * 2 },
  controls: { gap: space.md },
  hintWrap: { flex: 1 },
  hint: { paddingHorizontal: space.lg, paddingVertical: space.md },
});
