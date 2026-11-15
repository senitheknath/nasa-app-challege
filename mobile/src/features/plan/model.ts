import { z } from 'zod';
import { strings } from '@/i18n/strings';
import { formatUnit, parseCalendarDate } from '@/utils/format';
import { fieldSchema } from '../area/model';
import { cropSchema, mapCrop, type Crop } from '../crop/model';

export const planRequestSchema = fieldSchema.extend({
  strategyId: z.string().min(1), cropId: z.string().min(1).optional(),
  sowingDate: z.iso.date().refine((value) => parseCalendarDate(value) !== null),
});
const timelineSchema = z.object({
  id: z.string().min(1), season: z.string().min(1), year: z.number().int(),
  crop: cropSchema, note: z.string(),
});
export const planSchema = z.object({
  hectares: z.number().nonnegative(), strategyTag: z.string().min(1), crop: cropSchema,
  timeline: z.array(timelineSchema),
}).nullable();

export type PlanRequestDto = z.infer<typeof planRequestSchema>;
export type PlanDto = z.infer<typeof planSchema>;
export type PlanSeason = { id: string; season: string; label: string; crop: Crop; summary: string; note: string };
export type Plan = {
  area: string; strategy: string; crop: Crop; first: PlanSeason; nextCrop?: string; timeline: PlanSeason[];
};

export function mapPlan(dto: PlanDto): Plan | null {
  if (!dto?.timeline.length) return null;
  const timeline = dto.timeline.map((season) => {
    const crop = mapCrop(season.crop);
    return {
      id: season.id, season: season.season, label: season.season + ' ' + season.year,
      crop, summary: strings.cropSubtitle(crop.category, crop.cropYield), note: season.note,
    };
  });
  return {
    area: formatUnit(dto.hectares, strings.units.hectares, 1), strategy: dto.strategyTag, crop: mapCrop(dto.crop),
    first: timeline[0], nextCrop: timeline[1]?.crop.name, timeline,
  };
}
