import { useMemo, useState } from 'react';
import { Platform, Pressable, StyleSheet, View } from 'react-native';
import { GestureDetector, usePanGesture } from 'react-native-gesture-handler';
import Svg, { Circle, Defs, Line, LinearGradient, Polygon, Polyline, Stop } from 'react-native-svg';
import { Label, Surface } from '@/components/primitives';
import { colors, radius, space } from '@/theme/tokens';
import { formatNumber } from '@/utils/format';
import type { Slab3DDto, TerrainVertexDto } from './model';

type Camera = { azimuth: number; tilt: number; zoom: number };

const PRESETS: readonly { id: string; label: string; camera: Camera }[] = [
  { id: 'iso', label: 'Isometric', camera: { azimuth: -38, tilt: 32, zoom: 1 } },
  { id: 'top', label: 'Top-Down', camera: { azimuth: 0, tilt: 82, zoom: 1.08 } },
  { id: 'cutaway', label: 'Soil Cutaway', camera: { azimuth: -48, tilt: 16, zoom: 1.05 } },
];

type Vec3 = { x: number; y: number; z: number };
type Projected = { sx: number; sy: number; depth: number };

function project3D(p: Vec3, cam: Camera, width: number, height: number): Projected {
  const az = (cam.azimuth * Math.PI) / 180;
  const ti = (cam.tilt * Math.PI) / 180;

  const cosA = Math.cos(az);
  const sinA = Math.sin(az);
  const xr = p.x * cosA - p.y * sinA;
  const yr = p.x * sinA + p.y * cosA;
  const zr = p.z;

  const cosT = Math.cos(ti);
  const sinT = Math.sin(ti);
  const yView = yr * cosT - zr * sinT;
  const zView = yr * sinT + zr * cosT;

  const dist = 4.6;
  const scale = dist / Math.max(1.5, dist + yView * 0.65);
  const span = Math.min(width, height) * 0.34 * cam.zoom;

  return {
    sx: width / 2 + xr * span * scale,
    sy: height * 0.49 - zView * span * scale,
    depth: yView,
  };
}

function pts(list: Projected[]): string {
  return list.map((p) => `${p.sx.toFixed(1)},${p.sy.toFixed(1)}`).join(' ');
}

function clamp(val: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, val));
}

function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}

function sampleHydroSurface(
  elev5x5: number[][],
  wet5x5: number[][],
  u: number,
  v: number,
  phase: number,
): { elev: number; wet: number } {
  const gx = clamp(u * 4, 0, 4);
  const gy = clamp(v * 4, 0, 4);
  const c0 = Math.min(3, Math.floor(gx));
  const r0 = Math.min(3, Math.floor(gy));
  const tx = gx - c0;
  const ty = gy - r0;
  const sx = tx * tx * (3 - 2 * tx);
  const sy = ty * ty * (3 - 2 * ty);

  const eTop = lerp(elev5x5[r0][c0], elev5x5[r0][c0 + 1], sx);
  const eBot = lerp(elev5x5[r0 + 1][c0], elev5x5[r0 + 1][c0 + 1], sx);
  const baseElev = lerp(eTop, eBot, sy);

  const wTop = lerp(wet5x5[r0][c0], wet5x5[r0][c0 + 1], sx);
  const wBot = lerp(wet5x5[r0 + 1][c0], wet5x5[r0 + 1][c0 + 1], sx);
  const baseWet = lerp(wTop, wBot, sy);

  // 10m dendritic channel carving & micro-relief harmonics
  const cx = (u - 0.5) * 2;
  const cy = (v - 0.5) * 2;
  const meander = 0.22 * Math.sin(cy * 2.8 + phase);
  const chanDist = Math.abs(cx - meander);
  const valleyCarve = -0.16 * Math.exp(-((chanDist / 0.24) ** 2));
  const tribDist = Math.abs(cy - 0.32 * Math.sin(cx * 3.1 - phase) - 0.14);
  const tribMask = clamp((cx - meander + 0.05) * 2.4, 0, 1);
  const tribCarve = -0.08 * Math.exp(-((tribDist / 0.12) ** 2)) * tribMask;
  const microRelief = 0.04 * Math.sin(u * Math.PI * 3.2 + phase) * Math.cos(v * Math.PI * 2.8);

  const wetChannel = Math.max(
    Math.exp(-((chanDist / 0.11) ** 2)),
    0.75 * Math.exp(-((tribDist / 0.09) ** 2)) * tribMask,
  );

  return {
    elev: clamp(baseElev + valleyCarve + tribCarve + microRelief, 0, 1.15),
    wet: clamp(baseWet * 0.55 + wetChannel * 0.55, 0, 1),
  };
}

