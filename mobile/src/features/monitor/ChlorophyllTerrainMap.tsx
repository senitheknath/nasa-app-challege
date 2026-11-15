import { useMemo, useState } from 'react';
import { Platform, Pressable, StyleSheet, View } from 'react-native';
import { GestureDetector, usePanGesture } from 'react-native-gesture-handler';
import Svg, { Circle, Defs, Line, LinearGradient, Polygon, Polyline, Rect, Stop } from 'react-native-svg';
import { Chip, Label, Stat, Surface } from '@/components/primitives';
import { colors, radius, space } from '@/theme/tokens';
import { formatNumber } from '@/utils/format';
import { type LiveStateDto, type Slab3DDto } from './model';
import {
  buildVertexMatrices,
  chlorophyllHeatmapFill,
  clamp,
  clipCellToPolyUv,
  isConvexUvPoly,
  lerp,
  pointInPolyUv,
  polygonOrientation,
  project3D,
  pts,
  resolveBoundaryUv,
  sampleChlorophyllUgCm2,
  sampleHydroSurface,
  type Camera,
  type Projected,
  type UV,
} from './terrainGeometry';

type ViewMode = '3d' | 'flat';

const CAMERA_PRESETS: Record<ViewMode, Camera> = {
  '3d': { azimuth: -38, tilt: 32, zoom: 1.05 },
  flat: { azimuth: 0, tilt: 88, zoom: 1.18 },
};

function ModePill({
  label,
  active,
  onPress,
}: {
  label: string;
  active: boolean;
  onPress: () => void;
}) {
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ selected: active }}
      onPress={onPress}
      style={({ pressed }) => [
        styles.layerChip,
        active && styles.layerChipActive,
        pressed && styles.pressed,
      ]}
    >
      <Label variant="caption" tone={active ? 'accent' : 'muted'}>
        {label}
      </Label>
    </Pressable>
  );
}

