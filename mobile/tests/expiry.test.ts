import { endpoints } from '@/api/endpoints';
import {
  evaluateRotationExpiry,
  evaluateSlotExpiry,
  explainLiveExpiryShift,
  explainThresholdsPreview,
  formatExpiryCountdown,
} from '@/features/plan/expiryExplain';
import { mapPlan, planRequestSchema, planSchema } from '@/features/plan/model';
import { UNCERTAINTY_PRESETS, usePlanner } from '@/state/usePlanner';

jest.mock('@/api/config', () => ({ useMocks: false, baseUrl: 'https://api.example.test' }));
jest.mock('expo-secure-store', () => ({
  getItemAsync: jest.fn(async () => null),
  setItemAsync: jest.fn(async () => undefined),
  deleteItemAsync: jest.fn(async () => undefined),
}));

afterEach(() => {
  usePlanner.getState().reset();
  jest.restoreAllMocks();
});

test('usePlanner manages uncertainty presets, clamping, custom detection, and country persistence', () => {
  const store = usePlanner.getState();
  expect(store.uncertaintyPreset).toBe('balanced');
  expect(store.expirySafetyDays).toBe(7);
  expect(store.collisionThresholdPct).toBe(25);
  expect(store.weatherVolatility).toBe(0.18);

  store.setUncertaintyPreset('conservative');
  expect(usePlanner.getState()).toMatchObject({
    uncertaintyPreset: 'conservative',
    ...UNCERTAINTY_PRESETS.conservative,
  });

  store.setExpiryThresholds({ expirySafetyDays: 10 });
  expect(usePlanner.getState()).toMatchObject({
    uncertaintyPreset: 'custom',
    expirySafetyDays: 10,
    collisionThresholdPct: 10,
    weatherVolatility: 0.28,
  });

  // Setting values that match 'flexible' snaps preset back to 'flexible'
  store.setExpiryThresholds(UNCERTAINTY_PRESETS.flexible);
  expect(usePlanner.getState().uncertaintyPreset).toBe('flexible');

  // Clamping out-of-range inputs
  store.setExpiryThresholds({
    expirySafetyDays: 99,
    collisionThresholdPct: 2,
    weatherVolatility: 0.99,
  });
  expect(usePlanner.getState()).toMatchObject({
    uncertaintyPreset: 'custom',
    expirySafetyDays: 35,
    collisionThresholdPct: 5,
    weatherVolatility: 0.5,
  });

  // Thresholds survive chooseCountry and reset to balanced on reset()
  store.chooseCountry('KE');
  expect(usePlanner.getState().expirySafetyDays).toBe(35);
  store.reset();
  expect(usePlanner.getState()).toMatchObject({
    uncertaintyPreset: 'balanced',
    expirySafetyDays: 7,
    collisionThresholdPct: 25,
    weatherVolatility: 0.18,
  });
});

