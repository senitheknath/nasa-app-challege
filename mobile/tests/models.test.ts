import { fieldSchema, isValidBoundary, mapMeasurement, polygonArea } from '@/features/area/model';
import { countryDataSchema, mapCountryData } from '@/features/country/model';
import { cropPageSchema, cropSchema, mapCrop } from '@/features/crop/model';
import { mapMonitorResponse, monitorResponseSchema } from '@/features/monitor/model';
import { mapPlan, planRequestSchema, planSchema, rankRotationsByFilter } from '@/features/plan/model';
import { usePlanner } from '@/state/usePlanner';
import { calendarDate, parseCalendarDate } from '@/utils/format';

const countries = [
  { id: 'LK', name: 'Sri Lanka', supported: true, latitude: 7.8731, longitude: 80.7718, zoom: 7 },
  { id: 'KE', name: 'Kenya', supported: true, latitude: -0.0236, longitude: 37.9062, zoom: 6 },
];

const field = { countryId: 'LK', points: [{ x: 0, y: 0 }, { x: 20, y: 0 }, { x: 20, y: 10 }] };
const bootstrapData = {
  defaultCountryId: 'LK',
  currentSeason: 'Continuous',
  cropCount: 107,
  seasonCount: 8,
  defaultStrategyId: 'continuous_rainfed',
  defaultCropId: 'rice',
  countries,
};

test('validates supported country defaults and formats counts', () => {
  const view = mapCountryData(countryDataSchema.parse(bootstrapData));
  expect(view.defaultCountry?.name).toBe('Sri Lanka');
  expect(view.crops).toBe('107');
  expect(countryDataSchema.safeParse({ ...bootstrapData, defaultCountryId: 'IN' }).success).toBe(false);
  expect(mapCountryData(countryDataSchema.parse({ ...bootstrapData, countries: [] })).defaultCountry).toBeUndefined();
});

test('rejects malformed coordinates and maps valid field metrics with autofill telemetry', () => {
  expect(polygonArea(fieldSchema.parse(field).points)).toBe(100);
  expect(fieldSchema.safeParse({ ...field, points: [{ x: 101, y: -1 }, ...field.points] }).success).toBe(false);
  expect(mapMeasurement({
    hectares: 5,
    acres: 12.355,
    perimeterKm: 3.14,
    ph: 6.2,
    drainage: 'well_drained',
    annualRainfallMm: 1450,
    meanTemperatureC: 27.4,
  })).toEqual({
    hectares: '5.0',
    acres: '12.4',
    perimeter: '3.14',
    areaLabel: '5.0 ha',
    rawHectares: 5,
    ph: '6.2',
    drainage: 'well drained',
    rainfall: '1,450 mm',
    temperature: '27.4 °C',
  });
  expect(mapMeasurement(null)).toBeNull();
});

test('rejects crossings and repeated corners while accepting a concave field', () => {
  const crossing = [{ x: 0, y: 0 }, { x: 9, y: 8 }, { x: 0, y: 9 }, { x: 7, y: 0 }];
  expect(polygonArea(crossing)).toBeGreaterThan(0);
  expect(fieldSchema.safeParse({ ...field, points: crossing }).success).toBe(false);
  expect(isValidBoundary([...field.points, field.points[0]])).toBe(false);
  expect(isValidBoundary([{ x: 0, y: 0 }, { x: 8, y: 0 }, { x: 4, y: 3 }, { x: 8, y: 8 }, { x: 0, y: 8 }])).toBe(true);
});

