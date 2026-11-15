import { useMemo, useState } from 'react';
import { Platform, Pressable, StyleSheet, View } from 'react-native';
import { GestureDetector, usePanGesture } from 'react-native-gesture-handler';
import Svg, { Circle, Defs, Line, LinearGradient, Polygon, Polyline, Stop } from 'react-native-svg';
import { Label, Surface } from '@/components/primitives';
import { colors, radius, space } from '@/theme/tokens';
import { formatNumber } from '@/utils/format';
import type { Slab3DDto, TerrainVertexDto } from './model';

type Camera = { azimuth: number; tilt: number };

const PRESETS: readonly { id: string; label: string; camera: Camera }[] = [
  { id: 'iso', label: 'Isometric', camera: { azimuth: -38, tilt: 32 } },
  { id: 'top', label: 'Top-Down', camera: { azimuth: 0, tilt: 82 } },
  { id: 'cutaway', label: 'Soil Cutaway', camera: { azimuth: -48, tilt: 16 } },
];

type Vec3 = { x: number; y: number; z: number };
type Projected = { sx: number; sy: number; depth: number };

function project3D(p: Vec3, cam: Camera, width: number, height: number): Projected {
  const az = (cam.azimuth * Math.PI) / 180;
  const ti = (cam.tilt * Math.PI) / 180;

  // Rotate around Z (azimuth)
  const cosA = Math.cos(az);
  const sinA = Math.sin(az);
  const xr = p.x * cosA - p.y * sinA;
  const yr = p.x * sinA + p.y * cosA;
  const zr = p.z;

  // Rotate around X (tilt: 0 = side view, 90 = top-down)
  const cosT = Math.cos(ti);
  const sinT = Math.sin(ti);
  const yView = yr * cosT - zr * sinT; // depth into screen
  const zView = yr * sinT + zr * cosT; // vertical on screen

  // Subtle perspective
  const dist = 4.6;
  const scale = dist / Math.max(1.5, dist + yView * 0.65);
  const span = Math.min(width, height) * 0.34;

  return {
    sx: width / 2 + xr * span * scale,
    sy: height * 0.48 - zView * span * scale,
    depth: yView,
  };
}

function pts(list: Projected[]): string {
  return list.map((p) => `${p.sx.toFixed(1)},${p.sy.toFixed(1)}`).join(' ');
}

function moistureToSoilFill(moisturePct: number, idx: number): string {
  // Blend deep forest earth with moisture-driven teal/slate
  const m = Math.max(10, Math.min(55, moisturePct));
  const t = (m - 10) / 45;
  const r = Math.round(52 - t * 24 - idx * 4);
  const g = Math.round(44 + t * 38 - idx * 3);
  const b = Math.round(30 + t * 52 - idx * 2);
  return `rgba(${Math.max(14, r)}, ${Math.max(20, g)}, ${Math.max(18, b)}, 0.88)`;
}

function terrainCellFill(avgNormElev: number, wetness: number): string {
  const e = Math.max(0, Math.min(1, avgNormElev));
  const w = Math.max(0, Math.min(1, wetness));
  const r = Math.round(34 + e * 34 - w * 12);
  const g = Math.round(58 + e * 38 + w * 24);
  const b = Math.round(28 + e * 14 + w * 26);
  return `rgba(${r}, ${g}, ${b}, 0.92)`;
}

