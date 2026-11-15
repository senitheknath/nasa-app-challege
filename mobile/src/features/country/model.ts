import { z } from 'zod';
import { formatNumber } from '@/utils/format';

export const countrySchema = z.object({
  id: z.string().min(1),
  name: z.string().min(1),
  supported: z.boolean(),
  latitude: z.number().optional(),
  longitude: z.number().optional(),
  zoom: z.number().optional(),
});
export const countryDataSchema = z.object({
  defaultCountryId: z.string(),
  currentSeason: z.string(),
  countryCount: z.number().int().nonnegative().optional(),
  cropCount: z.number().int().nonnegative(),
  seasonCount: z.number().int().nonnegative(),
  defaultStrategyId: z.string().min(1),
  defaultCropId: z.string().min(1),
  countries: z.array(countrySchema),
}).refine((data) => data.countries.length === 0 ||
  data.countries.some((country) => country.id === data.defaultCountryId && country.supported), {
  path: ['defaultCountryId'], message: 'Default country must be supported',
});

export type CountryDto = z.infer<typeof countrySchema>;
export type CountryDataDto = z.infer<typeof countryDataSchema>;
export type Country = { id: string; name: string; supported: boolean; latitude?: number; longitude?: number; zoom?: number };
export type CountryData = {
  defaultCountry: Country | undefined;
  season: string;
  countriesPlus: string;
  crops: string;
  cropsPlus: string;
  seasons: string;
  defaultStrategyId: string;
  defaultCropId: string;
  countries: Country[];
};

export function formatMilestonePlus(count: number): string {
  const safe = Math.max(0, Math.floor(count));
  if (safe >= 100) return `${Math.floor(safe / 10) * 10}+`;
  if (safe >= 10) return `${Math.floor(safe / 5) * 5}+`;
  return `${safe}+`;
}

export function mapCountryData(dto: CountryDataDto): CountryData {
  const countries = dto.countries.map(({ id, name, supported, latitude, longitude, zoom }) => ({
    id, name, supported, latitude, longitude, zoom,
  }));
  const resolvedCountryCount = dto.countryCount ?? countries.filter((country) => country.supported).length;
  return {
    defaultCountry: countries.find((country) => country.id === dto.defaultCountryId),
    season: dto.currentSeason,
    countriesPlus: formatMilestonePlus(resolvedCountryCount),
    crops: formatNumber(dto.cropCount),
    cropsPlus: formatMilestonePlus(dto.cropCount),
    seasons: formatNumber(dto.seasonCount),
    defaultStrategyId: dto.defaultStrategyId,
    defaultCropId: dto.defaultCropId,
    countries,
  };
}