test('usePlanner handles step invalidation, GeoPoint conversion, and loadSavedFarm', () => {
  const draft = usePlanner.getState();
  try {
    draft.chooseCountry('LK', { latitude: 7.8731, longitude: 80.7718, zoom: 12 });
    draft.addPoint({ x: 25, y: 25 });
    expect(usePlanner.getState().boundary).toHaveLength(1);
    expect(usePlanner.getState().boundary[0].latitude).toBeGreaterThan(7.8731);

    draft.chooseStrategy('continuous_irrigated');
    expect(usePlanner.getState().irrigation).toBe('irrigated');
    draft.unlock(5);
    draft.chooseStrategy('continuous_irrigated');
    expect(usePlanner.getState().reached).toBe(5);

    draft.chooseStrategy('continuous_rainfed');
    expect(usePlanner.getState().reached).toBe(3);
    expect(usePlanner.getState().irrigation).toBe('rainfed');

    draft.unlock(5);
    draft.chooseCrop('maize');
    expect(usePlanner.getState().reached).toBe(4);
    draft.unlock(5);
    draft.setDate('2026-11-05');
    expect(usePlanner.getState().reached).toBe(4);

    draft.loadSavedFarm({
      id: 42,
      name: 'North Valley Parcel',
      country: 'KE',
      latitude: -0.0236,
      longitude: 37.9062,
      area_ha: 12.5,
      boundary: [
        { latitude: -0.02, longitude: 37.90 },
        { latitude: -0.02, longitude: 37.91 },
        { latitude: -0.03, longitude: 37.91 },
        { latitude: -0.03, longitude: 37.90 },
      ],
      irrigation: 'irrigated',
      crop_id: 'maize',
      start_date: '2026-11-20',
    });

    const loaded = usePlanner.getState();
    expect(loaded.farmId).toBe(42);
    expect(loaded.farmName).toBe('North Valley Parcel');
    expect(loaded.countryId).toBe('KE');
    expect(loaded.closed).toBe(true);
    expect(loaded.reached).toBe(6);
    expect(loaded.points).toHaveLength(4);
    expect(loaded.irrigation).toBe('irrigated');
  } finally {
    draft.reset();
  }
});

test('validates crop water bounds and cursor shape and maps units', () => {
  const crop = cropSchema.parse({
    id: 'rice',
    name: 'Paddy Rice',
    category: { id: 'Cereals', label: 'Cereals' },
    yieldTonnesPerHectare: 5.2,
    waterPercent: 85,
    family: 'Poaceae',
    growthDays: '110-130d',
  });
  expect(mapCrop(crop)).toMatchObject({ cropYield: '5.2 t/ha', waterLabel: '85%', category: 'Cereals', family: 'Poaceae' });
  expect(cropSchema.safeParse({ ...crop, waterPercent: 101 }).success).toBe(false);
  expect(cropPageSchema.safeParse({ items: [crop], nextCursor: '' }).success).toBe(false);
});