function moistureToSoilFill(moisturePct: number, idx: number, selected: boolean): string {
  const m = clamp(moisturePct, 10, 55);
  const t = (m - 10) / 45;
  const boost = selected ? 20 : 0;
  const r = Math.round(clamp(54 - t * 24 - idx * 4 + boost, 14, 140));
  const g = Math.round(clamp(46 + t * 38 - idx * 3 + boost, 20, 165));
  const b = Math.round(clamp(32 + t * 52 - idx * 2 + boost, 18, 175));
  return `rgba(${r}, ${g}, ${b}, ${selected ? 0.96 : 0.88})`;
}

function terrainCellFill(
  avgNormElev: number,
  wetness: number,
  shade: number,
  showMoisture: boolean,
  isContour: boolean,
): string {
  const e = clamp(avgNormElev, 0, 1);
  const w = showMoisture ? clamp(wetness, 0, 1) : 0;

  let r = 44 + e * 48;
  let g = 74 + e * 56;
  let b = 34 + e * 20;

  if (w > 0.15) {
    const wt = clamp((w - 0.15) * 1.1, 0, 0.85);
    r = lerp(r, 24, wt);
    g = lerp(g, 148, wt);
    b = lerp(b, 172, wt);
  }

  if (isContour) {
    r = lerp(r, 210, 0.28);
    g = lerp(g, 240, 0.28);
    b = lerp(b, 245, 0.28);
  }

  return `rgba(${Math.round(clamp(r * shade, 14, 245))}, ${Math.round(clamp(g * shade, 20, 245))}, ${Math.round(clamp(b * shade, 14, 245))}, 0.94)`;
}

