import { Image } from 'expo-image';
import { LinearGradient } from 'expo-linear-gradient';
import { useMemo, useRef, useState, type ReactNode } from 'react';
import { Platform, Pressable, StyleSheet, View } from 'react-native';
import {
  GestureDetector,
  useCompetingGestures,
  usePanGesture,
  usePinchGesture,
  useSimultaneousGestures,
  useTapGesture,
} from 'react-native-gesture-handler';
import Svg, { Line, Polygon, Polyline } from 'react-native-svg';
import type { Point } from '@/features/area/model';
import { strings } from '@/i18n/strings';
import type { GeoPoint } from '@/state/usePlanner';
import type { Picture } from '@/theme/images';
import { colors, radius, size, space, wireframe } from '@/theme/tokens';
import { IconButton, Label, Surface } from './primitives';

const TILE_SIZE = 256;
const MIN_ZOOM = 3;
const MAX_ZOOM = 18;

function clampLat(lat: number) {
  return Math.max(-85.05112878, Math.min(85.05112878, lat));
}

function wrapLon(lon: number) {
  return ((((lon + 180) % 360) + 360) % 360) - 180;
}

function latLonToWorld(lat: number, lon: number, zoom: number) {
  const scale = TILE_SIZE * Math.pow(2, zoom);
  const siny = Math.sin((clampLat(lat) * Math.PI) / 180);
  const clampedSin = Math.max(-0.9999, Math.min(0.9999, siny));
  return {
    x: ((wrapLon(lon) + 180) / 360) * scale,
    y: (0.5 - Math.log((1 + clampedSin) / (1 - clampedSin)) / (4 * Math.PI)) * scale,
  };
}

function worldToLatLon(wx: number, wy: number, zoom: number): GeoPoint {
  const scale = TILE_SIZE * Math.pow(2, zoom);
  const lon = (wx / scale) * 360 - 180;
  const n = Math.PI - (2 * Math.PI * wy) / scale;
  const lat = (180 / Math.PI) * Math.atan(0.5 * (Math.exp(n) - Math.exp(-n)));
  return {
    latitude: Number(clampLat(lat).toFixed(6)),
    longitude: Number(wrapLon(lon).toFixed(6)),
  };
}

function latLonToScreen(geo: GeoPoint, center: GeoPoint, zoom: number, width: number, height: number) {
  const centerWorld = latLonToWorld(center.latitude, center.longitude, zoom);
  const ptWorld = latLonToWorld(geo.latitude, geo.longitude, zoom);
  return {
    x: width / 2 + (ptWorld.x - centerWorld.x),
    y: height / 2 + (ptWorld.y - centerWorld.y),
  };
}

function screenToLatLon(sx: number, sy: number, center: GeoPoint, zoom: number, width: number, height: number): GeoPoint {
  const centerWorld = latLonToWorld(center.latitude, center.longitude, zoom);
  return worldToLatLon(centerWorld.x + (sx - width / 2), centerWorld.y + (sy - height / 2), zoom);
}

type MapStyle = 'satellite' | 'hybrid' | 'street';

function tileUrl(style: MapStyle, z: number, x: number, y: number) {
  if (style === 'street') {
    return `https://tile.openstreetmap.org/${z}/${x}/${y}.png`;
  }
  return `https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/${z}/${y}/${x}`;
}

function labelTileUrl(z: number, x: number, y: number) {
  return `https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/${z}/${y}/${x}`;
}