export function Slab3DView({ slab }: { slab: Slab3DDto }) {
  const [camera, setCamera] = useState<Camera>(PRESETS[0].camera);
  const [activePreset, setActivePreset] = useState<string>('iso');
  const [dragStart, setDragStart] = useState<Camera>(PRESETS[0].camera);
  const [size, setSize] = useState({ width: 340, height: 290 });

  const pan = usePanGesture({
    runOnJS: true,
    minDistance: 2,
    onActivate: () => {
      setDragStart(camera);
      setActivePreset('');
    },
    onUpdate: (event) => {
      const nextAz = Math.max(-180, Math.min(180, dragStart.azimuth + event.translationX * 0.45));
      const nextTilt = Math.max(8, Math.min(86, dragStart.tilt + event.translationY * 0.35));
      setCamera({ azimuth: nextAz, tilt: nextTilt });
    },
  });

  const scene = useMemo(() => {
    const { width, height } = size;
    const mesh = slab.terrain_3d_mesh;
    const gridN = Math.max(2, mesh.grid_size || 5);

    // Index vertices by (row, col)
    const vertexMap = new Map<string, TerrainVertexDto>();
    let minElev = Infinity;
    let maxElev = -Infinity;
    for (const v of mesh.vertices) {
      vertexMap.set(`${v.row}:${v.col}`, v);
      if (v.elevation_m < minElev) minElev = v.elevation_m;
      if (v.elevation_m > maxElev) maxElev = v.elevation_m;
    }
    if (!Number.isFinite(minElev)) {
      minElev = mesh.elevation_m;
      maxElev = mesh.elevation_m + 1;
    }
    const elevSpan = Math.max(0.5, maxElev - minElev);

    const baseZ = 0.18;
    const reliefAmp = 0.32;

    const getVertexVec = (r: number, c: number): { vec: Vec3; normElev: number; wet: number } => {
      const v = vertexMap.get(`${r}:${c}`);
      const x = (c / (gridN - 1)) * 2 - 1;
      const y = (r / (gridN - 1)) * 2 - 1;
      const normElev = v ? (v.elevation_m - minElev) / elevSpan : 0.3;
      const wet = v?.s1_s2_wetness_idx ?? 0.4;
      return {
        vec: { x, y, z: baseZ + normElev * reliefAmp },
        normElev,
        wet,
      };
    };

    // 1. Soil 3D horizon side walls (4 horizons below baseZ)
    const horizons = slab.soil_3d_horizons.slice(0, 4);
    const totalDepth = 0.82;
    const weights = [0.15, 0.2, 0.28, 0.37];
    let zCursor = baseZ;

    type Face = { points: Projected[]; fill: string; stroke: string; depth: number };
    const soilFaces: Face[] = [];

    horizons.forEach((h, idx) => {
      const thickness = totalDepth * (weights[idx] ?? 0.25);
      const zTop = zCursor;
      const zBot = zCursor - thickness;
      zCursor = zBot;

      const fill = moistureToSoilFill(h.volumetric_moisture_pct, idx);
      const stroke = h.roots_present ? 'rgba(200,243,29,0.28)' : 'rgba(255,255,255,0.12)';

      const cornersTop: Vec3[] = [
        { x: -1, y: -1, z: zTop },
        { x: 1, y: -1, z: zTop },
        { x: 1, y: 1, z: zTop },
        { x: -1, y: 1, z: zTop },
      ];
      const cornersBot: Vec3[] = [
        { x: -1, y: -1, z: zBot },
        { x: 1, y: -1, z: zBot },
        { x: 1, y: 1, z: zBot },
        { x: -1, y: 1, z: zBot },
      ];

      for (let side = 0; side < 4; side++) {
        const next = (side + 1) % 4;
        const p0 = project3D(cornersTop[side], camera, width, height);
        const p1 = project3D(cornersTop[next], camera, width, height);
        const p2 = project3D(cornersBot[next], camera, width, height);
        const p3 = project3D(cornersBot[side], camera, width, height);
        const avgDepth = (p0.depth + p1.depth + p2.depth + p3.depth) / 4;
        soilFaces.push({ points: [p0, p1, p2, p3], fill, stroke, depth: avgDepth });
      }
    });

    // Sort soil faces back-to-front (largest depth first)
    soilFaces.sort((a, b) => b.depth - a.depth);
    // Keep only the 2 front-most faces per horizon layer (or top half by depth) for clean cutaway
    const visibleSoilFaces = soilFaces.slice(Math.floor(soilFaces.length / 2));

    // Active root depth plane (0..1.0m mapped to baseZ .. baseZ - totalDepth)
    const rootFrac = Math.max(0.05, Math.min(1, slab.active_root_depth_m / 1.0));
    const rootZ = baseZ - totalDepth * rootFrac;
    const rootPlane = [
      project3D({ x: -1.02, y: -1.02, z: rootZ }, camera, width, height),
      project3D({ x: 1.02, y: -1.02, z: rootZ }, camera, width, height),
      project3D({ x: 1.02, y: 1.02, z: rootZ }, camera, width, height),
      project3D({ x: -1.02, y: 1.02, z: rootZ }, camera, width, height),
    ];

    // 2. Terrain 5x5 surface quads
    const terrainQuads: Face[] = [];
    for (let r = 0; r < gridN - 1; r++) {
      for (let c = 0; c < gridN - 1; c++) {
        const v00 = getVertexVec(r, c);
        const v10 = getVertexVec(r, c + 1);
        const v11 = getVertexVec(r + 1, c + 1);
        const v01 = getVertexVec(r + 1, c);

        const p00 = project3D(v00.vec, camera, width, height);
        const p10 = project3D(v10.vec, camera, width, height);
        const p11 = project3D(v11.vec, camera, width, height);
        const p01 = project3D(v01.vec, camera, width, height);

        const avgNorm = (v00.normElev + v10.normElev + v11.normElev + v01.normElev) / 4;
        const avgWet = (v00.wet + v10.wet + v11.wet + v01.wet) / 4;
        const avgDepth = (p00.depth + p10.depth + p11.depth + p01.depth) / 4;

        terrainQuads.push({
          points: [p00, p10, p11, p01],
          fill: terrainCellFill(avgNorm, avgWet),
          stroke: 'rgba(255,255,255,0.13)',
          depth: avgDepth,
        });
      }
    }
    terrainQuads.sort((a, b) => b.depth - a.depth);

    // 3. Project boundary_uv onto terrain surface
    const rawUv = mesh.boundary_uv.length >= 3
      ? mesh.boundary_uv
      : [
          { u: 0.2, v: 0.2 },
          { u: 0.8, v: 0.2 },
          { u: 0.8, v: 0.8 },
          { u: 0.2, v: 0.8 },
        ];

    const parcelPoints = rawUv.map((pt) => {
      const u = Math.max(0, Math.min(1, pt.u));
      const v = Math.max(0, Math.min(1, pt.v));
      const col = Math.min(gridN - 1, Math.max(0, Math.round(u * (gridN - 1))));
      const row = Math.min(gridN - 1, Math.max(0, Math.round(v * (gridN - 1))));
      const nearest = getVertexVec(row, col);
      return project3D(
        { x: u * 2 - 1, y: v * 2 - 1, z: nearest.vec.z + 0.03 },
        camera,
        width,
        height,
      );
    });

    // Vertical drop-lines from parcel vertices to root plane for 3D depth cue
    const parcelAnchors = parcelPoints.slice(0, 4).map((pp, idx) => {
      const uv = rawUv[idx];
      const u = Math.max(0, Math.min(1, uv.u));
      const v = Math.max(0, Math.min(1, uv.v));
      const rp = project3D({ x: u * 2 - 1, y: v * 2 - 1, z: rootZ }, camera, width, height);
      return { top: pp, bot: rp };
    });

    return {
      visibleSoilFaces,
      rootPlane,
      terrainQuads,
      parcelPoints,
      parcelAnchors,
    };
  }, [slab, camera, size]);

  const ndvi = slab.canopy_layer.ndvi_current;
  const canopyOpacity = Math.max(0.14, Math.min(0.45, ndvi * 0.52));

  return (
    <Surface kind="card" rounding={radius.card} style={styles.container}>
      <View style={styles.hudTop}>
        <View style={styles.badgeRow}>
          <Surface kind="strong" rounding={radius.pill} style={styles.hudBadge}>
            <Label variant="label" tone="sage">ELEV</Label>
            <Label variant="smallBold" tone="cream">{formatNumber(slab.terrain_3d_mesh.elevation_m, 0)} m</Label>
          </Surface>
          <Surface kind="strong" rounding={radius.pill} style={styles.hudBadge}>
            <Label variant="label" tone="sage">SLOPE</Label>
            <Label variant="smallBold" tone="cream">{formatNumber(slab.terrain_3d_mesh.regional_slope_pct, 1)}%</Label>
          </Surface>
          <Surface kind="strong" rounding={radius.pill} style={styles.hudBadge}>
            <Label variant="label" tone="sage">ROOT</Label>
            <Label variant="smallBold" tone="accent">{formatNumber(slab.active_root_depth_m, 2)} m</Label>
          </Surface>
          <Surface kind="strong" rounding={radius.pill} style={styles.hudBadge}>
            <Label variant="label" tone="sage">NDVI</Label>
            <Label variant="smallBold" tone="accent">{formatNumber(ndvi, 2)}</Label>
          </Surface>
        </View>
      </View>

      <GestureDetector gesture={pan} touchAction={Platform.OS === 'web' ? 'none' : undefined}>
        <View
          style={styles.canvas}
          onLayout={(e) => {
            const { width, height } = e.nativeEvent.layout;
            if (width > 0 && height > 0) setSize({ width, height });
          }}
        >
          <Svg width={size.width} height={size.height}>
            <Defs>
              <LinearGradient id="canopyGlow" x1="0" y1="0" x2="0" y2="1">
                <Stop offset="0" stopColor={colors.accent} stopOpacity={canopyOpacity} />
                <Stop offset="1" stopColor={colors.forest700} stopOpacity={0.25} />
              </LinearGradient>
            </Defs>

            {/* Extruded 3D Soil Horizons */}
            {scene.visibleSoilFaces.map((face, idx) => (
              <Polygon
                key={`soil-${idx}`}
                points={pts(face.points)}
                fill={face.fill}
                stroke={face.stroke}
                strokeWidth={1}
              />
            ))}

            {/* Active Root Depth Plane */}
            <Polygon
              points={pts(scene.rootPlane)}
              fill="rgba(200, 243, 29, 0.08)"
              stroke={colors.accent}
              strokeWidth={1.2}
              strokeDasharray="5 4"
            />

            {/* 5x5 Terrain Mesh */}
            {scene.terrainQuads.map((quad, idx) => (
              <Polygon
                key={`quad-${idx}`}
                points={pts(quad.points)}
                fill={quad.fill}
                stroke={quad.stroke}
                strokeWidth={0.8}
              />
            ))}

            {/* Parcel Vertical Depth Anchors */}
            {scene.parcelAnchors.map((anchor, idx) => (
              <Line
                key={`anchor-${idx}`}
                x1={anchor.top.sx}
                y1={anchor.top.sy}
                x2={anchor.bot.sx}
                y2={anchor.bot.sy}
                stroke={colors.accent}
                strokeOpacity={0.45}
                strokeWidth={1}
                strokeDasharray="3 3"
              />
            ))}

            {/* Projected Parcel Boundary + Canopy NDVI Fill */}
            {scene.parcelPoints.length >= 3 && (
              <>
                <Polygon
                  points={pts(scene.parcelPoints)}
                  fill="url(#canopyGlow)"
                  stroke={colors.accent}
                  strokeWidth={2.2}
                />
                <Polyline
                  points={pts([...scene.parcelPoints, scene.parcelPoints[0]])}
                  fill="none"
                  stroke={colors.cream}
                  strokeOpacity={0.5}
                  strokeWidth={0.8}
                />
                {scene.parcelPoints.map((pt, idx) => (
                  <Circle
                    key={`pv-${idx}`}
                    cx={pt.sx}
                    cy={pt.sy}
                    r={3.2}
                    fill={colors.accent}
                    stroke={colors.forest950}
                    strokeWidth={1.2}
                  />
                ))}
              </>
            )}
          </Svg>
        </View>
      </GestureDetector>

      <View style={styles.controlsBottom}>
        <View style={styles.presetRow}>
          {PRESETS.map((preset) => {
            const active = activePreset === preset.id;
            return (
              <Pressable
                key={preset.id}
                accessibilityRole="button"
                accessibilityState={{ selected: active }}
                onPress={() => {
                  setActivePreset(preset.id);
                  setCamera(preset.camera);
                }}
                style={({ pressed }) => [
                  styles.presetChip,
                  active && styles.presetChipActive,
                  pressed && styles.pressed,
                ]}
              >
                <Label variant="chip" tone={active ? 'forest950' : 'cream'}>
                  {preset.label}
                </Label>
              </Pressable>
            );
          })}
        </View>
        <Label variant="caption" tone="muted">Drag to orbit 3D slab</Label>
      </View>
    </Surface>
  );
}

const styles = StyleSheet.create({
  container: { padding: space.md, gap: space.sm, overflow: 'hidden' },
  hudTop: { gap: space.xs },
  badgeRow: { flexDirection: 'row', flexWrap: 'wrap', gap: space.xs },
  hudBadge: { flexDirection: 'row', alignItems: 'center', gap: space.xs, paddingHorizontal: space.sm, paddingVertical: space.xs },
  canvas: { height: 270, width: '100%' },
  controlsBottom: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: space.sm },
  presetRow: { flexDirection: 'row', flexWrap: 'wrap', gap: space.xs },
  presetChip: {
    paddingHorizontal: space.md,
    paddingVertical: space.xs + 2,
    borderRadius: radius.pill,
    backgroundColor: colors.chip,
    borderWidth: 1,
    borderColor: colors.border,
  },
  presetChipActive: {
    backgroundColor: colors.accent,
    borderColor: colors.accent,
  },
  pressed: { opacity: 0.72 },
});