test('endpoints.plan forwards expiry_buffer_days and maps uncertaintyCone & turnaroundExpiryPressure', async () => {
  const fetchSpy = jest.spyOn(globalThis, 'fetch').mockResolvedValue({
    status: 200,
    ok: true,
    json: async () => ({
      status: 'ok',
      mode: 'continuous',
      threshold_config: { expiry_buffer_days: 14 },
      rotations: [
        {
          id: 'rice__mungbean__sesame',
          name: 'Paddy Rice → Mungbean → Sesame',
          rank: 1,
          score: 89,
          rating: 'Optimal',
          easiness_matrix: {
            easiness_tier: 'Moderate',
            easiness_score: 7.4,
            factors: {
              turnaround_expiry_pressure: 3.2,
              water_irrigation_dependency: 2.5,
              soil_nutrient_intervention: 2.0,
              pest_pathogen_vigilance: 1.5,
            },
          },
          timeline: {
            feasible: true,
            total_agronomic_score: 89,
            safe_expiry_date: '2026-11-28',
            hard_expiry_date: '2026-12-08',
            days_until_safe_expiry: 13,
            days_until_hard_expiry: 23,
            collision_probability_pct: 12.5,
            turnaround_summary: { buffer_days: 14, status: 'optimal', advisory: 'Clean 14-day prep' },
            slots: [
              {
                crop_id: 'rice',
                crop_name: 'Paddy Rice',
                family: 'Poaceae',
                sowing_date: '2026-11-15',
                harvest_nominal_date: '2027-02-23',
                growth_cycle_days: { minimum: 90, nominal: 100, maximum: 110 },
                delay_slack_days: 23,
                turnaround_buffer_after_days: 14,
                safe_expiry_date: '2026-11-28',
                hard_expiry_date: '2026-12-08',
                days_until_safe_expiry: 13,
                days_until_hard_expiry: 23,
                collision_probability_pct: 12.5,
                uncertainty_cone: {
                  early_end_date: '2027-02-13',
                  nominal_end_date: '2027-02-23',
                  late_end_date: '2027-03-05',
                  span_days: 20,
                },
              },
              {
                crop_id: 'mungbean',
                crop_name: 'Mungbean',
                family: 'Fabaceae',
                sowing_date: '2027-03-09',
                harvest_nominal_date: '2027-05-18',
                growth_cycle_days: { minimum: 65, nominal: 70, maximum: 80 },
                delay_slack_days: 5,
                turnaround_buffer_after_days: 8,
                safe_expiry_date: '2027-03-04',
                hard_expiry_date: '2027-03-14',
                days_until_safe_expiry: -5,
                days_until_hard_expiry: 5,
                collision_probability_pct: 32,
                uncertainty_cone: {
                  early_end_date: '2027-05-13',
                  nominal_end_date: '2027-05-18',
                  late_end_date: '2027-05-28',
                  span_days: 15,
                },
              },
            ],
          },
        },
      ],
    }),
  } as Response);

  const req = planRequestSchema.parse({
    countryId: 'LK',
    points: [{ x: 0, y: 0 }, { x: 20, y: 0 }, { x: 20, y: 10 }],
    strategyId: 'continuous_rainfed',
    cropId: 'rice',
    sowingDate: '2026-11-15',
    expirySafetyDays: 14,
  });

  const dto = await endpoints.plan(req, new AbortController().signal);
  expect(fetchSpy).toHaveBeenCalledTimes(1);
  const sentBody = JSON.parse(String((fetchSpy.mock.calls[0][1] as RequestInit).body));
  expect(sentBody.expiry_buffer_days).toBe(14);

  const mapped = mapPlan(planSchema.parse(dto));
  expect(mapped).not.toBeNull();
  expect(mapped!.thresholdConfig?.expiryBufferDays).toBe(14);
  expect(mapped!.rotations[0].turnaroundExpiryPressure).toBe(3.2);
  expect(mapped!.rotations[0].slots[0].uncertaintyCone).toMatchObject({
    spanDays: 20,
    rawEarlyEndDate: '2027-02-13',
    rawNominalEndDate: '2027-02-23',
    rawLateEndDate: '2027-03-05',
  });
});

