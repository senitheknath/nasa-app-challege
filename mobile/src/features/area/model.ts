import { z } from 'zod';
import { strings } from '@/i18n/strings';
import { pictures, type Picture } from '@/theme/images';
import { formatNumber, formatUnit } from '@/utils/format';

export const pointSchema = z.object({ x: z.number().min(0).max(100), y: z.number().min(0).max(100) });
export const geoPointSchema = z.object({ latitude: z.number(), longitude: z.number() });
export const fieldSchema = z.object({
  countryId: z.string().min(1),
  points: z.array(pointSchema).min(3).refine(isValidBoundary, 'Boundary must have distinct corners and no crossing edges'),
  latitude: z.number().optional(),
  longitude: z.number().optional(),
  boundary: z.array(geoPointSchema).optional(),
});
export const mapSchema = z.object({
  imageUrl: z.string().optional(),
  latitude: z.number().default(7.8731),
  longitude: z.number().default(80.7718),
  zoom: z.number().default(7),
  countryName: z.string().optional(),
  layerTitle: z.string().optional(),
  regions: z.array(z.object({ id: z.string(), name: z.string(), latitude: z.number(), longitude: z.number() })).optional(),
}).nullable();
export const placeSchema = z.object({
  id: z.string().min(1),
  name: z.string().min(1),
  latitude: z.number().optional(),
  longitude: z.number().optional(),
  detail: z.string().optional(),
});
export const placesSchema = z.array(placeSchema);
export const measurementSchema = z.object({
  hectares: z.number().nonnegative(),
  acres: z.number().nonnegative(),
  perimeterKm: z.number().nonnegative(),
  ph: z.number().nullable().optional(),
  drainage: z.string().nullable().optional(),
  annualRainfallMm: z.number().nullable().optional(),
  meanTemperatureC: z.number().nullable().optional(),
  wetness: z.string().nullable().optional(),
  latitude: z.number().optional(),
  longitude: z.number().optional(),
}).nullable();

export type Point = z.infer<typeof pointSchema>;
export type GeoPoint = z.infer<typeof geoPointSchema>;
export type FieldDto = z.infer<typeof fieldSchema>;
export type MapDto = z.infer<typeof mapSchema>;
export type PlaceDto = z.infer<typeof placeSchema>;
export type MeasurementDto = z.infer<typeof measurementSchema>;
export type FieldMap = {
  image: Picture;
  latitude: number;
  longitude: number;
  zoom: number;
  countryName?: string;
  layerTitle?: string;
  regions?: { id: string; name: string; latitude: number; longitude: number }[];
};
export type Place = { id: string; name: string; latitude?: number; longitude?: number; detail?: string };
export type Measurement = {
  hectares: string;
  acres: string;
  perimeter: string;
  areaLabel: string;
  rawHectares: number;
  ph: string | null;
  drainage: string | null;
  rainfall: string | null;
  temperature: string | null;
};

export const mapFieldMap = (dto: MapDto): FieldMap | null => dto ? {
  image: dto.imageUrl ? { uri: dto.imageUrl } : pictures.aerial,
  latitude: dto.latitude,
  longitude: dto.longitude,
  zoom: dto.zoom,
  countryName: dto.countryName,
  layerTitle: dto.layerTitle,
  regions: dto.regions,
} : null;
export const mapPlace = (dto: PlaceDto): Place => ({
  id: dto.id,
  name: dto.name,
  latitude: dto.latitude,
  longitude: dto.longitude,
  detail: dto.detail,
});
export function mapMeasurement(dto: MeasurementDto): Measurement | null {
  if (!dto) return null;
  return {
    hectares: formatNumber(dto.hectares, 1),
    acres: formatNumber(dto.acres, 1),
    perimeter: formatNumber(dto.perimeterKm, 2),
    areaLabel: formatUnit(dto.hectares, strings.units.hectares, 1),
    rawHectares: dto.hectares,
    ph: dto.ph != null ? formatNumber(dto.ph, 1) : null,
    drainage: dto.drainage ? dto.drainage.replace(/_/g, ' ') : null,
    rainfall: dto.annualRainfallMm != null ? formatNumber(dto.annualRainfallMm, 0) + ' mm' : null,
    temperature: dto.meanTemperatureC != null ? formatNumber(dto.meanTemperatureC, 1) + ' °C' : null,
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