function SlippyTileLayer({
  center,
  zoom,
  width,
  height,
  mapStyle,
}: {
  center: GeoPoint;
  zoom: number;
  width: number;
  height: number;
  mapStyle: MapStyle;
}) {
  const tiles = useMemo(() => {
    if (!width || !height) return [];
    const z = Math.round(Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, zoom)));
    const maxIndex = Math.pow(2, z);
    const centerWorld = latLonToWorld(center.latitude, center.longitude, z);
    const topLeftX = centerWorld.x - width / 2;
    const topLeftY = centerWorld.y - height / 2;
    const minTileX = Math.floor(topLeftX / TILE_SIZE);
    const maxTileX = Math.floor((topLeftX + width) / TILE_SIZE);
    const minTileY = Math.max(0, Math.floor(topLeftY / TILE_SIZE));
    const maxTileY = Math.min(maxIndex - 1, Math.floor((topLeftY + height) / TILE_SIZE));

    const list: { key: string; left: number; top: number; url: string; labelUrl?: string }[] = [];
    for (let tx = minTileX; tx <= maxTileX; tx++) {
      const wrappedX = ((tx % maxIndex) + maxIndex) % maxIndex;
      for (let ty = minTileY; ty <= maxTileY; ty++) {
        list.push({
          key: `${mapStyle}-${z}-${tx}-${ty}`,
          left: tx * TILE_SIZE - topLeftX,
          top: ty * TILE_SIZE - topLeftY,
          url: tileUrl(mapStyle, z, wrappedX, ty),
          labelUrl: mapStyle === 'hybrid' ? labelTileUrl(z, wrappedX, ty) : undefined,
        });
      }
    }
    return list;
  }, [center.latitude, center.longitude, height, mapStyle, width, zoom]);

  return (
    <View pointerEvents="none" style={StyleSheet.absoluteFill}>
      {tiles.map((t) => (
        <View key={t.key} style={{ position: 'absolute', left: t.left, top: t.top, width: TILE_SIZE, height: TILE_SIZE }}>
          <Image source={{ uri: t.url }} style={StyleSheet.absoluteFill} contentFit="fill" transition={120} />
          {t.labelUrl && (
            <Image source={{ uri: t.labelUrl }} style={StyleSheet.absoluteFill} contentFit="fill" />
          )}
        </View>
      ))}
      <View style={[StyleSheet.absoluteFill, styles.tileScrim]} />
    </View>
  );
}

export function Backdrop({ image, kind }: { image: Picture; kind: 'country' | 'field' | 'map' | 'parcel' }) {
  const field = kind === 'field';
  return (
    <View pointerEvents="none" style={[StyleSheet.absoluteFill, kind === 'parcel' && styles.parcelBackdrop]}>
      <Image source={image} contentFit="cover" style={StyleSheet.absoluteFill} />
      <View style={[StyleSheet.absoluteFill, field && styles.fieldTint, (kind === 'map' || kind === 'parcel') && styles.mapTint]} />
      {!field && (
        <LinearGradient
          colors={kind === 'country' ? colors.heroScrim : kind === 'map' ? colors.mapScrim : colors.parcelScrim}
          style={StyleSheet.absoluteFill}
          locations={[0, 0.5, 1]}
        />
      )}
    </View>
  );
}

export function FieldOverlay({ points, closed, fit = false }: { points: readonly Point[]; closed: boolean; fit?: boolean }) {
  if (points.length < 2) return null;
  const positions = points.map((point) => point.x + ',' + point.y).join(' ');
  const center = points.reduce(
    (sum, point) => ({ x: sum.x + point.x / points.length, y: sum.y + point.y / points.length }),
    { x: 0, y: 0 },
  );
  let viewBox = [0, 0, wireframe.bounds, wireframe.bounds].join(' ');
  if (fit) {
    const x = points.map((point) => point.x);
    const y = points.map((point) => point.y);
    const pad = wireframe.padding;
    const minX = Math.min(...x) - pad;
    const minY = Math.min(...y) - pad;
    const width = Math.max(...x) + pad - minX;
    const height = Math.max(...y) + pad - minY;
    const edge = Math.max(width, height * 0.9);
    viewBox = [minX - (edge - width) / 2, minY - (edge - height) / 2, edge, edge].join(' ');
  }
  return (
    <View style={StyleSheet.absoluteFill} pointerEvents="none">
      <Svg width="100%" height="100%" viewBox={viewBox} preserveAspectRatio={fit ? 'xMidYMid meet' : 'none'}>
        {closed ? (
          <>
            <Polygon
              points={positions}
              fill={colors.parcel}
              stroke={colors.accent}
              strokeWidth={wireframe.stroke}
              strokeLinejoin="round"
              vectorEffect="non-scaling-stroke"
            />
            {points.map((point, index) => (
              <Line
                key={index}
                x1={center.x}
                y1={center.y}
                x2={point.x}
                y2={point.y}
                stroke={colors.accent}
                strokeWidth={wireframe.fanStroke}
                strokeOpacity={wireframe.fanOpacity}
                vectorEffect="non-scaling-stroke"
              />
            ))}
          </>
        ) : (
          <Polyline
            points={positions}
            fill="none"
            stroke={colors.accent}
            strokeWidth={wireframe.stroke}
            strokeDasharray={wireframe.dash}
            vectorEffect="non-scaling-stroke"
          />
        )}
      </Svg>
    </View>
  );
}