export function ChlorophyllTerrainMap({
  slab,
  liveState,
}: {
  slab: Slab3DDto;
  liveState?: LiveStateDto;
}) {
  const [viewMode, setViewMode] = useState<ViewMode>('3d');
  const [camera, setCamera] = useState<Camera>(CAMERA_PRESETS['3d']);
  const [dragStart, setDragStart] = useState<Camera>(CAMERA_PRESETS['3d']);
  const [showContours, setShowContours] = useState(true);
  const [size, setSize] = useState({ width: 340, height: 260 });

  const pan = usePanGesture({
    runOnJS: true,
    minDistance: 2,
    onActivate: () => {
      setDragStart(camera);
    },
    onUpdate: (event) => {
      const nextAz = clamp(dragStart.azimuth + event.translationX * 0.45, -180, 180);
      const nextTilt = clamp(dragStart.tilt + event.translationY * 0.35, 10, 88);
      setCamera((prev) => ({ ...prev, azimuth: nextAz, tilt: nextTilt }));
    },
  });

  const switchMode = (mode: ViewMode) => {
    setViewMode(mode);
    setCamera(CAMERA_PRESETS[mode]);
  };

  const adjustZoom = (delta: number) => {
    setCamera((prev) => ({ ...prev, zoom: clamp(Number((prev.zoom + delta).toFixed(2)), 0.78, 1.85) }));
  };

  const isFlatPose = viewMode === 'flat' && camera.tilt >= 80;
  const activeNdvi =
    liveState?.observed_ndvi ??
    (slab.canopy_layer.is_bare_soil
      ? slab.canopy_layer.ndvi_current
      : (liveState?.expected_ndvi ?? slab.canopy_layer.ndvi_current));
  const baseNdviNorm = clamp((slab.canopy_layer.ndvi_current - 0.12) / 0.76, 0, 1);
  const activeNdviNorm = clamp((activeNdvi - 0.12) / 0.76, 0, 1);
  const ndviShiftCab = (56 * activeNdviNorm ** 1.15) - (56 * baseNdviNorm ** 1.15);

  const scene = useMemo(() => {
    const { width, height } = size;
    const mesh = slab.terrain_3d_mesh;
    const { elev5x5, wet5x5, chl5x5, minElev, maxElev, phase } = buildVertexMatrices(slab);
    const { rawUv, isCroppedPoly } = resolveBoundaryUv(mesh);
    const isConvex = isConvexUvPoly(rawUv);

    const N_SUB = 18;
    const reliefAmp = isFlatPose ? 0.0 : 0.36;
    const baseZ = isFlatPose ? 0.0 : 0.08;
    const skirtBottomZ = -0.14;
    const centerYFrac = isFlatPose ? 0.50 : 0.54;

    const surfElev: number[][] = Array.from({ length: N_SUB + 1 }, () => new Array(N_SUB + 1).fill(0));
    const surfWet: number[][] = Array.from({ length: N_SUB + 1 }, () => new Array(N_SUB + 1).fill(0));
    const surfChl: number[][] = Array.from({ length: N_SUB + 1 }, () => new Array(N_SUB + 1).fill(0));
    const surfPts: Projected[][] = Array.from({ length: N_SUB + 1 }, () => new Array(N_SUB + 1));

    for (let r = 0; r <= N_SUB; r++) {
      const v = r / N_SUB;
      for (let c = 0; c <= N_SUB; c++) {
        const u = c / N_SUB;
        const s = sampleHydroSurface(elev5x5, wet5x5, u, v, phase);
        const cab = sampleChlorophyllUgCm2(chl5x5, s.wet, s.elev, u, v, phase, ndviShiftCab);
        surfElev[r][c] = s.elev;
        surfWet[r][c] = s.wet;
        surfChl[r][c] = cab;
        surfPts[r][c] = project3D(
          { x: u * 2 - 1, y: v * 2 - 1, z: baseZ + s.elev * reliefAmp },
          camera,
          width,
          height,
          centerYFrac,
        );
      }
    }

    // 1. 3D Terrain Plinth Skirt along the clipped parcel polygon walls (visible when not completely top-down)
    type Face = { points: Projected[]; fill: string; stroke: string; depth: number };
    const skirtFaces: Face[] = [];
    if (!isFlatPose) {
      const polyOrient = polygonOrientation(rawUv);
      const azRad = (camera.azimuth * Math.PI) / 180;
      const camDirX = -Math.sin(azRad);
      const camDirY = -Math.cos(azRad);
      const WALL_STEPS = 8;

      const allSides = rawUv.map((pt, i) => {
        const next = rawUv[(i + 1) % rawUv.length];
        return { u0: pt.u, v0: pt.v, u1: next.u, v1: next.v };
      });

      const visibleSides = allSides.filter((side) => {
        const du = side.u1 - side.u0;
        const dv = side.v1 - side.v0;
        const len = Math.hypot(du, dv);
        if (len < 1e-6) return false;
        const nx = (polyOrient * dv) / len;
        const ny = (-polyOrient * du) / len;
        return nx * camDirX + ny * camDirY > -0.1;
      });

      for (const side of visibleSides) {
        const du = side.u1 - side.u0;
        const dv = side.v1 - side.v0;
        const len = Math.hypot(du, dv) || 1;
        const nx = (polyOrient * dv) / len;
        const ny = (-polyOrient * du) / len;
        const wallShade = clamp(0.76 + 0.18 * (nx * -0.55 + ny * -0.45), 0.56, 0.96);
        const rCol = Math.round(58 * wallShade);
        const gCol = Math.round(68 * wallShade);
        const bCol = Math.round(42 * wallShade);

        const topPts: Projected[] = [];
        const botPts: Projected[] = [];
        let depthSum = 0;
        for (let s = 0; s <= WALL_STEPS; s++) {
          const t = s / WALL_STEPS;
          const u = lerp(side.u0, side.u1, t);
          const v = lerp(side.v0, side.v1, t);
          const surf = sampleHydroSurface(elev5x5, wet5x5, u, v, phase);
          const ptTop = project3D(
            { x: u * 2 - 1, y: v * 2 - 1, z: baseZ + surf.elev * reliefAmp },
            camera,
            width,
            height,
            centerYFrac,
          );
          const ptBot = project3D(
            { x: u * 2 - 1, y: v * 2 - 1, z: skirtBottomZ },
            camera,
            width,
            height,
            centerYFrac,
          );
          topPts.push(ptTop);
          botPts.unshift(ptBot);
          depthSum += ptTop.depth + ptBot.depth;
        }
        skirtFaces.push({
          points: [...topPts, ...botPts],
          fill: `rgba(${rCol}, ${gCol}, ${bCol}, 0.94)`,
          stroke: 'rgba(200, 243, 29, 0.28)',
          depth: depthSum / (2 * (WALL_STEPS + 1)),
        });
      }
      skirtFaces.sort((a, b) => b.depth - a.depth);
    }

    // 2. Clipped Chlorophyll Terrain Cells + Parcel Stats
    const lx = -0.55;
    const ly = -0.45;
    const lz = 0.70;
    const lLen = Math.hypot(lx, ly, lz);
    const nlx = lx / lLen;
    const nly = ly / lLen;
    const nlz = lz / lLen;

    const chlFaces: Face[] = [];
    let chlSum = 0;
    let chlCount = 0;
    let minChl = Infinity;
    let maxChl = -Infinity;
    let minSpot: UV | null = null;
    let maxSpot: UV | null = null;

    for (let r = 0; r < N_SUB; r++) {
      for (let c = 0; c < N_SUB; c++) {
        const u0 = c / N_SUB;
        const v0 = r / N_SUB;
        const u1 = (c + 1) / N_SUB;
        const v1 = (r + 1) / N_SUB;

        let clippedUv: UV[] | null = [
          { u: u0, v: v0 },
          { u: u1, v: v0 },
          { u: u1, v: v1 },
          { u: u0, v: v1 },
        ];
        if (isCroppedPoly) {
          clippedUv = clipCellToPolyUv(clippedUv, rawUv, isConvex);
          if (!clippedUv) continue;
        }

        const avgChl = (surfChl[r][c] + surfChl[r][c + 1] + surfChl[r + 1][c + 1] + surfChl[r + 1][c]) * 0.25;
        const centU = clippedUv.reduce((s, p) => s + p.u, 0) / clippedUv.length;
        const centV = clippedUv.reduce((s, p) => s + p.v, 0) / clippedUv.length;

        chlSum += avgChl;
        chlCount += 1;
        if (avgChl < minChl) {
          minChl = avgChl;
          minSpot = { u: centU, v: centV };
        }
        if (avgChl > maxChl) {
          maxChl = avgChl;
          maxSpot = { u: centU, v: centV };
        }

        const dzDx = ((surfElev[r][c + 1] - surfElev[r][c]) + (surfElev[r + 1][c + 1] - surfElev[r + 1][c])) * 0.5 * N_SUB * 0.42;
        const dzDy = ((surfElev[r + 1][c] - surfElev[r][c]) + (surfElev[r + 1][c + 1] - surfElev[r][c + 1])) * 0.5 * N_SUB * 0.42;
        const nLen = Math.hypot(-dzDx, -dzDy, 1);
        const dot = (-dzDx * nlx - dzDy * nly + nlz) / nLen;
        const shade = isFlatPose ? 1.0 : clamp(0.68 + 0.42 * dot, 0.52, 1.15);

        const projList = isCroppedPoly
          ? clippedUv.map((pt) => {
              const s = sampleHydroSurface(elev5x5, wet5x5, pt.u, pt.v, phase);
              return project3D(
                { x: pt.u * 2 - 1, y: pt.v * 2 - 1, z: baseZ + s.elev * reliefAmp },
                camera,
                width,
                height,
                centerYFrac,
              );
            })
          : [surfPts[r][c], surfPts[r][c + 1], surfPts[r + 1][c + 1], surfPts[r + 1][c]];

        const fill = chlorophyllHeatmapFill(avgChl, shade);
        chlFaces.push({
          points: projList,
          fill,
          stroke: 'rgba(18, 25, 14, 0.14)',
          depth: projList.reduce((acc, p) => acc + p.depth, 0) / projList.length,
        });
      }
    }
    chlFaces.sort((a, b) => b.depth - a.depth);

    // 3. Elevation contours draped over the chlorophyll surface
    const contourLines: { a: Projected; b: Projected }[] = [];
    if (showContours) {
      const levels = [0.18, 0.34, 0.50, 0.66, 0.82];
      for (let r = 0; r < N_SUB; r++) {
        for (let c = 0; c < N_SUB; c++) {
          const corners = [
            { u: c / N_SUB, v: r / N_SUB, e: surfElev[r][c] },
            { u: (c + 1) / N_SUB, v: r / N_SUB, e: surfElev[r][c + 1] },
            { u: (c + 1) / N_SUB, v: (r + 1) / N_SUB, e: surfElev[r + 1][c + 1] },
            { u: c / N_SUB, v: (r + 1) / N_SUB, e: surfElev[r + 1][c] },
          ];
          const minE = Math.min(corners[0].e, corners[1].e, corners[2].e, corners[3].e);
          const maxE = Math.max(corners[0].e, corners[1].e, corners[2].e, corners[3].e);
          for (const lvl of levels) {
            if (lvl < minE || lvl > maxE) continue;
            const hits: UV[] = [];
            for (let edge = 0; edge < 4; edge++) {
              const p1 = corners[edge];
              const p2 = corners[(edge + 1) % 4];
              if ((p1.e <= lvl && p2.e > lvl) || (p2.e <= lvl && p1.e > lvl)) {
                const t = (lvl - p1.e) / (p2.e - p1.e || 1e-9);
                hits.push({ u: lerp(p1.u, p2.u, t), v: lerp(p1.v, p2.v, t) });
              }
            }
            if (hits.length >= 2) {
              const mu = (hits[0].u + hits[1].u) * 0.5;
              const mv = (hits[0].v + hits[1].v) * 0.5;
              if (isCroppedPoly && !pointInPolyUv(mu, mv, rawUv)) continue;
              const zElev = baseZ + lvl * reliefAmp + 0.008;
              contourLines.push({
                a: project3D({ x: hits[0].u * 2 - 1, y: hits[0].v * 2 - 1, z: zElev }, camera, width, height, centerYFrac),
                b: project3D({ x: hits[1].u * 2 - 1, y: hits[1].v * 2 - 1, z: zElev }, camera, width, height, centerYFrac),
              });
            }
          }
        }
      }
    }

    // 4. Parcel cutout boundary outline along terrain relief
    const boundaryPts = rawUv.map((pt) => {
      const s = sampleHydroSurface(elev5x5, wet5x5, pt.u, pt.v, phase);
      return project3D(
        { x: pt.u * 2 - 1, y: pt.v * 2 - 1, z: baseZ + s.elev * reliefAmp + 0.012 },
        camera,
        width,
        height,
        centerYFrac,
      );
    });

    const projectSpot = (spot: UV | null) => {
      if (!spot) return null;
      const s = sampleHydroSurface(elev5x5, wet5x5, spot.u, spot.v, phase);
      return project3D(
        { x: spot.u * 2 - 1, y: spot.v * 2 - 1, z: baseZ + s.elev * reliefAmp + 0.018 },
        camera,
        width,
        height,
        centerYFrac,
      );
    };

    const meanChl = chlCount > 0 ? chlSum / chlCount : slab.canopy_layer.chlorophyll_mean_ug_cm2 ?? 35;

    return {
      skirtFaces,
      chlFaces,
      contourLines,
      boundaryPts,
      isCroppedPoly,
      vertexCount: rawUv.length,
      meanChl,
      minChl: Number.isFinite(minChl) ? minChl : meanChl,
      maxChl: Number.isFinite(maxChl) ? maxChl : meanChl,
      minSpotPt: projectSpot(minSpot),
      maxSpotPt: projectSpot(maxSpot),
      reliefMeters: Math.max(0, maxElev - minElev),
    };
  }, [slab, camera, size, showContours, isFlatPose, ndviShiftCab]);

  const sourceLabel =
    slab.canopy_layer.chlorophyll_source ?? 'Sentinel-2 / HLS / MODIS + 30m TWI';

  return (
    <Surface kind="card" rounding={radius.card} style={styles.cardPad}>
      <View style={styles.headerRow}>
        <View style={styles.titleBlock}>
          <Label variant="tag" tone="sage">SATELLITE CHLOROPHYLL · TERRAIN FITTED</Label>
          <Label variant="cardTitle" tone="cream">Canopy Chlorophyll Heatmap</Label>
        </View>
        <Chip label={scene.isCroppedPoly ? `Cut (${scene.vertexCount}-pt)` : 'Parcel Grid'} accent />
      </View>

      <View style={styles.controlsRow}>
        <View style={styles.modeToggleWrap}>
          <ModePill
            label="3D Terrain"
            active={viewMode === '3d'}
            onPress={() => switchMode('3d')}
          />
          <ModePill
            label="Flat Map"
            active={viewMode === 'flat'}
            onPress={() => switchMode('flat')}
          />
        </View>
        <ModePill
          label="Contours"
          active={showContours}
          onPress={() => setShowContours((v) => !v)}
        />
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
              <LinearGradient id="chlBgGlow" x1="0" y1="0" x2="0" y2="1">
                <Stop offset="0" stopColor="#121A0E" stopOpacity="1" />
                <Stop offset="1" stopColor="#0A0F08" stopOpacity="1" />
              </LinearGradient>
            </Defs>
            <Rect x={0} y={0} width={size.width} height={size.height} fill="url(#chlBgGlow)" rx={12} />

            {/* 3D Terrain Plinth Skirt Cut to Selected Boundary */}
            {scene.skirtFaces.map((face, idx) => (
              <Polygon
                key={`skirt-${idx}`}
                points={pts(face.points)}
                fill={face.fill}
                stroke={face.stroke}
                strokeWidth={0.8}
              />
            ))}

            {/* Polygon-Clipped Satellite Chlorophyll Raster Draped on Terrain */}
            {scene.chlFaces.map((face, idx) => (
              <Polygon
                key={`chl-${idx}`}
                points={pts(face.points)}
                fill={face.fill}
                stroke={face.stroke}
                strokeWidth={0.35}
              />
            ))}

            {/* Elevation Contour Lines Draped Over Chlorophyll Surface */}
            {scene.contourLines.map((seg, idx) => (
              <Line
                key={`cnt-${idx}`}
                x1={seg.a.sx}
                y1={seg.a.sy}
                x2={seg.b.sx}
                y2={seg.b.sy}
                stroke="rgba(245, 248, 238, 0.36)"
                strokeWidth={0.95}
              />
            ))}

            {/* Crisp Selected Parcel Boundary Outline */}
            {scene.boundaryPts.length >= 3 && (
              <>
                <Polyline
                  points={pts([...scene.boundaryPts, scene.boundaryPts[0]])}
                  fill="none"
                  stroke={colors.accent}
                  strokeWidth={2}
                />
                {scene.boundaryPts.map((pt, idx) => (
                  <Circle
                    key={`bp-${idx}`}
                    cx={pt.sx}
                    cy={pt.sy}
                    r={2.8}
                    fill={colors.accent}
                    stroke={colors.forest950}
                    strokeWidth={1.1}
                  />
                ))}
              </>
            )}

            {/* Low / Peak Chlorophyll Hotspot Markers */}
            {scene.minSpotPt && scene.maxChl - scene.minChl >= 2.5 && (
              <Circle
                cx={scene.minSpotPt.sx}
                cy={scene.minSpotPt.sy}
                r={4.5}
                fill="#EAB308"
                stroke="#181F12"
                strokeWidth={1.5}
              />
            )}
            {scene.maxSpotPt && scene.maxChl - scene.minChl >= 2.5 && (
              <Circle
                cx={scene.maxSpotPt.sx}
                cy={scene.maxSpotPt.sy}
                r={4.5}
                fill="#4ADE80"
                stroke="#181F12"
                strokeWidth={1.5}
              />
            )}
          </Svg>

          {/* Zoom Controls */}
          <View style={styles.zoomStack}>
            <Pressable
              accessibilityRole="button"
              accessibilityLabel="Zoom in chlorophyll terrain map"
              onPress={() => adjustZoom(0.16)}
              style={({ pressed }) => [styles.zoomBtn, pressed && styles.pressed]}
            >
              <Label variant="button" tone="cream">+</Label>
            </Pressable>
            <Pressable
              accessibilityRole="button"
              accessibilityLabel="Zoom out chlorophyll terrain map"
              onPress={() => adjustZoom(-0.16)}
              style={({ pressed }) => [styles.zoomBtn, pressed && styles.pressed]}
            >
              <Label variant="button" tone="cream">-</Label>
            </Pressable>
          </View>

          <View style={styles.hintOverlay}>
            <Label variant="label" tone="sage">
              {isFlatPose ? 'Flat Top-Down Cutout · Drag to tilt 3D' : '3D Terrain-Fitted · Drag to orbit'}
            </Label>
          </View>
        </View>
      </GestureDetector>

      {/* Chlorophyll Color Scale Bar (Cab ug/cm2) */}
      <View style={styles.legendWrap}>
        <View style={styles.legendBarRow}>
          <Label variant="label" tone="sage">Chlorotic (12)</Label>
          <View style={styles.legendBar}>
            <View style={[styles.legendSeg, { backgroundColor: '#D97706' }]} />
            <View style={[styles.legendSeg, { backgroundColor: '#EAB308' }]} />
            <View style={[styles.legendSeg, { backgroundColor: '#84CC16' }]} />
            <View style={[styles.legendSeg, { backgroundColor: '#22C55E' }]} />
            <View style={[styles.legendSeg, { backgroundColor: '#15803D' }]} />
          </View>
          <Label variant="label" tone="accent">Peak (64 µg/cm²)</Label>
        </View>
      </View>

      <View style={styles.statRow}>
        <Stat
          tile
          compact
          label="Mean Chl (Cab)"
          value={`${formatNumber(scene.meanChl, 1)} µg/cm²`}
          accent
          style={styles.flexOne}
        />
        <Stat
          tile
          compact
          label="Zone Range"
          value={`${formatNumber(scene.minChl, 0)}–${formatNumber(scene.maxChl, 0)}`}
          style={styles.flexOne}
        />
        <Stat
          tile
          compact
          label="Terrain Relief"
          value={`${formatNumber(scene.reliefMeters, 1)} m`}
          style={styles.flexOne}
        />
      </View>

      <View style={styles.footerRow}>
        <Label variant="caption" tone="sage">Source: {sourceLabel}</Label>
        <Label variant="caption" tone="muted">
          Elev {formatNumber(slab.terrain_3d_mesh.elevation_m, 0)}m · Slope {formatNumber(slab.terrain_3d_mesh.regional_slope_pct, 1)}%
        </Label>
      </View>
    </Surface>
  );
}

