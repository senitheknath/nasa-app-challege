import { z } from 'zod';
import { strings } from '@/i18n/strings';
import { formatPercent, formatUnit } from '@/utils/format';

export const categorySchema = z.object({ id: z.string().min(1), label: z.string().min(1) });
export const categoriesSchema = z.array(categorySchema);
export const cropSchema = z.object({
  id: z.string().min(1),
  name: z.string().min(1),
  category: categorySchema,
  yieldTonnesPerHectare: z.number().nonnegative(),
  waterPercent: z.number().min(0).max(100),
  scientificName: z.string().optional(),
  family: z.string().optional(),
  lifeCycle: z.string().optional(),
  growthDays: z.string().optional(),
  suitability: z.string().optional(),
  reason: z.string().optional(),
  supportLevel: z.string().optional(),
  score: z.number().optional(),
});
export const cropPageSchema = z.object({ items: z.array(cropSchema), nextCursor: z.string().min(1).nullable() });

export type CategoryDto = z.infer<typeof categorySchema>;
export type CropDto = z.infer<typeof cropSchema>;
export type CropPageDto = z.infer<typeof cropPageSchema>;
export type Category = { id: string; label: string };
export type Crop = {
  id: string;
  name: string;
  category: string;
  cropYield: string;
  water: number;
  waterLabel: string;
  scientificName?: string;
  family?: string;
  lifeCycle?: string;
  growthDays?: string;
  suitability?: string;
  reason?: string;
  supportLevel?: string;
  botanicalSummary?: string;
  coverageValue: number;
  coverageLabel: string;
};
export type CropPage = { items: Crop[]; nextCursor: string | null };

const SUPPORT_COVERAGE: Record<string, number> = {
  regional: 100,
  general: 70,
  catalogue: 35,
};

const capitalize = (value?: string) => (value ? value.charAt(0).toUpperCase() + value.slice(1) : undefined);

export const mapCategory = (dto: CategoryDto): Category => ({ id: dto.id, label: dto.label });
export const mapCrop = (dto: CropDto): Crop => {
  const supportKey = dto.supportLevel?.toLowerCase() ?? '';
  const coverageValue = SUPPORT_COVERAGE[supportKey] ?? dto.waterPercent;
  const supportName = strings.supportLevels[supportKey];
  const coverageLabel = supportName ? `${supportName} ${formatPercent(coverageValue)}` : formatPercent(dto.waterPercent);
  const lifeCycleLabel = capitalize(dto.lifeCycle);
  const botanicalParts = [dto.family, lifeCycleLabel].filter(Boolean);

  return {
    id: dto.id,
    name: dto.name,
    category: dto.category.label,
    cropYield: formatUnit(dto.yieldTonnesPerHectare, strings.units.cropYield, Number.isInteger(dto.yieldTonnesPerHectare) ? 0 : 1),
    water: dto.waterPercent,
    waterLabel: formatPercent(dto.waterPercent),
    scientificName: dto.scientificName,
    family: dto.family,
    lifeCycle: lifeCycleLabel,
    growthDays: dto.growthDays,
    suitability: dto.suitability,
    reason: dto.reason,
    supportLevel: dto.supportLevel,
    botanicalSummary: botanicalParts.length > 0 ? botanicalParts.join(' · ') : undefined,
    coverageValue,
    coverageLabel,
  };
};
export const mapCropPage = (dto: CropPageDto): CropPage => ({
  items: dto.items.map(mapCrop), nextCursor: dto.nextCursor,
});