export function FieldMap({
  image: _image,
  points,
  boundary,
  center,
  zoom = 13,
  closed,
  canClose,
  invalidBoundary,
  onPoint,
  onGeoPoint,
  onCenterChange,
  onClose,
  onReset,
  top,
  bottom,
  search,
  metrics,
  onRefresh,
}: {
  image: Picture;
  points: readonly Point[];
  boundary?: readonly GeoPoint[];
  center?: GeoPoint;
  zoom?: number;
  closed: boolean;
  canClose: boolean;
  invalidBoundary?: boolean;
  onPoint: (point: Point) => void;
  onGeoPoint?: (point: Point, geo: GeoPoint) => void;
  onCenterChange?: (latitude: number, longitude: number, zoom: number) => void;
  onClose: () => void;
  onReset: () => void;
  top: number;
  bottom: number;
  search: ReactNode;
  metrics: ReactNode;
  onRefresh?: () => void;
}) {
  const [layout, setLayout] = useState({ width: 0, height: 0 });
  const [mapStyle, setMapStyle] = useState<MapStyle>('hybrid');
  const [panDelta, setPanDelta] = useState({ x: 0, y: 0 });
  const [pinchScale, setPinchScale] = useState(1);
  const panOriginRef = useRef<GeoPoint | null>(null);
  const lastWheelAtRef = useRef(0);

  const effectiveCenter = useMemo<GeoPoint | undefined>(() => {
    if (!center) return undefined;
    if (panDelta.x === 0 && panDelta.y === 0) return center;
    const world = latLonToWorld(center.latitude, center.longitude, zoom);
    return worldToLatLon(world.x - panDelta.x, world.y - panDelta.y, zoom);
  }, [center, panDelta.x, panDelta.y, zoom]);

  const grid = useMemo(
    () => ({
      columns: Array.from({ length: Math.floor(layout.width / size.grid) }, (_, i) => (i + 1) * size.grid),
      rows: Array.from({ length: Math.floor(layout.height / size.grid) }, (_, i) => (i + 1) * size.grid),
    }),
    [layout],
  );

  const panGesture = usePanGesture({
    runOnJS: true,
    minDistance: 6,
    onActivate: () => {
      if (center) panOriginRef.current = center;
    },
    onUpdate: (event) => {
      if (center) {
        setPanDelta({ x: event.translationX, y: event.translationY });
      }
    },
    onDeactivate: (event) => {
      if (center && panOriginRef.current) {
        const world = latLonToWorld(panOriginRef.current.latitude, panOriginRef.current.longitude, zoom);
        const nextCenter = worldToLatLon(world.x - event.translationX, world.y - event.translationY, zoom);
        setPanDelta({ x: 0, y: 0 });
        panOriginRef.current = null;
        onCenterChange?.(nextCenter.latitude, nextCenter.longitude, zoom);
      } else if (event.translationY >= size.primary) {
        onRefresh?.();
      }
    },
  });

  const tapGesture = useTapGesture({
    runOnJS: true,
    onActivate: ({ x, y }) => {
      if (!layout.width || !layout.height || !Number.isFinite(x) || !Number.isFinite(y)) return;
      const pt = { x: normalize(x, layout.width), y: normalize(y, layout.height) };
      if (effectiveCenter && onGeoPoint) {
        const geo = screenToLatLon(x, y, effectiveCenter, zoom, layout.width, layout.height);
        onGeoPoint(pt, geo);
      } else {
        onPoint(pt);
      }
    },
  });

  const pinchGesture = usePinchGesture({
    runOnJS: true,
    onUpdate: (event) => {
      if (!center || !Number.isFinite(event.scale)) return;
      setPinchScale(Math.max(0.4, Math.min(2.5, event.scale)));
    },
    onDeactivate: (event) => {
      if (center && Number.isFinite(event.scale) && Math.abs(event.scale - 1) > 0.08) {
        const deltaZoom = Math.round(Math.log2(event.scale));
        const nextZoom = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, zoom + deltaZoom));
        if (nextZoom !== zoom) {
          onCenterChange?.(center.latitude, center.longitude, nextZoom);
        }
      }
      setPinchScale(1);
    },
  });

  const gestures = useSimultaneousGestures(pinchGesture, useCompetingGestures(panGesture, tapGesture));

  // Project geo boundary vertices onto the current viewport when available so the polygon stays locked to earth coordinates
  const displayPoints = useMemo<readonly Point[]>(() => {
    if (effectiveCenter && boundary && boundary.length > 0 && layout.width > 0 && layout.height > 0) {
      return boundary.map((geo) => {
        const sc = latLonToScreen(geo, effectiveCenter, zoom, layout.width, layout.height);
        return {
          x: (sc.x / layout.width) * wireframe.bounds,
          y: (sc.y / layout.height) * wireframe.bounds,
        };
      });
    }
    return points;
  }, [boundary, effectiveCenter, layout.height, layout.width, points, zoom]);

  const cycleMapStyle = () => {
    setMapStyle((prev) => (prev === 'hybrid' ? 'satellite' : prev === 'satellite' ? 'street' : 'hybrid'));
  };

  const stepZoom = (delta: number) => {
    if (!center) return;
    const nextZoom = Math.max(MIN_ZOOM, Math.min(MAX_ZOOM, zoom + delta));
    if (nextZoom !== zoom) onCenterChange?.(center.latitude, center.longitude, nextZoom);
  };

  const webWheelProps = Platform.OS === 'web'
    ? {
        onWheel: (event: { nativeEvent?: { deltaY?: number }; deltaY?: number }) => {
          if (!center) return;
          const now = Date.now();
          if (now - lastWheelAtRef.current < 160) return;
          const dy = event.nativeEvent?.deltaY ?? event.deltaY ?? 0;
          if (Math.abs(dy) < 2) return;
          lastWheelAtRef.current = now;
          stepZoom(dy < 0 ? 1 : -1);
        },
      }
    : {};

  return (
    <View style={styles.flex} onLayout={(event) => setLayout(event.nativeEvent.layout)} {...webWheelProps}>
      <View pointerEvents="none" style={[StyleSheet.absoluteFill, styles.blackBg]} />
      {effectiveCenter && layout.width > 0 && layout.height > 0 && (
        <View
          pointerEvents="none"
          style={[StyleSheet.absoluteFill, pinchScale !== 1 && { transform: [{ scale: pinchScale }] }]}
        >
          <SlippyTileLayer center={effectiveCenter} zoom={zoom} width={layout.width} height={layout.height} mapStyle={mapStyle} />
        </View>
      )}
      <View pointerEvents="none" style={StyleSheet.absoluteFill}>
        {grid.columns.map((left) => (
          <View key={left} style={[styles.gridColumn, { left }]} />
        ))}
        {grid.rows.map((topPos) => (
          <View key={topPos} style={[styles.gridRow, { top: topPos }]} />
        ))}
      </View>
      <View style={StyleSheet.absoluteFill}>
        <GestureDetector gesture={gestures} touchAction="none">
          <View testID="field-canvas" accessible accessibilityLabel={strings.map} style={styles.flex} />
        </GestureDetector>
      </View>
      <FieldOverlay points={displayPoints} closed={closed} />
      {displayPoints.map((point, index) => {
        const first = canClose && index === 0;
        const location = {
          left: (point.x / 100) * layout.width - size.touch / 2,
          top: (point.y / 100) * layout.height - size.touch / 2,
        };
        return first ? (
          <Pressable
            key={index}
            accessibilityRole="button"
            accessibilityLabel={strings.closeBoundary}
            onPress={onClose}
            style={[styles.vertexHit, location]}
          >
            <View style={[styles.vertex, styles.firstVertex]} />
          </Pressable>
        ) : (
          <View key={index} pointerEvents="none" style={[styles.vertexHit, location]}>
            <View style={styles.vertex} />
          </View>
        );
      })}
      <View pointerEvents="box-none" style={[styles.mapLayout, { paddingTop: top, paddingBottom: bottom }]}>
        <View style={styles.searchWrap} pointerEvents="box-none">
          {search}
        </View>
        <View style={[styles.mapSpacer, layout.height >= size.roomyCanvas && styles.roomyMapSpacer]} pointerEvents="box-none">
          {(!points.length || invalidBoundary) && (
            <View style={styles.hintWrap} pointerEvents="none">
              <Surface kind={invalidBoundary ? 'danger' : 'glass'} rounding={radius.tile} style={styles.hint}>
                <Label variant="detail" accessibilityLiveRegion="polite">
                  {invalidBoundary
                    ? strings.invalidBoundary
                    : 'Drag to pan · Tap corners to draw parcel'}
                </Label>
              </Surface>
            </View>
          )}
          <View style={styles.controls} pointerEvents="box-none">
            {center && (
              <>
                <IconButton label="Zoom in" name="plus" tone="glass" onPress={() => stepZoom(1)} />
                <Pressable accessibilityRole="button" accessibilityLabel="Zoom out" onPress={() => stepZoom(-1)} style={styles.zoomOutBtn}>
                  <Label variant="button" tone="cream">−</Label>
                </Pressable>
              </>
            )}
            <IconButton label={`Map layer: ${mapStyle}`} name="layers" tone="glass" onPress={cycleMapStyle} />
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
  return Math.min(wireframe.bounds, Math.max(0, (offset / span) * wireframe.bounds));
}

