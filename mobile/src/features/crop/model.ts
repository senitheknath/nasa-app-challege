import { z } from 'zod';
import { strings } from '@/i18n/strings';
import { formatPercent, formatUnit } from '@/utils/format';

export const categorySchema = z.object({ id: z.string().min(1), label: z.string().min(1) });
export const categoriesSchema = z.array(categorySchema);
export const cropSchema = z.object({
  id: z.string().min(1), name: z.string().min(1), category: categorySchema,
  yieldTonnesPerHectare: z.number().nonnegative(), waterPercent: z.number().min(0).max(100),
});
export const cropPageSchema = z.object({ items: z.array(cropSchema), nextCursor: z.string().min(1).nullable() });

export type CategoryDto = z.infer<typeof categorySchema>;
export type CropDto = z.infer<typeof cropSchema>;
export type CropPageDto = z.infer<typeof cropPageSchema>;
export type Category = { id: string; label: string };
export type Crop = { id: string; name: string; category: string; cropYield: string; water: number; waterLabel: string };
export type CropPage = { items: Crop[]; nextCursor: string | null };

export const mapCategory = (dto: CategoryDto): Category => ({ id: dto.id, label: dto.label });
export const mapCrop = (dto: CropDto): Crop => ({
  id: dto.id, name: dto.name, category: dto.category.label,
  cropYield: formatUnit(dto.yieldTonnesPerHectare, strings.units.cropYield, Number.isInteger(dto.yieldTonnesPerHectare) ? 0 : 1),
  water: dto.waterPercent, waterLabel: formatPercent(dto.waterPercent),
});
export const mapCropPage = (dto: CropPageDto): CropPage => ({
  items: dto.items.map(mapCrop), nextCursor: dto.nextCursor,
});