const styles = StyleSheet.create({
  cardPad: {
    padding: space.md,
    gap: space.sm,
  },
  headerRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: space.sm,
  },
  titleBlock: {
    flex: 1,
    gap: 2,
  },
  controlsRow: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    gap: space.xs,
  },
  modeToggleWrap: {
    flexDirection: 'row',
    gap: space.xs,
  },
  layerChip: {
    paddingHorizontal: space.sm,
    paddingVertical: 5,
    borderRadius: radius.pill,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: 'rgba(18, 25, 14, 0.65)',
  },
  layerChipActive: {
    borderColor: colors.accentBorder,
    backgroundColor: 'rgba(200, 243, 29, 0.12)',
  },
  canvas: {
    height: 260,
    borderRadius: radius.tile,
    overflow: 'hidden',
    position: 'relative',
    borderWidth: 1,
    borderColor: colors.border,
  },
  zoomStack: {
    position: 'absolute',
    right: 10,
    top: 10,
    gap: 6,
  },
  zoomBtn: {
    width: 30,
    height: 30,
    borderRadius: 15,
    backgroundColor: 'rgba(18, 26, 14, 0.85)',
    borderWidth: 1,
    borderColor: colors.border,
    alignItems: 'center',
    justifyContent: 'center',
  },
  pressed: {
    opacity: 0.72,
  },
  hintOverlay: {
    position: 'absolute',
    left: 10,
    bottom: 8,
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderRadius: radius.pill,
    backgroundColor: 'rgba(12, 18, 10, 0.72)',
  },
  legendWrap: {
    gap: 4,
  },
  legendBarRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  legendBar: {
    flex: 1,
    height: 8,
    borderRadius: 4,
    overflow: 'hidden',
    flexDirection: 'row',
  },
  legendSeg: {
    flex: 1,
    height: '100%',
  },
  statRow: {
    flexDirection: 'row',
    gap: space.xs,
  },
  flexOne: {
    flex: 1,
  },
  footerRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    flexWrap: 'wrap',
    gap: space.xs,
  },
});