const styles = StyleSheet.create({
  flex: { flex: 1 },
  blackBg: { backgroundColor: '#000000' },
  fieldTint: { backgroundColor: colors.imageTint },
  mapTint: { backgroundColor: colors.aerialTint },
  tileScrim: { backgroundColor: 'rgba(18,23,12,.14)' },
  parcelBackdrop: { height: size.planHero, bottom: undefined },
  gridColumn: { position: 'absolute', width: size.hairline, top: 0, bottom: 0, backgroundColor: colors.grid },
  gridRow: { position: 'absolute', height: size.hairline, start: 0, end: 0, backgroundColor: colors.grid },
  vertexHit: { position: 'absolute', width: size.touch, height: size.touch, alignItems: 'center', justifyContent: 'center' },
  vertex: {
    width: size.vertex,
    height: size.vertex,
    borderRadius: radius.pill,
    borderWidth: size.outline,
    borderColor: colors.forest950,
    backgroundColor: colors.accent,
    shadowColor: colors.accent,
    shadowOpacity: 0.9,
    shadowRadius: space.snug,
  },
  firstVertex: { width: size.activeVertex, height: size.activeVertex },
  mapLayout: { ...StyleSheet.absoluteFill, paddingHorizontal: space.gutter },
  searchWrap: { zIndex: 2 },
  mapSpacer: { flex: 1, flexDirection: 'row', alignItems: 'center', gap: space.md, justifyContent: 'flex-end' },
  roomyMapSpacer: { paddingTop: space.xxl * 2 },
  controls: { gap: space.sm, alignItems: 'center' },
  zoomOutBtn: {
    width: size.touch,
    height: size.touch,
    borderRadius: radius.pill,
    borderWidth: size.hairline,
    borderColor: colors.border,
    backgroundColor: colors.iconGlass,
    alignItems: 'center',
    justifyContent: 'center',
  },
  hintWrap: { flex: 1 },
  hint: { paddingHorizontal: space.lg, paddingVertical: space.md },
});