test('maps continuous rotation slots with FAO-56 stages and turnaround telemetry', () => {
  const draft = planRequestSchema.parse({
    ...field,
    strategyId: 'continuous_rainfed',
    cropId: 'rice',
    sowingDate: '2026-11-15',
    irrigation: 'rainfed',
  });
  expect(draft.strategyId).toBe('continuous_rainfed');

  const dto = planSchema.parse({
    hectares: 5.0,
    strategyTag: 'Rainfed',
    mode: 'continuous',
    crop: {
      id: 'rice',
      name: 'Paddy Rice',
      category: { id: 'Poaceae', label: 'Poaceae' },
      yieldTonnesPerHectare: 4.5,
      waterPercent: 50,
    },
    timeline: [
      {
        id: 'rot-1-0',
        season: 'Slot 1',
        year: 2026,
        crop: {
          id: 'rice',
          name: 'Paddy Rice',
          category: { id: 'Poaceae', label: 'Poaceae' },
          yieldTonnesPerHectare: 4.5,
          waterPercent: 50,
        },
        note: '2026-11-15 → 2027-03-15',
        sowingDate: '2026-11-15',
        harvestDate: '2027-03-15',
        stages: [
          { stage: 'initial', start_date: '2026-11-15', end_date: '2026-12-10', duration_days: 25 },
          { stage: 'development', start_date: '2026-12-10', end_date: '2027-01-14', duration_days: 35 },
          { stage: 'mid', start_date: '2027-01-14', end_date: '2027-02-23', duration_days: 40 },
          { stage: 'late', start_date: '2027-02-23', end_date: '2027-03-15', duration_days: 20 },
        ],
      },
    ],
    rotations: [
      {
        id: 'rice__mungbean',
        name: 'Paddy Rice → Mungbean',
        rank: 1,
        score: 88,
        rating: 'Optimal',
        timeline: {
          feasible: true,
          total_agronomic_score: 88,
          collision_probability_pct: 6,
          turnaround_summary: { buffer_days: 14, status: 'optimal', advisory: 'Clean 14-day residue turnaround' },
          slots: [
            {
              crop_id: 'rice',
              crop_name: 'Paddy Rice',
              family: 'Poaceae',
              sowing_date: '2026-11-15',
              harvest_nominal_date: '2027-03-15',
              growth_cycle_days: { minimum: 110, nominal: 120, maximum: 135 },
              stages: [
                { stage: 'initial', start_date: '2026-11-15', end_date: '2026-12-10', duration_days: 25 },
                { stage: 'development', start_date: '2026-12-10', end_date: '2027-01-14', duration_days: 35 },
                { stage: 'mid', start_date: '2027-01-14', end_date: '2027-02-23', duration_days: 40 },
                { stage: 'late', start_date: '2027-02-23', end_date: '2027-03-15', duration_days: 20 },
              ],
            },
          ],
        },
      },
    ],
  });

  const mapped = mapPlan(dto);
  expect(mapped).not.toBeNull();
  expect(mapped?.area).toBe('5.0 ha');
  expect(mapped?.rotations).toHaveLength(1);
  expect(mapped?.rotations[0].slots[0].stages).toHaveLength(4);
  expect(mapped?.rotations[0].slots[0].stages[0].label).toBe('Initial');
  expect(mapPlan(dto && { ...dto, timeline: [], rotations: [] })).toBeNull();
  expect(planRequestSchema.safeParse({ ...draft, sowingDate: '2026-02-31' }).success).toBe(false);
});

test('parses and maps 3D field slab and live rotation monitor response', () => {
  const dto = monitorResponseSchema.parse({
    location: { country: 'LK', latitude: 7.8731, longitude: 80.7718, area_ha: 5.0 },
    slab_3d: {
      location: { country: 'LK', latitude: 7.8731, longitude: 80.7718, area_ha: 5.0 },
      active_root_depth_m: 0.45,
      atmosphere_layer: { temp_c: 28.5 },
      canopy_layer: { ndvi_current: 0.64 },
      terrain_3d_mesh: {
        grid_size: 5,
        span_km_x: 0.5,
        span_km_y: 0.5,
        area_km2: 0.25,
        elevation_m: 142,
        regional_slope_pct: 2.3,
        boundary_uv: [{ u: 0.2, v: 0.2 }, { u: 0.8, v: 0.2 }, { u: 0.8, v: 0.8 }],
        vertices: [{ row: 0, col: 0, elevation_m: 141 }],
      },
      soil_3d_horizons: [
        { depth_label: '0-5cm', ph: 6.1, volumetric_moisture_pct: 28.4, roots_present: true },
      ],
      update_frequencies: { sentinel2: '5d' },
      sensor_fusion: {
        stack: ['SENTINEL2_L2A', 'COP_DEM_GLO30'],
        combined_parcel_dt_days: 2.5,
        parcel_mean_moisture_conserved_pct: 31.2,
      },
    },
    live_rotation_monitor: {
      t_now_day: 42,
      observed_ndvi: 0.64,
      weather_volatility: 0.18,
      plain_rotations: [
        {
          id: 'rice__mungbean',
          name: 'Paddy Rice → Mungbean',
          live_state: {
            t_now_day: 42,
            current_date: '2026-12-27',
            growth_lag_days: 2,
            active_stage: 'development',
            active_root_depth_m: 0.45,
            expected_ndvi: 0.61,
            observed_ndvi: 0.64,
            sigma_at_harvest_days: 4.5,
            uncertainty_cone_series: [
              { day: 42, nominal_progress_pct: 35, optimistic_bound_pct: 40, pessimistic_bound_pct: 30 },
            ],
          },
        },
      ],
      easiness_rotations: [],
    },
  });

  const mapped = mapMonitorResponse(dto);
  expect(mapped.elevationLabel).toBe('142 m');
  expect(mapped.slopeLabel).toBe('2.3%');
  expect(mapped.rootDepthLabel).toBe('0.45 m');
  expect(mapped.ndviLabel).toBe('0.64');
  expect(mapped.liveMonitor.plain_rotations[0].live_state.active_stage).toBe('development');
});

