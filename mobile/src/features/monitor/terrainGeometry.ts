import { type Slab3DDto, type TerrainVertexDto } from './model';

export type Camera = { azimuth: number; tilt: number; zoom: number };
export type Vec3 = { x: number; y: number; z: number };
export type Projected = { sx: number; sy: number; depth: number };
export type UV = { u: number; v: number };

export function clamp(val: number, min: number, max: number): number {
  return Math.max(min, Math.min(max, val));
}

export function lerp(a: number, b: number, t: number): number {
  return a + (b - a) * t;
}

export function project3D(p: Vec3, cam: Camera, width: number, height: number, centerYFrac = 0.49): Projected {
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
    sy: height * centerYFrac - zView * span * scale,
    depth: yView,
  };
}

export function pts(list: Projected[]): string {
  return list.map((p) => `${p.sx.toFixed(1)},${p.sy.toFixed(1)}`).join(' ');
}

export function isUnitSquareUv(poly: UV[]): boolean {
  if (poly.length !== 4) return false;
  return poly.every(
    (p) => (Math.abs(p.u) < 0.02 || Math.abs(p.u - 1) < 0.02) && (Math.abs(p.v) < 0.02 || Math.abs(p.v - 1) < 0.02),
  );
}

export function resolveBoundaryUv(mesh: Slab3DDto['terrain_3d_mesh']): { rawUv: UV[]; isCroppedPoly: boolean } {
  const rawUv: UV[] =
    mesh.boundary_uv.length >= 3
      ? mesh.boundary_uv.map((pt) => ({ u: clamp(pt.u, 0, 1), v: clamp(pt.v, 0, 1) }))
      : [
          { u: 0, v: 0 },
          { u: 1, v: 0 },
          { u: 1, v: 1 },
          { u: 0, v: 1 },
        ];
  return { rawUv, isCroppedPoly: rawUv.length >= 3 && !isUnitSquareUv(rawUv) };
}

export function pointInPolyUv(u: number, v: number, poly: UV[]): boolean {
  let inside = false;
  for (let i = 0, j = poly.length - 1; i < poly.length; j = i++) {
    const ui = poly[i].u;
    const vi = poly[i].v;
    const uj = poly[j].u;
    const vj = poly[j].v;
    if ((vi > v) !== (vj > v) && u < ((uj - ui) * (v - vi)) / (vj - vi || 1e-12) + ui) {
      inside = !inside;
    }
  }
  return inside;
}

export function polygonOrientation(poly: UV[]): number {
  let area2 = 0;
  for (let i = 0; i < poly.length; i++) {
    const a = poly[i];
    const b = poly[(i + 1) % poly.length];
    area2 += a.u * b.v - b.u * a.v;
  }
  return area2 >= 0 ? 1 : -1;
}

export function isConvexUvPoly(poly: UV[]): boolean {
  if (poly.length < 3) return false;
  let sign = 0;
  for (let i = 0; i < poly.length; i++) {
    const a = poly[i];
    const b = poly[(i + 1) % poly.length];
    const c = poly[(i + 2) % poly.length];
    const cross = (b.u - a.u) * (c.v - b.v) - (b.v - a.v) * (c.u - b.u);
    if (Math.abs(cross) > 1e-9) {
      const s = cross > 0 ? 1 : -1;
      if (sign === 0) sign = s;
      else if (sign !== s) return false;
    }
  }
  return sign !== 0;
}

export function raySegmentIntersect(
  ox: number,
  oy: number,
  dx: number,
  dy: number,
  ax: number,
  ay: number,
  bx: number,
  by: number,
): number | null {
  const sx = bx - ax;
  const sy = by - ay;
  const denom = dx * sy - dy * sx;
  if (Math.abs(denom) < 1e-12) return null;
  const qpx = ax - ox;
  const qpy = ay - oy;
  const t = (qpx * sy - qpy * sx) / denom;
  const u = (qpx * dy - qpy * dx) / denom;
  if (t >= 0 && t <= 1.0001 && u >= -1e-6 && u <= 1.000001) {
    return t;
  }
  return null;
}

