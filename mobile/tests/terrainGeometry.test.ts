import { type Slab3DDto } from '@/features/monitor/model';
import {
  buildVertexMatrices,
  chlorophyllHeatmapFill,
  clipCellToPolyUv,
  isConvexUvPoly,
  project3D,
  resolveBoundaryUv,
  sampleChlorophyllUgCm2,
} from '@/features/monitor/terrainGeometry';

const makeSlab = (withVertexChl: boolean): Slab3DDto => ({
  location: { country: 'LK', latitude: 7.87, longitude: 80.77, area_ha: 4 },
  active_root_depth_m: 0.45,
  atmosphere_layer: { rainfall_mm_day: 4.5 },
  canopy_layer: {
    ndvi_current: 0.68,
    is_bare_soil: false,
    ecostress_thermal_stress_delta_c: 1.2,
    ...(withVertexChl
      ? {
          chlorophyll_mean_ug_cm2: 46.5,
          chlorophyll_min_ug_cm2: 41.0,
          chlorophyll_max_ug_cm2: 52.0,
          chlorophyll_source: 'Sentinel-2 / Landsat / MODIS + 30m TWI',
        }
      : {}),
  },
  terrain_3d_mesh: {
    grid_size: 5,
    elevation_m: 120,
    regional_slope_pct: 4.2,
    boundary_uv: [
      { u: 0.2, v: 0.1 },
      { u: 0.85, v: 0.2 },
      { u: 0.75, v: 0.85 },
      { u: 0.15, v: 0.75 },
    ],
    vertices: Array.from({ length: 25 }, (_, idx) => {
      const row = Math.floor(idx / 5);
      const col = idx % 5;
      return {
        row,
        col,
        elevation_m: 118 + row * 1.1 + col * 0.6,
        s1_s2_wetness_idx: 0.35 + (col / 4) * 0.3,
        ...(withVertexChl ? { chlorophyll_ug_cm2: 41 + col * 2.5 + row * 0.5 } : {}),
      };
    }),
  },
  soil_3d_horizons: [
    { depth_label: '0-15cm', ph: 6.4, volumetric_moisture_pct: 28, roots_present: true },
  ],
  update_frequencies: {},
  sensor_fusion: { stack: ['SENTINEL2_L2A (10m)'] },
});

test('clips grid cells accurately to selected convex polygon boundary', () => {
  const slab = makeSlab(true);
  const { rawUv, isCroppedPoly } = resolveBoundaryUv(slab.terrain_3d_mesh);
  expect(isCroppedPoly).toBe(true);
  expect(isConvexUvPoly(rawUv)).toBe(true);

  const outside = clipCellToPolyUv(
    [{ u: 0, v: 0 }, { u: 0.1, v: 0 }, { u: 0.1, v: 0.1 }, { u: 0, v: 0.1 }],
    rawUv,
    true,
  );
  expect(outside).toBeNull();

  const inside = clipCellToPolyUv(
    [{ u: 0.4, v: 0.4 }, { u: 0.5, v: 0.4 }, { u: 0.5, v: 0.5 }, { u: 0.4, v: 0.5 }],
    rawUv,
    true,
  );
  expect(inside).toHaveLength(4);

  const straddling = clipCellToPolyUv(
    [{ u: 0.1, v: 0.3 }, { u: 0.35, v: 0.3 }, { u: 0.35, v: 0.5 }, { u: 0.1, v: 0.5 }],
    rawUv,
    true,
  );
  expect(straddling).not.toBeNull();
  expect(straddling!.every((pt) => pt.u >= 0.14 && pt.u <= 0.36)).toBe(true);
});

test('samples satellite chlorophyll matrix and projects onto 3D terrain vs flat mode', () => {
  const slabWithChl = makeSlab(true);
  const { chl5x5, elev5x5, wet5x5, phase } = buildVertexMatrices(slabWithChl);
  expect(chl5x5[0][0]).toBe(41);
  expect(chl5x5[4][4]).toBe(53);

  const slabFallback = makeSlab(false);
  const fb = buildVertexMatrices(slabFallback);
  expect(fb.chl5x5[2][2]).toBeGreaterThan(20);
  expect(fb.chl5x5[2][2]).toBeLessThan(72);

  const cab = sampleChlorophyllUgCm2(chl5x5, wet5x5[2][2], elev5x5[2][2], 0.5, 0.5, phase, 0);
  expect(cab).toBeGreaterThanOrEqual(5);
  expect(cab).toBeLessThanOrEqual(72);

  const fillLow = chlorophyllHeatmapFill(15, 1);
  const fillHigh = chlorophyllHeatmapFill(60, 1);
  expect(fillLow).not.toBe(fillHigh);
  expect(fillHigh.startsWith('rgb(')).toBe(true);

  const pFlat = project3D({ x: 0, y: 0, z: 0 }, { azimuth: 0, tilt: 88, zoom: 1.18 }, 340, 260, 0.5);
  const p3dLow = project3D({ x: 0, y: 0, z: 0.08 }, { azimuth: -38, tilt: 32, zoom: 1.05 }, 340, 260, 0.54);
  const p3dHigh = project3D({ x: 0, y: 0, z: 0.44 }, { azimuth: -38, tilt: 32, zoom: 1.05 }, 340, 260, 0.54);
  expect(pFlat.sx).toBeCloseTo(170, 0);
  expect(p3dHigh.sy).toBeLessThan(p3dLow.sy);
});
