import { polygonArea, type FieldDto } from '@/features/area/model';
import type { PlanDto, PlanRequestDto } from '@/features/plan/model';
import { parseCalendarDate } from '@/utils/format';
import { crops, strategies } from './catalog';

export function seasonOf(date: Date) {
  const month = date.getMonth();
  return month >= 9 || month <= 2 ? 'Maha' : 'Yala';
}

export function measureField(field: FieldDto) {
  const hectares = polygonArea(field.points) * .05;
  const perimeterKm = field.points.reduce((sum, point, index) => {
    const next = field.points[(index + 1) % field.points.length];
    return sum + Math.hypot(next.x - point.x, next.y - point.y);
  }, 0) * .06;
  return { hectares, acres: hectares * 2.471, perimeterKm };
}

const rotation = ['cereals', 'legumes', 'vegetables', 'roots'];
export function buildMockPlan(draft: PlanRequestDto): PlanDto {
  const strategy = strategies.find((item) => item.id === draft.strategyId);
  const crop = draft.cropId ? crops.find((item) => item.id === draft.cropId) : crops[0];
  const date = parseCalendarDate(draft.sowingDate);
  if (!strategy || !crop || !date) return null;

  const perennial = crop.category.id === 'perennial';
  const start = rotation.indexOf(crop.category.id);
  const timeline = Array.from({ length: 4 }, (_, index) => {
    const month = new Date(date.getFullYear(), date.getMonth() + index * 6, 1);
    const category = rotation[(start + index) % rotation.length];
    const next = index === 0 ? crop : perennial
      ? crops.find((item) => item.id === (index % 2 ? 'green-gram' : 'groundnut')) ?? crop
      : crops.findLast((item) => item.category.id === category) ?? crop;
    const note = perennial && index > 0 ? 'Cover crop' : next.category.id === 'legumes'
      ? 'Restores nitrogen' : index === 0 ? 'Current' : next.category.id === 'cereals' ? 'High yield' : 'Breaks pest cycle';
    return { id: 'season-' + index, season: seasonOf(month), year: month.getFullYear(), crop: next, note };
  });
  return { hectares: measureField(draft).hectares, strategyTag: strategy.tag, crop, timeline };
}
