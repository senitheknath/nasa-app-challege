import { z } from 'zod';
import { strings } from '@/i18n/strings';
import type { Picture } from '@/theme/images';
import { formatNumber, formatUnit } from '@/utils/format';

export const pointSchema = z.object({ x: z.number().min(0).max(100), y: z.number().min(0).max(100) });
export const fieldSchema = z.object({
  countryId: z.string().min(1),
  points: z.array(pointSchema).min(3).refine(isValidBoundary, 'Boundary must have distinct corners and no crossing edges'),
});
export const mapSchema = z.object({ imageUrl: z.url({ protocol: /^https?$/ }) }).nullable();
export const placeSchema = z.object({ id: z.string().min(1), name: z.string().min(1) });
export const placesSchema = z.array(placeSchema);
export const measurementSchema = z.object({
  hectares: z.number().nonnegative(), acres: z.number().nonnegative(), perimeterKm: z.number().nonnegative(),
}).nullable();

export type Point = z.infer<typeof pointSchema>;
export type FieldDto = z.infer<typeof fieldSchema>;
export type MapDto = z.infer<typeof mapSchema>;
export type PlaceDto = z.infer<typeof placeSchema>;
export type MeasurementDto = z.infer<typeof measurementSchema>;
export type FieldMap = { image: Picture };
export type Place = { id: string; name: string };
export type Measurement = { hectares: string; acres: string; perimeter: string; areaLabel: string };

export const mapFieldMap = (dto: MapDto): FieldMap | null => dto ? { image: { uri: dto.imageUrl } } : null;
export const mapPlace = (dto: PlaceDto): Place => ({ id: dto.id, name: dto.name });
export function mapMeasurement(dto: MeasurementDto): Measurement | null {
  if (!dto) return null;
  return {
    hectares: formatNumber(dto.hectares, 1), acres: formatNumber(dto.acres, 1), perimeter: formatNumber(dto.perimeterKm, 2),
    areaLabel: formatUnit(dto.hectares, strings.units.hectares, 1),
  };
}

const geometryTolerance = 1e-8;

function orientation(a: Point, b: Point, c: Point) {
  const cross = (b.x - a.x) * (c.y - a.y) - (b.y - a.y) * (c.x - a.x);
  return Math.abs(cross) <= geometryTolerance ? 0 : Math.sign(cross);
}

function containsPoint(a: Point, b: Point, point: Point) {
  return point.x >= Math.min(a.x, b.x) - geometryTolerance && point.x <= Math.max(a.x, b.x) + geometryTolerance
    && point.y >= Math.min(a.y, b.y) - geometryTolerance && point.y <= Math.max(a.y, b.y) + geometryTolerance;
}

function edgesIntersect(a: Point, b: Point, c: Point, d: Point) {
  const abc = orientation(a, b, c);
  const abd = orientation(a, b, d);
  const cda = orientation(c, d, a);
  const cdb = orientation(c, d, b);
  return (abc * abd < 0 && cda * cdb < 0)
    || (abc === 0 && containsPoint(a, b, c))
    || (abd === 0 && containsPoint(a, b, d))
    || (cda === 0 && containsPoint(c, d, a))
    || (cdb === 0 && containsPoint(c, d, b));
}

export function isValidBoundary(points: readonly Point[]) {
  if (points.length < 3 || polygonArea(points) <= geometryTolerance) return false;
  if (new Set(points.map(({ x, y }) => x + ',' + y)).size !== points.length) return false;
  for (let start = 0; start < points.length - 2; start++) {
    for (let other = start + 2; other < points.length; other++) {
      const end = (other + 1) % points.length;
      // Consecutive edges share a corner, including the closing edge and first edge.
      if (start === end) continue;
      if (edgesIntersect(points[start], points[start + 1], points[other], points[end])) return false;
    }
  }
  return true;
}

export function polygonArea(points: readonly Point[]) {
  if (points.length < 3) return 0;
  const twiceArea = points.reduce((sum, point, index) => {
    const next = points[(index + 1) % points.length];
    return sum + point.x * next.y - next.x * point.y;
  }, 0);
  return Math.abs(twiceArea) / 2;
}