test('keeps date-only values in the user’s local calendar', () => {
  expect(calendarDate(new Date(2026, 0, 1), -1)).toBe('2025-12-31');
  expect(parseCalendarDate('2024-02-29')?.getDate()).toBe(29);
  expect(parseCalendarDate('2026-02-29')).toBeNull();
});

test('parses rotation plans when backend harvest_window is an object', () => {
  const harvestWindowObj = {
    early_maturity: '2025-03-15',
    nominal_maturity: '2025-03-30',
    late_maturity: '2025-04-14',
  };
  const dto = planSchema.parse({
    hectares: 12.5,
    strategyTag: 'Rainfed',
    mode: 'continuous',
    crop: {
      id: 'wheat',
      name: 'Wheat',
      category: { id: 'Poaceae', label: 'Poaceae' },
      yieldTonnesPerHectare: 4.5,
      waterPercent: 50,
    },
    timeline: [
      {
        id: 'wheat_then_mung_bean-0',
        season: '15 Nov – 13 Mar',
        year: 2024,
        crop: {
          id: 'wheat',
          name: 'Wheat',
          category: { id: 'Poaceae', label: 'Poaceae' },
          yieldTonnesPerHectare: 4.5,
          waterPercent: 50,
        },
        note: '2024-11-15 → 2025-03-30',
        sowingDate: '2024-11-15',
        harvestDate: '2025-03-30',
        harvestWindow: harvestWindowObj,
        kcMax: null,
      },
    ],
    rotations: [
      {
        id: 'wheat_then_mung_bean',
        name: 'Wheat → Mung bean',
        rank: 1,
        score: 89.9,
        rating: 'Excellent',
        timeline: {
          feasible: true,
          slots: [
            {
              crop_id: 'wheat',
              crop_name: 'Wheat',
              family: 'Poaceae',
              sowing_date: '2024-11-15',
              harvest_nominal_date: '2025-03-30',
              harvest_window: harvestWindowObj,
              kc_max: null,
            },
          ],
        },
      },
    ],
  });

  const plan = mapPlan(dto);
  expect(plan).not.toBeNull();
  expect(plan?.rotations).toHaveLength(1);
  expect(plan?.rotations[0].slots[0].harvestWindow).toContain('–');
  expect(plan?.timeline[0].harvestWindow).toContain('–');
});