test('evaluateSlotExpiry and evaluateRotationExpiry classify urgency and format negative countdowns safely', () => {
  expect(formatExpiryCountdown(-3, 'hard')).toBe('3d overdue');
  expect(formatExpiryCountdown(-3, 'safe')).toBe('3d past safe');
  expect(formatExpiryCountdown(0, 'hard')).toBe('Due today');
  expect(formatExpiryCountdown(14, 'safe')).toBe('14d left');
  expect(formatExpiryCountdown(null, 'safe')).toBe('No fixed cutoff');

  const balanced = UNCERTAINTY_PRESETS.balanced;
  const conservative = UNCERTAINTY_PRESETS.conservative;

  const slot1 = {
    cropName: 'Paddy Rice',
    safeExpiryDate: '28 Nov 2026',
    hardExpiryDate: '8 Dec 2026',
    daysUntilSafeExpiry: 12,
    daysUntilHardExpiry: 22,
    delaySlackDays: 22,
    collisionProbabilityPct: 0,
    growthCycleDays: { minimum: 90, nominal: 100, maximum: 110 },
  };

  // Safe under balanced (7d), tight under conservative (14d)
  const evalBalanced = evaluateSlotExpiry(slot1, balanced, 'Mungbean');
  expect(evalBalanced.urgency).toBe('safe');
  expect(evalBalanced.badgeText).toBe('Safe +12d');
  expect(evalBalanced.explanation).toContain('7d safety turnaround buffer');
  expect(evalBalanced.explanation).toContain('Mungbean');
  expect(evalBalanced.barMetrics.safeZonePct + evalBalanced.barMetrics.cautionZonePct + evalBalanced.barMetrics.criticalZonePct).toBe(100);

  const evalConservative = evaluateSlotExpiry(slot1, conservative, 'Mungbean');
  expect(evalConservative.urgency).toBe('tight');
  expect(evalConservative.badgeText).toBe('Tight 12d');

  // Negative hard expiry days never render "-3d"
  const overdueSlot = {
    cropName: 'Maize',
    daysUntilSafeExpiry: -10,
    daysUntilHardExpiry: -3,
    collisionProbabilityPct: 45,
  };
  const evalOverdue = evaluateSlotExpiry(overdueSlot, balanced, 'Sesame');
  expect(evalOverdue.urgency).toBe('critical');
  expect(evalOverdue.badgeText).toBe('Overdue 3d');
  expect(evalOverdue.countdownLabel).toBe('3d overdue');
  expect(evalOverdue.countdownLabel).not.toContain('-3');

  // Rotation evaluation catches worst slot collision (e.g. Slot 2 = 32% >= 25% balanced threshold)
  const rotEval = evaluateRotationExpiry(
    {
      name: 'Rice → Mungbean → Sesame',
      daysUntilSafeExpiry: 13,
      daysUntilHardExpiry: 23,
      collisionProbabilityPct: 12,
      turnaroundExpiryPressure: 4.1,
      turnaroundSummary: { bufferDays: 14, status: 'optimal', advisory: '14d buffer' },
      slots: [
        { daysUntilSafeExpiry: 13, daysUntilHardExpiry: 23, collisionProbabilityPct: 12 },
        { daysUntilSafeExpiry: 4, daysUntilHardExpiry: 14, collisionProbabilityPct: 32 },
      ],
    },
    balanced,
  );
  expect(rotEval.urgency).toBe('critical');
  expect(rotEval.collisionPct).toBe(32);
  expect(rotEval.pressureLabel).toBe('Moderate expiry pressure (4.1/10)');
});

test('explainLiveExpiryShift and explainThresholdsPreview produce clear plain-English guidance', () => {
  const liveEval = explainLiveExpiryShift(
    {
      t_now_day: 42,
      growth_lag_days: 5,
      safe_expiry_date: '2026-12-20',
      hard_expiry_date: '2026-12-28',
      days_until_safe_expiry: -2,
      days_until_hard_expiry: 6,
      sigma_at_harvest_days: 5.4,
    },
    UNCERTAINTY_PRESETS.balanced,
  );
  expect(liveEval.urgency).toBe('tight');
  expect(liveEval.lagDirection).toBe('behind');
  expect(liveEval.safeCountdownLabel).toBe('2d past safe');
  expect(liveEval.hardCountdownLabel).toBe('6d left');
  expect(liveEval.explanation).toContain('5d slower than nominal');
  expect(liveEval.explanation).toContain('σ=0.18');

  const preview = explainThresholdsPreview(UNCERTAINTY_PRESETS.conservative);
  expect(preview.summary).toContain('14d safety buffer');
  expect(preview.collisionDetail).toContain('10%');
  expect(preview.volatilityDetail).toContain('0.28');
});