export function snapQuadToPoly(corners: UV[], poly: UV[]): UV[] | null {
  const insideFlags = corners.map((c) => pointInPolyUv(c.u, c.v, poly));
  const insideCount = insideFlags.filter(Boolean).length;
  if (insideCount === 4) return corners;

  const cu = corners.reduce((s, p) => s + p.u, 0) / 4;
  const cv = corners.reduce((s, p) => s + p.v, 0) / 4;
  const centerInside = pointInPolyUv(cu, cv, poly);
  if (insideCount === 0 && !centerInside) return null;

  let au = cu;
  let av = cv;
  if (!centerInside) {
    const ins = corners.filter((_, idx) => insideFlags[idx]);
    au = ins.reduce((s, p) => s + p.u, 0) / ins.length;
    av = ins.reduce((s, p) => s + p.v, 0) / ins.length;
  }

  return corners.map((pt, idx) => {
    if (insideFlags[idx]) return pt;
    const dx = pt.u - au;
    const dy = pt.v - av;
    let bestT = 1;
    for (let i = 0; i < poly.length; i++) {
      const a = poly[i];
      const b = poly[(i + 1) % poly.length];
      const t = raySegmentIntersect(au, av, dx, dy, a.u, a.v, b.u, b.v);
      if (t !== null && t < bestT) bestT = t;
    }
    return { u: au + dx * bestT, v: av + dy * bestT };
  });
}

/**
 * Exact Sutherland-Hodgman polygon clipping for convex boundary polygons,
 * with graceful fallback to ray-snapping for concave shapes.
 */
export function clipCellToPolyUv(corners: UV[], poly: UV[], convex?: boolean): UV[] | null {
  const useConvexClip = convex ?? isConvexUvPoly(poly);
  if (!useConvexClip) {
    return snapQuadToPoly(corners, poly);
  }
  const orient = polygonOrientation(poly);
  let output: UV[] = corners;

  for (let i = 0; i < poly.length; i++) {
    if (output.length < 3) return null;
    const a = poly[i];
    const b = poly[(i + 1) % poly.length];
    const eu = b.u - a.u;
    const ev = b.v - a.v;
    const isInside = (p: UV) => ((p.u - a.u) * ev - (p.v - a.v) * eu) * orient <= 1e-9;

    const intersect = (p1: UV, p2: UV): UV => {
      const d1 = ((p1.u - a.u) * ev - (p1.v - a.v) * eu) * orient;
      const d2 = ((p2.u - a.u) * ev - (p2.v - a.v) * eu) * orient;
      const denom = d1 - d2;
      const t = Math.abs(denom) < 1e-12 ? 0.5 : clamp(d1 / denom, 0, 1);
      return { u: lerp(p1.u, p2.u, t), v: lerp(p1.v, p2.v, t) };
    };

    const nextOut: UV[] = [];
    for (let j = 0; j < output.length; j++) {
      const curr = output[j];
      const prev = output[(j + output.length - 1) % output.length];
      const currIn = isInside(curr);
      const prevIn = isInside(prev);
      if (currIn) {
        if (!prevIn) nextOut.push(intersect(prev, curr));
        nextOut.push(curr);
      } else if (prevIn) {
        nextOut.push(intersect(prev, curr));
      }
    }
    output = nextOut;
  }

  return output.length >= 3 ? output : null;
}