test('maps multi-crop rotation slots, best rotation highlights, and concise soil benefits', () => {
  const dto = planSchema.parse({
    hectares: 3.0,
    strategyTag: 'Rainfed',
    mode: 'continuous',
    crop: {
      id: 'rice',
      name: 'Paddy Rice',
      category: { id: 'Poaceae', label: 'Poaceae' },
      yieldTonnesPerHectare: 4.5,
      waterPercent: 50,
    },
    timeline: [],
    rotations: [
      {
        id: 'rice__groundnut__cabbage__sweet_potato',
        name: 'Paddy Rice → Groundnut → Cabbage → Sweet Potato',
        rank: 1,
        score: 92,
        rating: 'Optimal',
        summary: 'Very long verbose agronomic summary sentence that must never appear inside soilBenefit pills',
        transition: {
          status: 'good',
          summary: 'Smooth residue transition',
          benefits: ['Very long transition benefit sentence that should not spam the UI card'],
        },
        easiness_matrix: {
          easiness_tier: 'Easy',
          easiness_score: 86,
        },
        timeline: {
          feasible: true,
          slots: [
            {
              crop_id: 'rice',
              crop_name: 'Paddy Rice',
              family: 'Poaceae',
              window: 'Maha 2026 (next year)',
              sowing_date: '2026-11-15',
              harvest_nominal_date: '2027-02-23',
              growth_cycle_days: { minimum: 90, nominal: 100, maximum: 110 },
              kc_max: 1.2,
            },
            {
              crop_id: 'groundnut',
              crop_name: 'Groundnut',
              family: 'Fabaceae',
              window: 'Yala 2027',
              sowing_date: '2027-03-09',
              harvest_nominal_date: '2027-06-17',
              growth_cycle_days: { minimum: 95, nominal: 100, maximum: 110 },
              kc_max: 1.15,
            },
            {
              crop_id: 'cabbage',
              crop_name: 'Cabbage',
              family: 'Brassicaceae',
              sowing_date: '2027-07-01',
              harvest_nominal_date: '2027-09-29',
              growth_cycle_days: { minimum: 85, nominal: 90, maximum: 100 },
              kc_max: null,
            },
            {
              crop_id: 'sweet_potato',
              crop_name: 'Sweet Potato',
              family: 'Convolvulaceae',
              sowing_date: '2027-10-13',
              harvest_nominal_date: '2028-01-21',
              growth_cycle_days: { minimum: 90, nominal: 100, maximum: 115 },
              kc_max: 1.0,
            },
          ],
        },
      },
      {
        id: 'rice__cowpea__maize',
        name: 'Paddy Rice → Cowpea → Maize',
        rank: 2,
        score: 86,
        rating: 'Good',
        timeline: {
          feasible: true,
          slots: [
            {
              crop_id: 'rice',
              crop_name: 'Paddy Rice',
              family: 'Poaceae',
              sowing_date: '2026-11-15',
              harvest_nominal_date: '2027-03-15',
              kc_max: 0.2,
            },
            {
              crop_id: 'cowpea',
              crop_name: 'Cowpea',
              family: 'Fabaceae',
              sowing_date: '2027-03-29',
              harvest_nominal_date: '2027-06-22',
            },
            {
              crop_id: 'maize',
              crop_name: 'Maize',
              family: 'Poaceae',
              sowing_date: '2027-07-06',
              harvest_nominal_date: '2027-10-14',
            },
          ],
        },
      },
      {
        id: 'rice__sesame__tomato',
        name: 'Paddy Rice → Sesame → Tomato',
        rank: 3,
        score: 82,
        rating: 'Good',
        timeline: {
          feasible: true,
          slots: [
            {
              crop_id: 'rice',
              crop_name: 'Paddy Rice',
              family: 'Poaceae',
              sowing_date: '2026-11-15',
              harvest_nominal_date: '2027-03-15',
            },
            {
              crop_id: 'sesame',
              crop_name: 'Sesame',
              family: 'Pedaliaceae',
              sowing_date: '2027-03-29',
              harvest_nominal_date: '2027-06-27',
            },
            {
              crop_id: 'tomato',
              crop_name: 'Tomato',
              family: 'Solanaceae',
              sowing_date: '2027-07-11',
              harvest_nominal_date: '2027-10-09',
            },
          ],
        },
      },
      {
        id: 'rice__sorghum',
        name: 'Paddy Rice → Sorghum',
        rank: 4,
        score: 76,
        rating: 'Fair',
        timeline: {
          feasible: true,
          slots: [
            {
              crop_id: 'rice',
              crop_name: 'Paddy Rice',
              family: 'Poaceae',
              sowing_date: '2026-11-15',
              harvest_nominal_date: '2027-03-15',
            },
            {
              crop_id: 'sorghum',
              crop_name: 'Sorghum',
              family: null,
              sowing_date: '2027-03-29',
              harvest_nominal_date: '2027-07-07',
            },
          ],
        },
      },
    ],
  });

  const plan = mapPlan(dto);
  expect(plan).not.toBeNull();
  expect(plan?.timeline).toHaveLength(4);
  const [best, alt2, alt3, alt4] = plan!.rotations;

  expect(best.isBest).toBe(true);
  expect(best.title).toBe('Best Rotation');
  expect(best.badge).toBe('Highest yield & fit');
  expect(best.cropCount).toBe(4);
  expect(best.totalDays).toBe(390);
  expect(best.period).toBe('Nov 2026 – Jan 2028 · 4 crops');

  expect(best.slots[0]).toMatchObject({
    order: 1,
    status: 'Current',
    shortSeason: 'Nov - Feb',
    fullSeason: '15 Nov – 23 Feb · 100d',
    actionPrefix: '',
    actionHighlight: 'Paddy Rice',
    yieldLabel: '4.5 t/ha',
    waterPercent: 78,
    soilBenefit: 'Builds root biomass',
  });
  expect(best.slots[1]).toMatchObject({
    order: 2,
    status: 'Upcoming',
    shortSeason: 'Mar - Jun',
    fullSeason: '9 Mar – 17 Jun · 100d',
    actionPrefix: '',
    actionHighlight: 'Groundnut',
    waterPercent: 75,
    soilBenefit: 'Fixes soil nitrogen',
  });
  expect(best.slots[2]).toMatchObject({
    order: 3,
    status: 'Planned',
    shortSeason: 'Jul - Sep',
    fullSeason: '1 Jul – 29 Sep · 90d',
    actionPrefix: '',
    actionHighlight: 'Cabbage',
    waterPercent: 55,
    soilBenefit: 'Breaks pest cycle',
  });
  expect(best.slots[3]).toMatchObject({
    order: 4,
    status: 'Planned',
    shortSeason: 'Oct - Jan',
    fullSeason: '13 Oct – 21 Jan · 100d',
    actionPrefix: '',
    actionHighlight: 'Sweet Potato',
    soilBenefit: 'Improves soil structure',
  });

  expect(alt2.isBest).toBe(false);
  expect(alt2.title).toBe('Alternative 2');
  expect(alt2.badge).toBe('Improves nitrogen');
  expect(alt2.cropCount).toBe(3);
  expect(alt2.totalDays).toBe(285);
  expect(alt2.period).toBe('Nov 2026 – Oct 2027 · 3 crops');
  expect(alt2.slots[0].waterPercent).toBe(25);

  expect(alt3.isBest).toBe(false);
  expect(alt3.title).toBe('Alternative 3');
  expect(alt3.badge).toBe('Breaks pest cycle');
  expect(alt3.slots[1].soilBenefit).toBe('Deep moisture capture');

  expect(alt4.isBest).toBe(false);
  expect(alt4.title).toBe('Alternative 4');
  expect(alt4.badge).toBe('Balanced cycle');
  expect(alt4.cropCount).toBe(2);
  expect(alt4.totalDays).toBe(190);
  expect(alt4.slots[1].soilBenefit).toBe('Balances soil nutrients');
});