export function Slab3DView({ slab }: { slab: Slab3DDto }) {
  const [camera, setCamera] = useState<Camera>(PRESETS[0].camera);
  const [activePreset, setActivePreset] = useState<string>('iso');
  const [dragStart, setDragStart] = useState<Camera>(PRESETS[0].camera);
  const [size, setSize] = useState({ width: 340, height: 300 });

  const [showMoisture, setShowMoisture] = useState(true);
  const [showContours, setShowContours] = useState(true);
  const [showRunoff, setShowRunoff] = useState(true);
  const [showRoots, setShowRoots] = useState(true);
  const [selectedHorizon, setSelectedHorizon] = useState<number | null>(null);

  const pan = usePanGesture({
    runOnJS: true,
    minDistance: 2,
    onActivate: () => {
      setDragStart(camera);
      setActivePreset('');
    },
    onUpdate: (event) => {
      const nextAz = clamp(dragStart.azimuth + event.translationX * 0.45, -180, 180);
      const nextTilt = clamp(dragStart.tilt + event.translationY * 0.35, 8, 86);
      setCamera((prev) => ({ ...prev, azimuth: nextAz, tilt: nextTilt }));
    },
  });

  const adjustZoom = (delta: number) => {
    setActivePreset('');
    setCamera((prev) => ({ ...prev, zoom: clamp(Number((prev.zoom + delta).toFixed(2)), 0.72, 1.8) }));
  };

  const scene = useMemo(() => {
    const { width, height } = size;
    const mesh = slab.terrain_3d_mesh;
    const gridN = Math.max(2, mesh.grid_size || 5);

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

    // Build 5x5 normalized elevation & wetness matrices for smooth sub-grid sampling
    const elev5x5: number[][] = Array.from({ length: 5 }, (_, r) =>
      Array.from({ length: 5 }, (_, c) => {
        const rr = Math.min(gridN - 1, r);
        const cc = Math.min(gridN - 1, c);
        const v = vertexMap.get(`${rr}:${cc}`);
        return v ? (v.elevation_m - minElev) / elevSpan : 0.35;
      }),
    );
    const wet5x5: number[][] = Array.from({ length: 5 }, (_, r) =>
      Array.from({ length: 5 }, (_, c) => {
        const rr = Math.min(gridN - 1, r);
        const cc = Math.min(gridN - 1, c);
        const v = vertexMap.get(`${rr}:${cc}`);
        return v?.s1_s2_wetness_idx ?? 0.4;
      }),
    );

    const seed = Math.abs(Math.sin(slab.location.latitude * 12.9898 + slab.location.longitude * 78.233)) * 43758.5453;
    const phase = (seed - Math.floor(seed)) * Math.PI * 2;

    const baseZ = 0.16;
    const reliefAmp = 0.34;
    const N_SUB = 16;

    const surfElev: number[][] = Array.from({ length: N_SUB + 1 }, () => new Array(N_SUB + 1).fill(0));
    const surfWet: number[][] = Array.from({ length: N_SUB + 1 }, () => new Array(N_SUB + 1).fill(0));
    const surfPts: Projected[][] = Array.from({ length: N_SUB + 1 }, () => new Array(N_SUB + 1));

    for (let r = 0; r <= N_SUB; r++) {
      const v = r / N_SUB;
      for (let c = 0; c <= N_SUB; c++) {
        const u = c / N_SUB;
        const s = sampleHydroSurface(elev5x5, wet5x5, u, v, phase);
        surfElev[r][c] = s.elev;
        surfWet[r][c] = s.wet;
        surfPts[r][c] = project3D(
          { x: u * 2 - 1, y: v * 2 - 1, z: baseZ + s.elev * reliefAmp },
          camera,
          width,
          height,
        );
      }
    }

    // 1. Terrain-following 4-layer underground soil cutaway walls
    const horizons = slab.soil_3d_horizons.slice(0, 4);
    const totalDepth = 0.80;
    const weights = [0.15, 0.2, 0.28, 0.37];
    const follows = [
      [1.0, 0.92],
      [0.92, 0.72],
      [0.72, 0.42],
      [0.42, 0.0],
    ];
    let offCursor = 0;

    type Face = { points: Projected[]; fill: string; stroke: string; depth: number; horizonIdx?: number };
    const soilFaces: Face[] = [];

    // Helper for terrain-following horizon Z at perimeter (u, v)
    const horizonZAt = (u: number, v: number, off: number, follow: number): number => {
      const s = sampleHydroSurface(elev5x5, wet5x5, u, v, phase);
      return baseZ + s.elev * reliefAmp * follow - off;
    };

    const WALL_STEPS = 8;
    const sides: { u0: number; v0: number; u1: number; v1: number }[] = [
      { u0: 0, v0: 0, u1: 1, v1: 0 },
      { u0: 1, v0: 0, u1: 1, v1: 1 },
      { u0: 1, v0: 1, u1: 0, v1: 1 },
      { u0: 0, v0: 1, u1: 0, v1: 0 },
    ];

    horizons.forEach((h, idx) => {
      const thickness = totalDepth * (weights[idx] ?? 0.25);
      const offTop = offCursor;
      const offBot = offCursor + thickness;
      offCursor = offBot;
      const [fTop, fBot] = follows[idx] ?? [0.5, 0.0];
      const isSel = selectedHorizon === idx;
      const fill = moistureToSoilFill(h.volumetric_moisture_pct, idx, isSel);
      const stroke = isSel
        ? colors.accent
        : h.roots_present
          ? 'rgba(200,243,29,0.28)'
          : 'rgba(255,255,255,0.12)';

      for (const side of sides) {
        const topPts: Projected[] = [];
        const botPts: Projected[] = [];
        let depthSum = 0;
        for (let s = 0; s <= WALL_STEPS; s++) {
          const t = s / WALL_STEPS;
          const u = lerp(side.u0, side.u1, t);
          const v = lerp(side.v0, side.v1, t);
          const ptTop = project3D({ x: u * 2 - 1, y: v * 2 - 1, z: horizonZAt(u, v, offTop, fTop) }, camera, width, height);
          const ptBot = project3D({ x: u * 2 - 1, y: v * 2 - 1, z: horizonZAt(u, v, offBot, fBot) }, camera, width, height);
          topPts.push(ptTop);
          botPts.unshift(ptBot);
          depthSum += ptTop.depth + ptBot.depth;
        }
        soilFaces.push({
          points: [...topPts, ...botPts],
          fill,
          stroke,
          depth: depthSum / (2 * (WALL_STEPS + 1)),
          horizonIdx: idx,
        });
      }
    });

    soilFaces.sort((a, b) => b.depth - a.depth);
    const visibleSoilFaces = soilFaces.slice(Math.floor(soilFaces.length / 2));

    // Active root depth plane
    const rootFrac = clamp(slab.active_root_depth_m / 1.0, 0.05, 1);
    const rootZ = baseZ - totalDepth * rootFrac;
    const rootPlane = [
      project3D({ x: -1.02, y: -1.02, z: rootZ }, camera, width, height),
      project3D({ x: 1.02, y: -1.02, z: rootZ }, camera, width, height),
      project3D({ x: 1.02, y: 1.02, z: rootZ }, camera, width, height),
      project3D({ x: -1.02, y: 1.02, z: rootZ }, camera, width, height),
    ];

    // 2. High-Res 16x16 Terrain Surface Quads with NW Sun Hillshading
    const lx = -0.55;
    const ly = -0.45;
    const lz = 0.70;
    const lLen = Math.hypot(lx, ly, lz);
    const nlx = lx / lLen;
    const nly = ly / lLen;
    const nlz = lz / lLen;

    const terrainQuads: Face[] = [];
    for (let r = 0; r < N_SUB; r++) {
      for (let c = 0; c < N_SUB; c++) {
        const e00 = surfElev[r][c];
        const e10 = surfElev[r][c + 1];
        const e11 = surfElev[r + 1][c + 1];
        const e01 = surfElev[r + 1][c];

        const dzDx = ((e10 - e00) + (e11 - e01)) * 0.5 * N_SUB * 0.45;
        const dzDy = ((e01 - e00) + (e11 - e10)) * 0.5 * N_SUB * 0.45;
        const nLen = Math.hypot(-dzDx, -dzDy, 1);
        const dot = (-dzDx * nlx - dzDy * nly + nlz) / nLen;
        const shade = clamp(0.58 + 0.55 * dot, 0.42, 1.18);

        const avgNorm = (e00 + e10 + e11 + e01) / 4;
        const avgWet = (surfWet[r][c] + surfWet[r][c + 1] + surfWet[r + 1][c + 1] + surfWet[r + 1][c]) / 4;
        const minF = Math.min(e00, e10, e11, e01);
        const maxF = Math.max(e00, e10, e11, e01);
        const isContour = showContours && Math.floor(minF * 7) !== Math.floor(maxF * 7);

        const p00 = surfPts[r][c];
        const p10 = surfPts[r][c + 1];
        const p11 = surfPts[r + 1][c + 1];
        const p01 = surfPts[r + 1][c];
        const avgDepth = (p00.depth + p10.depth + p11.depth + p01.depth) / 4;

        terrainQuads.push({
          points: [p00, p10, p11, p01],
          fill: terrainCellFill(avgNorm, avgWet, shade, showMoisture, isContour),
          stroke: isContour ? 'rgba(200,243,29,0.22)' : 'rgba(255,255,255,0.08)',
          depth: avgDepth,
        });
      }
    }
    terrainQuads.sort((a, b) => b.depth - a.depth);

    // 3. Downhill runoff flow arrows (-grad z)
    const runoffArrows: { start: Projected; end: Projected }[] = [];
    if (showRunoff) {
      for (let r = 2; r < N_SUB - 1; r += 3) {
        for (let c = 2; c < N_SUB - 1; c += 3) {
          const dzDu = (surfElev[r][c + 1] - surfElev[r][c - 1]) * 0.5 * N_SUB;
          const dzDv = (surfElev[r + 1][c] - surfElev[r - 1][c]) * 0.5 * N_SUB;
          const mag = Math.hypot(dzDu, dzDv);
          if (mag > 0.12) {
            const u0 = c / N_SUB;
            const v0 = r / N_SUB;
            const u1 = clamp(u0 - (dzDu / mag) * 0.08, 0.03, 0.97);
            const v1 = clamp(v0 - (dzDv / mag) * 0.08, 0.03, 0.97);
            const s1 = sampleHydroSurface(elev5x5, wet5x5, u1, v1, phase);
            runoffArrows.push({
              start: project3D({ x: u0 * 2 - 1, y: v0 * 2 - 1, z: baseZ + surfElev[r][c] * reliefAmp + 0.015 }, camera, width, height),
              end: project3D({ x: u1 * 2 - 1, y: v1 * 2 - 1, z: baseZ + s1.elev * reliefAmp + 0.015 }, camera, width, height),
            });
          }
        }
      }
    }

    // 4. Project boundary_uv onto hydro surface
    const rawUv = mesh.boundary_uv.length >= 3
      ? mesh.boundary_uv
      : [
          { u: 0.18, v: 0.18 },
          { u: 0.82, v: 0.18 },
          { u: 0.82, v: 0.82 },
          { u: 0.18, v: 0.82 },
        ];

    const parcelPoints = rawUv.map((pt) => {
      const u = clamp(pt.u, 0, 1);
      const v = clamp(pt.v, 0, 1);
      const s = sampleHydroSurface(elev5x5, wet5x5, u, v, phase);
      return project3D(
        { x: u * 2 - 1, y: v * 2 - 1, z: baseZ + s.elev * reliefAmp + 0.03 },
        camera,
        width,
        height,
      );
    });

    const parcelAnchors = parcelPoints.slice(0, 4).map((pp, idx) => {
      const uv = rawUv[idx];
      const u = clamp(uv.u, 0, 1);
      const v = clamp(uv.v, 0, 1);
      const rp = project3D({ x: u * 2 - 1, y: v * 2 - 1, z: rootZ }, camera, width, height);
      return { top: pp, bot: rp };
    });

    return {
      visibleSoilFaces,
      rootPlane,
      terrainQuads,
      runoffArrows,
      parcelPoints,
      parcelAnchors,
    };
  }, [slab, camera, size, showMoisture, showContours, showRunoff, selectedHorizon]);

  const ndvi = slab.canopy_layer.ndvi_current;
  const canopyOpacity = clamp(ndvi * 0.45, 0.12, 0.40);
  const inspectedHorizon = selectedHorizon !== null ? slab.soil_3d_horizons[selectedHorizon] : null;

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
                <Stop offset="1" stopColor={colors.forest700} stopOpacity={0.20} />
              </LinearGradient>
            </Defs>

            {/* Terrain-Following 3D Soil Horizons */}
            {scene.visibleSoilFaces.map((face, idx) => (
              <Polygon
                key={`soil-${idx}`}
                points={pts(face.points)}
                fill={face.fill}
                stroke={face.stroke}
                strokeWidth={face.horizonIdx === selectedHorizon ? 1.8 : 1}
                onPress={face.horizonIdx !== undefined
                  ? () => setSelectedHorizon((prev) => (prev === face.horizonIdx ? null : face.horizonIdx ?? null))
                  : undefined}
              />
            ))}

            {/* Active Root Depth Plane */}
            {showRoots && (
              <Polygon
                points={pts(scene.rootPlane)}
                fill="rgba(200, 243, 29, 0.08)"
                stroke={colors.accent}
                strokeWidth={1.2}
                strokeDasharray="5 4"
              />
            )}

            {/* High-Res 16x16 Hydro-Conditioned Terrain Mesh */}
            {scene.terrainQuads.map((quad, idx) => (
              <Polygon
                key={`quad-${idx}`}
                points={pts(quad.points)}
                fill={quad.fill}
                stroke={quad.stroke}
                strokeWidth={0.5}
              />
            ))}

            {/* 3D Downhill Runoff Arrows */}
            {scene.runoffArrows.map((arrow, idx) => (
              <Line
                key={`flow-${idx}`}
                x1={arrow.start.sx}
                y1={arrow.start.sy}
                x2={arrow.end.sx}
                y2={arrow.end.sy}
                stroke="rgba(125, 211, 252, 0.88)"
                strokeWidth={1.5}
              />
            ))}

            {/* Parcel Vertical Depth Anchors */}
            {showRoots && scene.parcelAnchors.map((anchor, idx) => (
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

            {/* Projected Parcel Boundary */}
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

          {/* Interactive Zoom Controls */}
          <View style={styles.zoomStack}>
            <Pressable
              accessibilityRole="button"
              accessibilityLabel="Zoom in 3D view"
              onPress={() => adjustZoom(0.16)}
              style={({ pressed }) => [styles.zoomBtn, pressed && styles.pressed]}
            >
              <Label variant="button" tone="cream">+</Label>
            </Pressable>
            <Pressable
              accessibilityRole="button"
              accessibilityLabel="Zoom out 3D view"
              onPress={() => adjustZoom(-0.16)}
              style={({ pressed }) => [styles.zoomBtn, pressed && styles.pressed]}
            >
              <Label variant="button" tone="cream">-</Label>
            </Pressable>
          </View>
        </View>
      </GestureDetector>

      {inspectedHorizon && (
        <Surface kind="strong" rounding={radius.tile} style={styles.inspectorBar}>
          <Label variant="smallBold" tone="accent">{inspectedHorizon.depth_label}</Label>
          <Label variant="caption" tone="cream">
            pH {formatNumber(inspectedHorizon.ph, 2)} · {formatNumber(inspectedHorizon.volumetric_moisture_pct, 1)}% vol
            {inspectedHorizon.usda_texture ? ` · ${inspectedHorizon.usda_texture}` : ''}
          </Label>
        </Surface>
      )}

      {/* Interactive Layer Toggles */}
      <View style={styles.presetRow}>
        {[
          { label: 'Moisture', active: showMoisture, toggle: () => setShowMoisture((v) => !v) },
          { label: 'Contours', active: showContours, toggle: () => setShowContours((v) => !v) },
          { label: 'Runoff', active: showRunoff, toggle: () => setShowRunoff((v) => !v) },
          { label: 'Roots', active: showRoots, toggle: () => setShowRoots((v) => !v) },
        ].map((layer) => (
          <Pressable
            key={layer.label}
            accessibilityRole="button"
            accessibilityState={{ selected: layer.active }}
            onPress={layer.toggle}
            style={({ pressed }) => [
              styles.layerChip,
              layer.active && styles.layerChipActive,
              pressed && styles.pressed,
            ]}
          >
            <Label variant="caption" tone={layer.active ? 'accent' : 'muted'}>
              {layer.label}
            </Label>
          </Pressable>
        ))}
      </View>

      {/* Camera Viewpoint Presets */}
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
        <Label variant="caption" tone="muted">Drag to orbit · Tap soil layer</Label>
      </View>
    </Surface>
  );
}

const styles = StyleSheet.create({
  container: { padding: space.md, gap: space.sm, overflow: 'hidden' },
  hudTop: { gap: space.xs },
  badgeRow: { flexDirection: 'row', flexWrap: 'wrap', gap: space.xs },
  hudBadge: { flexDirection: 'row', alignItems: 'center', gap: space.xs, paddingHorizontal: space.sm, paddingVertical: space.xs },
  canvas: { height: 290, width: '100%', position: 'relative' },
  zoomStack: { position: 'absolute', right: space.xs, top: space.xs, gap: space.xs },
  zoomBtn: {
    width: 32,
    height: 32,
    borderRadius: radius.pill,
    backgroundColor: colors.chip,
    borderWidth: 1,
    borderColor: colors.border,
    alignItems: 'center',
    justifyContent: 'center',
  },
  inspectorBar: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: space.md,
    paddingVertical: space.xs + 2,
    gap: space.sm,
  },
  controlsBottom: { flexDirection: 'row', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: space.sm },
  presetRow: { flexDirection: 'row', flexWrap: 'wrap', gap: space.xs },
  layerChip: {
    paddingHorizontal: space.sm + 2,
    paddingVertical: space.xs,
    borderRadius: radius.pill,
    backgroundColor: colors.forest950,
    borderWidth: 1,
    borderColor: colors.border,
  },
  layerChipActive: {
    borderColor: colors.accent,
  },
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
