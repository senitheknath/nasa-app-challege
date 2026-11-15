import { fieldSchema, mapMeasurement, polygonArea } from '@/features/area/model';
import { countryDataSchema, mapCountryData } from '@/features/country/model';
import { cropPageSchema, cropSchema, mapCrop } from '@/features/crop/model';
import { mapPlan, planRequestSchema, planSchema } from '@/features/plan/model';
import { buildMockPlan } from '@/mocks/agronomy';
import { countries, crops } from '@/mocks/catalog';
import { calendarDate, parseCalendarDate } from '@/utils/format';

const field = { countryId: 'LK', points: [{ x: 0, y: 0 }, { x: 20, y: 0 }, { x: 20, y: 10 }] };
const bootstrapData = {
  defaultCountryId: 'LK', currentSeason: 'Maha', cropCount: 10, seasonCount: 2, defaultStrategyId: 'rotation', defaultCropId: 'rice', countries,
};

test('validates supported country defaults and formats counts', () => {
  const view = mapCountryData(countryDataSchema.parse(bootstrapData));
  expect(view.defaultCountry?.name).toBe('Sri Lanka');
  expect(view.crops).toBe('10');
  expect(countryDataSchema.safeParse({ ...bootstrapData, defaultCountryId: 'IN' }).success).toBe(false);
  expect(mapCountryData(countryDataSchema.parse({ ...bootstrapData, countries: [] })).defaultCountry).toBeUndefined();
});

test('rejects malformed coordinates and maps valid field metrics', () => {
  expect(polygonArea(fieldSchema.parse(field).points)).toBe(100);
  expect(fieldSchema.safeParse({ ...field, points: [{ x: 101, y: -1 }, ...field.points] }).success).toBe(false);
  expect(mapMeasurement({ hectares: 5, acres: 12.355, perimeterKm: 3.14 })).toEqual({
    hectares: '5.0', acres: '12.4', perimeter: '3.14', areaLabel: '5.0 ha',
  });
  expect(mapMeasurement(null)).toBeNull();
});

test('validates crop water bounds and cursor shape and maps units', () => {
  const crop = cropSchema.parse(crops[0]);
  expect(mapCrop(crop)).toMatchObject({ cropYield: '5.2 t/ha', waterLabel: '85%', category: 'Cereals' });
  expect(cropSchema.safeParse({ ...crop, waterPercent: 101 }).success).toBe(false);
  expect(cropPageSchema.safeParse({ items: [crop], nextCursor: '' }).success).toBe(false);
});

test('maps a crop-free Fallow preview and an empty timeline', () => {
  const draft = planRequestSchema.parse({ ...field, strategyId: 'fallow', sowingDate: '2026-11-15' });
  const dto = planSchema.parse(buildMockPlan(draft));
  expect(mapPlan(dto)).toMatchObject({ area: '5.0 ha', strategy: 'Fallow', first: { label: 'Maha 2026', crop: { name: 'Paddy Rice' } } });
  expect(mapPlan(dto && { ...dto, timeline: [] })).toBeNull();
  expect(planRequestSchema.safeParse({ ...draft, sowingDate: '2026-02-31' }).success).toBe(false);
});

test('keeps date-only values in the user’s local calendar', () => {
  expect(calendarDate(new Date(2026, 0, 1), -1)).toBe('2025-12-31');
  expect(parseCalendarDate('2024-02-29')?.getDate()).toBe(29);
  expect(parseCalendarDate('2026-02-29')).toBeNull();
});