test('usePlanner manages rotationFilter and customCropIds with max 4 crops and resets on country change/reset', () => {
  const draft = usePlanner.getState();
  try {
    expect(usePlanner.getState().rotationFilter).toBe('default');
    expect(usePlanner.getState().customCropIds).toEqual([]);

    draft.setRotationFilter('water');
    expect(usePlanner.getState().rotationFilter).toBe('water');

    draft.toggleCustomCropId('rice');
    draft.toggleCustomCropId('mungbean');
    draft.toggleCustomCropId('maize');
    draft.toggleCustomCropId('groundnut');
    draft.toggleCustomCropId('potato');
    expect(usePlanner.getState().customCropIds).toEqual(['rice', 'mungbean', 'maize', 'groundnut']);

    draft.toggleCustomCropId('mungbean');
    expect(usePlanner.getState().customCropIds).toEqual(['rice', 'maize', 'groundnut']);

    draft.setCustomCropIds(['soybean', 'cowpea', 'soybean']);
    expect(usePlanner.getState().customCropIds).toEqual(['soybean', 'cowpea']);

    draft.chooseCountry('KE');
    expect(usePlanner.getState().rotationFilter).toBe('default');
    expect(usePlanner.getState().customCropIds).toEqual([]);

    draft.setRotationFilter('pest');
    draft.setCustomCropIds(['maize', 'groundnut']);
    draft.reset();
    expect(usePlanner.getState().rotationFilter).toBe('default');
    expect(usePlanner.getState().customCropIds).toEqual([]);
  } finally {
    draft.reset();
  }
});

