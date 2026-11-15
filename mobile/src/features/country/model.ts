import { z } from 'zod';
import { formatNumber } from '@/utils/format';

export const countrySchema = z.object({ id: z.string().min(1), name: z.string().min(1), supported: z.boolean() });
export const countryDataSchema = z.object({
  defaultCountryId: z.string(),
  currentSeason: z.string(),
  cropCount: z.number().int().nonnegative(),
  seasonCount: z.number().int().positive(),
  defaultStrategyId: z.string().min(1),
  defaultCropId: z.string().min(1),
  countries: z.array(countrySchema),
}).refine((data) => data.countries.length === 0 ||
  data.countries.some((country) => country.id === data.defaultCountryId && country.supported), {
  path: ['defaultCountryId'], message: 'Default country must be supported',
});

export type CountryDto = z.infer<typeof countrySchema>;
export type CountryDataDto = z.infer<typeof countryDataSchema>;
export type Country = { id: string; name: string; supported: boolean };
export type CountryData = {
  defaultCountry: Country | undefined;
  season: string;
  crops: string;
  seasons: string;
  defaultStrategyId: string;
  defaultCropId: string;
  countries: Country[];
};

export function mapCountryData(dto: CountryDataDto): CountryData {
  const countries = dto.countries.map(({ id, name, supported }) => ({ id, name, supported }));
  return {
    defaultCountry: countries.find((country) => country.id === dto.defaultCountryId),
    season: dto.currentSeason, crops: formatNumber(dto.cropCount), seasons: formatNumber(dto.seasonCount),
    defaultStrategyId: dto.defaultStrategyId, defaultCropId: dto.defaultCropId, countries,
  };
}
