import { z } from 'zod';
import { strings } from '@/i18n/strings';
import type { Picture } from '@/theme/images';
import { formatNumber, formatUnit } from '@/utils/format';

export const pointSchema = z.object({ x: z.number().min(0).max(100), y: z.number().min(0).max(100) });
export const fieldSchema = z.object({ countryId: z.string().min(1), points: z.array(pointSchema).min(3) });
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

export function polygonArea(points: readonly Point[]) {
  if (points.length < 3) return 0;
  const twiceArea = points.reduce((sum, point, index) => {
    const next = points[(index + 1) % points.length];
    return sum + point.x * next.y - next.x * point.y;
  }, 0);
  return Math.abs(twiceArea) / 2;
}