export function buildVertexMatrices(slab: Slab3DDto): {
  elev5x5: number[][];
  wet5x5: number[][];
  chl5x5: number[][];
  minElev: number;
  maxElev: number;
  elevSpan: number;
  phase: number;
} {
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

  const ndviNorm = clamp((slab.canopy_layer.ndvi_current - 0.12) / 0.76, 0, 1);
  const fallbackCab = 8 + 56 * ndviNorm ** 1.15;

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
  const chl5x5: number[][] = Array.from({ length: 5 }, (_, r) =>
    Array.from({ length: 5 }, (_, c) => {
      const rr = Math.min(gridN - 1, r);
      const cc = Math.min(gridN - 1, c);
      const v = vertexMap.get(`${rr}:${cc}`);
      if (v?.chlorophyll_ug_cm2 != null) return v.chlorophyll_ug_cm2;
      const wet = v?.s1_s2_wetness_idx ?? 0.4;
      const elev = v ? (v.elevation_m - minElev) / elevSpan : 0.35;
      return clamp(fallbackCab + (wet - 0.42) * 14 - Math.abs(elev - 0.45) * 6, 5, 72);
    }),
  );

  const seed = Math.abs(Math.sin(slab.location.latitude * 12.9898 + slab.location.longitude * 78.233)) * 43758.5453;
  const phase = (seed - Math.floor(seed)) * Math.PI * 2;

  return { elev5x5, wet5x5, chl5x5, minElev, maxElev, elevSpan, phase };
}

export function sampleHydroSurface(
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

export function sampleChlorophyllUgCm2(
  chl5x5: number[][],
  wet: number,
  elev: number,
  u: number,
  v: number,
  phase: number,
  ndviShiftCab = 0,
): number {
  const gx = clamp(u * 4, 0, 4);
  const gy = clamp(v * 4, 0, 4);
  const c0 = Math.min(3, Math.floor(gx));
  const r0 = Math.min(3, Math.floor(gy));
  const tx = gx - c0;
  const ty = gy - r0;
  const sx = tx * tx * (3 - 2 * tx);
  const sy = ty * ty * (3 - 2 * ty);

  const top = lerp(chl5x5[r0][c0], chl5x5[r0][c0 + 1], sx);
  const bot = lerp(chl5x5[r0 + 1][c0], chl5x5[r0 + 1][c0 + 1], sx);
  const baseCab = lerp(top, bot, sy);

  // Fine 10m canopy chlorophyll patchiness driven by moisture & solar aspect micro-variation
  const microWave = 2.4 * Math.sin(u * Math.PI * 4.5 + phase * 1.3) * Math.cos(v * Math.PI * 3.8 - phase);
  const moistureBoost = (wet - 0.45) * 5.0 - Math.max(0, elev - 0.85) * 4.0;
  return clamp(baseCab + ndviShiftCab + microWave + moistureBoost, 5, 72);
}

/**
 * Map Leaf Chlorophyll Content (Cab in ug/cm2, ~10..68) to an agronomic heatmap RGB color
 * (chlorotic amber-yellow -> chartreuse -> healthy emerald -> dense deep chlorophyll green).
 */
export function chlorophyllHeatmapFill(cabUgCm2: number, shade = 1): string {
  const t = clamp((cabUgCm2 - 8) / 56, 0, 1);
  let r: number;
  let g: number;
  let b: number;

  if (t < 0.35) {
    const k = t / 0.35;
    r = lerp(180, 234, k); // #B45309 -> #EAB308
    g = lerp(83, 179, k);
    b = lerp(9, 8, k);
  } else if (t < 0.65) {
    const k = (t - 0.35) / 0.3;
    r = lerp(234, 132, k); // #EAB308 -> #84CC16
    g = lerp(179, 204, k);
    b = lerp(8, 22, k);
  } else {
    const k = (t - 0.65) / 0.35;
    r = lerp(132, 21, k); // #84CC16 -> #15803D
    g = lerp(204, 152, k);
    b = lerp(22, 61, k);
  }

  return `rgb(${Math.round(clamp(r * shade, 10, 250))}, ${Math.round(clamp(g * shade, 14, 250))}, ${Math.round(clamp(b * shade, 8, 240))})`;
}