test('maps filterScores, isCustom, customComparison, smartSwap and ranks rotations via rankRotationsByFilter', () => {
  const req = planRequestSchema.parse({
    ...field,
    strategyId: 'continuous_rainfed',
    sowingDate: '2026-11-15',
    customCropIds: ['maize', 'groundnut', 'potato'],
  });
  expect(req.customCropIds).toEqual(['maize', 'groundnut', 'potato']);

  const dto = planSchema.parse({
    hectares: 4.0,
    strategyTag: 'Rainfed',
    mode: 'continuous',
    crop: {
      id: 'rice',
      name: 'Paddy Rice',
      category: { id: 'Poaceae', label: 'Poaceae' },
      yieldTonnesPerHectare: 4.5,
      waterPercent: 50,
    },
    timeline: [],
    rotations: [
      {
        id: 'rice__mungbean__sesame',
        name: 'Paddy Rice → Mungbean → Sesame',
        rank: 1,
        score: 90,
        ease_adjusted_score: 78,
        rating: 'Optimal',
        is_custom: false,
        filter_scores: {
          default: 90,
          water: 72,
          soil: 86,
          pest: 88,
          ease: 78,
        },
        timeline: {
          feasible: true,
          turnaround_summary: { buffer_days: 10, status: 'good', advisory: '10d prep' },
          slots: [
            {
              crop_id: 'rice',
              crop_name: 'Paddy Rice',
              family: 'Poaceae',
              sowing_date: '2026-11-15',
              harvest_nominal_date: '2027-02-20',
            },
            {
              crop_id: 'mungbean',
              crop_name: 'Mungbean',
              family: 'Fabaceae',
              sowing_date: '2027-03-02',
              harvest_nominal_date: '2027-05-20',
            },
            {
              crop_id: 'sesame',
              crop_name: 'Sesame',
              family: 'Pedaliaceae',
              sowing_date: '2027-06-01',
              harvest_nominal_date: '2027-08-30',
            },
          ],
        },
      },
      {
        id: 'custom_maize_groundnut_potato',
        name: 'Maize → Groundnut → Potato',
        rank: 2,
        score: 82,
        ease_adjusted_score: 85,
        rating: 'Good',
        is_custom: true,
        components: {
          climate_suitability: 35,
          transition_synergy: 24,
        },
        easiness_matrix: {
          easiness_tier: 'Easy',
          easiness_score: 85,
          factors: {
            water_irrigation_dependency: 1.5,
            soil_nutrient_intervention: 2.0,
            pest_pathogen_vigilance: 3.0,
          },
        },
        custom_comparison: {
          gap_pts: -8,
          reason: 'Lower seasonal climate fit than #1 regional plan',
        },
        smart_swap: {
          replace_crop_id: 'potato',
          replace_crop_name: 'Potato',
          with_crop_id: 'cowpea',
          with_crop_name: 'Cowpea',
          gain_pts: 6.5,
          reason: 'Fixes soil nitrogen',
        },
        timeline: {
          feasible: true,
          turnaround_summary: { buffer_days: 18, status: 'optimal', advisory: '18d buffer' },
          slots: [
            {
              crop_id: 'maize',
              crop_name: 'Maize',
              family: 'Poaceae',
              sowing_date: '2026-11-15',
              harvest_nominal_date: '2027-02-25',
            },
            {
              crop_id: 'groundnut',
              crop_name: 'Groundnut',
              family: 'Fabaceae',
              sowing_date: '2027-03-15',
              harvest_nominal_date: '2027-06-20',
            },
            {
              crop_id: 'potato',
              crop_name: 'Potato',
              family: 'Solanaceae',
              sowing_date: '2027-07-08',
              harvest_nominal_date: '2027-10-15',
            },
          ],
        },
      },
      {
        id: 'custom_fallback_no_reason',
        name: 'Maize → Sorghum',
        rank: 3,
        score: 74,
        rating: 'Fair',
        is_custom: true,
        filter_scores: {
          default: 74,
          water: 60,
          soil: 55,
          pest: 50,
          ease: 68,
        },
        timeline: {
          feasible: true,
          slots: [
            {
              crop_id: 'maize',
              crop_name: 'Maize',
              family: 'Poaceae',
              sowing_date: '2026-11-15',
              harvest_nominal_date: '2027-02-25',
            },
            {
              crop_id: 'sorghum',
              crop_name: 'Sorghum',
              family: 'Poaceae',
              sowing_date: '2027-03-15',
              harvest_nominal_date: '2027-06-20',
            },
          ],
        },
      },
    ],
  });

  const plan = mapPlan(dto);
  expect(plan).not.toBeNull();
  const rotations = plan!.rotations;
  expect(rotations[0].isCustom).toBe(false);
  expect(rotations[0].filterScores).toEqual({
    default: 90,
    water: 72,
    soil: 86,
    pest: 88,
    ease: 78,
  });

  // Fallback filterScores computed from components & easiness_matrix.factors
  // water: (10 - 1.5) * 7 + 35 * 0.8 = 59.5 + 28 = 87.5 -> 88
  // soil: (10 - 2.0) * 7 + 24 = 56 + 24 = 80
  // pest: (10 - 3.0) * 7 + 24 = 49 + 24 = 73
  expect(rotations[1].isCustom).toBe(true);
  expect(rotations[1].filterScores).toEqual({
    default: 82,
    water: 88,
    soil: 80,
    pest: 73,
    ease: 85,
  });
  expect(rotations[1].customComparison).toEqual({
    gapPts: -8,
    reason: 'Lower seasonal climate fit than #1 regional plan',
  });
  expect(rotations[1].smartSwap).toEqual({
    replaceCropId: 'potato',
    replaceCropName: 'Potato',
    withCropId: 'cowpea',
    withCropName: 'Cowpea',
    gainPts: 6.5,
    reason: 'Fixes soil nitrogen',
  });

  // Default filter keeps regional #1 on top and updates customComparison
  const rankedDefault = rankRotationsByFilter(rotations, 'default');
  expect(rankedDefault.map((r) => r.id)).toEqual([
    'rice__mungbean__sesame',
    'custom_maize_groundnut_potato',
    'custom_fallback_no_reason',
  ]);
  expect(rankedDefault[0]).toMatchObject({ rank: 1, isBest: true, score: 90, badge: 'Highest yield & fit' });
  expect(rankedDefault[1]).toMatchObject({
    rank: 2,
    isBest: false,
    score: 82,
    badge: 'Custom rotation',
    customComparison: { gapPts: -8, reason: 'Lower seasonal climate fit than #1 regional plan' },
  });
  expect(rankedDefault[2].customComparison).toEqual({
    gapPts: -16,
    reason: '-16 pts vs #1 Paddy Rice plan',
  });

  // Water filter promotes custom_maize_groundnut_potato (88) to #1
  const rankedWater = rankRotationsByFilter(rotations, 'water');
  expect(rankedWater[0].id).toBe('custom_maize_groundnut_potato');
  expect(rankedWater[0]).toMatchObject({
    rank: 1,
    isBest: true,
    score: 88,
    badge: 'Low water · Rainfed safe',
    customComparison: {
      gapPts: 0,
      reason: '★ #1 Best choice for water in this region',
    },
  });
  expect(rankedWater[1]).toMatchObject({
    rank: 2,
    isBest: false,
    score: 72,
    badge: 'Moderate water use',
  });

  // Ease filter uses turnaround_summary.buffer_days in badge
  const rankedEase = rankRotationsByFilter(rotations, 'ease');
  expect(rankedEase[0].id).toBe('custom_maize_groundnut_potato');
  expect(rankedEase[0].badge).toBe('18d buffer · Easy prep');
  expect(rankedEase[1].badge).toBe('10d buffer · Easy prep');
  expect(rankedEase[2].badge).toBe('14d buffer · Easy prep');

  // Empty array returns empty
  expect(rankRotationsByFilter([], 'soil')).toEqual([]);
});
