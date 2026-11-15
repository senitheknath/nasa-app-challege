import { z } from 'zod';
import { strings } from '@/i18n/strings';
import { formatDate, formatNumber, formatUnit, parseCalendarDate } from '@/utils/format';
import { fieldSchema } from '../area/model';
import { cropSchema, mapCrop, type Crop } from '../crop/model';

export type RotationFilterId = 'default' | 'water' | 'soil' | 'pest' | 'ease';

export const planRequestSchema = fieldSchema.extend({
  strategyId: z.string().min(1),
  cropId: z.string().min(1).optional(),
  sowingDate: z.iso.date().refine((value) => parseCalendarDate(value) !== null),
  latitude: z.number().optional(),
  longitude: z.number().optional(),
  boundary: z.array(z.object({ latitude: z.number(), longitude: z.number() })).optional(),
  areaHa: z.number().nullable().optional(),
  irrigation: z.enum(['rainfed', 'irrigated']).optional(),
  customCropIds: z.array(z.string()).optional(),
});

export const stageSchema = z.object({
  stage: z.string(),
  description: z.string().optional(),
  start_date: z.string(),
  end_date: z.string(),
  duration_days: z.number(),
});

export const harvestWindowSchema = z.union([
  z.string(),
  z.object({
    early_maturity: z.string().optional(),
    nominal_maturity: z.string().optional(),
    late_maturity: z.string().optional(),
  }),
]);

export const slotSchema = z.object({
  crop_id: z.string(),
  crop_name: z.string(),
  family: z.string().nullable().optional(),
  window: z.string().nullable().optional(),
  sowing_date: z.string(),
  harvest_nominal_date: z.string(),
  harvest_window: harvestWindowSchema.nullable().optional(),
  growth_cycle_days: z.object({
    minimum: z.number(),
    nominal: z.number(),
    maximum: z.number(),
  }).nullable().optional(),
  stages: z.array(stageSchema).nullable().optional(),
  kc_max: z.number().nullable().optional(),
  delay_slack_days: z.number().nullable().optional(),
  turnaround_buffer_after_days: z.number().nullable().optional(),
  safe_expiry_date: z.string().nullable().optional(),
  hard_expiry_date: z.string().nullable().optional(),
  days_until_safe_expiry: z.number().nullable().optional(),
  days_until_hard_expiry: z.number().nullable().optional(),
  collision_probability_pct: z.number().nullable().optional(),
});

export const turnaroundSummarySchema = z.object({
  buffer_days: z.number(),
  status: z.string(),
  advisory: z.string(),
});

export const uncertaintyConeSchema = z.object({
  slot_1_span_days: z.number().optional(),
  slot_2_span_days: z.number().optional(),
  collision_probability_pct: z.number().optional(),
});

export const rotationOptionSchema = z.object({
  id: z.string(),
  name: z.string(),
  rank: z.number(),
  ease_rank: z.number().optional(),
  score: z.number(),
  rating: z.string(),
  overall_status: z.string().optional(),
  summary: z.string().optional(),
  ease_adjusted_score: z.number().optional(),
  is_custom: z.boolean().nullable().optional(),
  filter_scores: z.record(z.string(), z.number()).nullable().optional(),
  custom_comparison: z.object({
    gap_pts: z.number().nullable().optional(),
    reason: z.string().nullable().optional(),
  }).nullable().optional(),
  smart_swap: z.object({
    replace_crop_id: z.string(),
    replace_crop_name: z.string(),
    with_crop_id: z.string(),
    with_crop_name: z.string(),
    gain_pts: z.number(),
    reason: z.string(),
  }).nullable().optional(),
  components: z.object({
    climate_suitability: z.number().nullable().optional(),
    transition_synergy: z.number().nullable().optional(),
  }).passthrough().nullable().optional(),
  transition: z.object({
    status: z.string().nullable().optional(),
    summary: z.string().nullable().optional(),
    benefits: z.array(z.string()).nullable().optional(),
  }).passthrough().nullable().optional(),
  easiness_matrix: z.object({
    easiness_tier: z.string().nullable().optional(),
    easiness_score: z.number().nullable().optional(),
    factors: z.object({
      water_irrigation_dependency: z.number().nullable().optional(),
      soil_nutrient_intervention: z.number().nullable().optional(),
      pest_pathogen_vigilance: z.number().nullable().optional(),
    }).passthrough().nullable().optional(),
  }).passthrough().nullable().optional(),
  timeline: z.object({
    overall_status: z.string().optional(),
    feasible: z.boolean().optional(),
    total_agronomic_score: z.number().optional(),
    safe_expiry_date: z.string().nullable().optional(),
    hard_expiry_date: z.string().nullable().optional(),
    days_until_safe_expiry: z.number().nullable().optional(),
    days_until_hard_expiry: z.number().nullable().optional(),
    collision_probability_pct: z.number().nullable().optional(),
    turnaround_summary: turnaroundSummarySchema.nullable().optional(),
    uncertainty_cone: uncertaintyConeSchema.nullable().optional(),
    slots: z.array(slotSchema),
  }),
});

export const timelineSchema = z.object({
  id: z.string().min(1),
  season: z.string().min(1),
  year: z.number().int(),
  crop: cropSchema,
  note: z.string(),
  sowingDate: z.string().nullable().optional(),
  harvestDate: z.string().nullable().optional(),
  harvestWindow: harvestWindowSchema.nullable().optional(),
  family: z.string().nullable().optional(),
  growthDays: z.string().nullable().optional(),
  stages: z.array(stageSchema).nullable().optional(),
  turnaroundBufferDays: z.number().nullable().optional(),
  delaySlackDays: z.number().nullable().optional(),
  safeExpiryDate: z.string().nullable().optional(),
  hardExpiryDate: z.string().nullable().optional(),
  collisionProbabilityPct: z.number().nullable().optional(),
  kcMax: z.number().nullable().optional(),
});

export const planSchema = z.object({
  hectares: z.number().nonnegative(),
  strategyTag: z.string().min(1),
  mode: z.string().optional(),
  crop: cropSchema,
  timeline: z.array(timelineSchema),
  rotations: z.array(rotationOptionSchema).optional(),
}).nullable();

export type PlanRequestDto = z.infer<typeof planRequestSchema>;
export type PlanDto = z.infer<typeof planSchema>;
export type StageDto = z.infer<typeof stageSchema>;
export type SlotDto = z.infer<typeof slotSchema>;
export type RotationOptionDto = z.infer<typeof rotationOptionSchema>;

export type MappedStage = {
  stage: string;
  label: string;
  description?: string;
  startDate: string;
  endDate: string;
  durationDays: number;
  percent: number;
};

export type MappedSlot = {
  cropId: string;
  cropName: string;
  family?: string;
  window?: string;
  sowingDate: string;
  harvestDate: string;
  dateSpan: string;
  harvestWindow?: string;
  growthDays?: string;
  stages: MappedStage[];
  kcMax?: number;
  delaySlackDays?: number;
  turnaroundBufferDays?: number;
  safeExpiryDate?: string;
  hardExpiryDate?: string;
  daysUntilSafeExpiry?: number;
  daysUntilHardExpiry?: number;
  collisionProbabilityPct?: number;
  order: number;
  status: 'Current' | 'Upcoming' | 'Planned';
  shortSeason: string;
  fullSeason: string;
  actionPrefix: string;
  actionHighlight: string;
  yieldLabel: string;
  waterPercent: number;
  soilBenefit: string;
};

export type RotationOption = {
  id: string;
  name: string;
  rank: number;
  easeRank?: number;
  score: number;
  rating: string;
  overallStatus?: string;
  summary?: string;
  easeAdjustedScore?: number;
  feasible: boolean;
  totalAgronomicScore: number;
  safeExpiryDate?: string;
  hardExpiryDate?: string;
  daysUntilSafeExpiry?: number;
  daysUntilHardExpiry?: number;
  collisionProbabilityPct?: number;
  turnaroundSummary?: {
    bufferDays: number;
    status: string;
    advisory: string;
  };
  uncertaintyCone?: {
    slot1SpanDays?: number;
    slot2SpanDays?: number;
    collisionProbabilityPct?: number;
  };
  slots: MappedSlot[];
  period: string;
  title: string;
  badge: string;
  isBest: boolean;
  cropCount: number;
  totalDays: number;
  isCustom: boolean;
  filterScores: Record<RotationFilterId, number>;
  filterBadges: Record<RotationFilterId, string>;
  customComparison?: { gapPts: number; reason: string };
  smartSwap?: {
    replaceCropId: string;
    replaceCropName: string;
    withCropId: string;
    withCropName: string;
    gainPts: number;
    reason: string;
  };
};

export type PlanSeason = {
  id: string;
  season: string;
  label: string;
  crop: Crop;
  summary: string;
  note: string;
  dateSpan?: string;
  harvestWindow?: string;
  family?: string;
  growthDays?: string;
  stages?: MappedStage[];
  turnaroundBufferDays?: number;
  delaySlackDays?: number;
  safeExpiryDate?: string;
  hardExpiryDate?: string;
  collisionProbabilityPct?: number;
  kcMax?: number;
};

export type Plan = {
  area: string;
  strategy: string;
  mode: string;
  crop: Crop;
  first: PlanSeason;
  nextCrop?: string;
  timeline: PlanSeason[];
  rotations: RotationOption[];
};

const STAGE_LABELS: Record<string, string> = {
  initial: 'Initial',
  init: 'Initial',
  crop_development: 'Canopy',
  development: 'Canopy',
  canopy: 'Canopy',
  dev: 'Canopy',
  mid_season: 'Mid-Season',
  'mid-season': 'Mid-Season',
  mid: 'Mid-Season',
  late_season: 'Ripening',
  'late-season': 'Ripening',
  late: 'Ripening',
  ripening: 'Ripening',
};

function formatStageLabel(raw: string): string {
  const key = raw.trim().toLowerCase().replace(/\s+/g, '_');
  if (STAGE_LABELS[key]) return STAGE_LABELS[key];
  return raw.replace(/_/g, ' ').replace(/\b\w/g, (ch) => ch.toUpperCase());
}

export function mapStages(stages?: readonly StageDto[]): MappedStage[] {
  if (!stages?.length) return [];
  const totalDays = stages.reduce((sum, item) => sum + Math.max(0, item.duration_days), 0);
  return stages.map((item) => ({
    stage: item.stage,
    label: formatStageLabel(item.stage),
    description: item.description,
    startDate: formatDate(item.start_date),
    endDate: formatDate(item.end_date),
    durationDays: item.duration_days,
    percent: totalDays > 0 ? Math.round((item.duration_days / totalDays) * 100) : Math.round(100 / stages.length),
  }));
}

function formatHarvestWindow(value?: z.infer<typeof harvestWindowSchema> | null): string | undefined {
  if (!value) return undefined;
  if (typeof value === 'string') return value || undefined;
  if (value.early_maturity && value.late_maturity) {
    return `${formatDate(value.early_maturity)} – ${formatDate(value.late_maturity)}`;
  }
  const single = value.nominal_maturity ?? value.early_maturity ?? value.late_maturity;
  return single ? formatDate(single) : undefined;
}

const SHORT_MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'] as const;

function formatShortMonth(date: Date): string {
  return SHORT_MONTHS[date.getMonth()];
}

function formatDayMonth(date: Date): string {
  return `${date.getDate()} ${SHORT_MONTHS[date.getMonth()]}`;
}

function formatMonthYear(date: Date): string {
  return `${SHORT_MONTHS[date.getMonth()]} ${date.getFullYear()}`;
}

function getSlotDurationDays(slot: SlotDto, sowDate: Date | null, harvDate: Date | null): number {
  if (slot.growth_cycle_days?.nominal && slot.growth_cycle_days.nominal > 0) {
    return Math.round(slot.growth_cycle_days.nominal);
  }
  if (slot.stages?.length) {
    const stageSum = slot.stages.reduce((sum, stage) => sum + Math.max(0, stage.duration_days), 0);
    if (stageSum > 0) return Math.round(stageSum);
  }
  if (sowDate && harvDate) {
    const diffDays = Math.round((harvDate.getTime() - sowDate.getTime()) / (1000 * 60 * 60 * 24));
    if (diffDays > 0) return diffDays;
  }
  return 95;
}

function deriveSoilBenefit(family?: string | null): string {
  const f = (family ?? '').trim().toLowerCase();
  if (f.includes('fabaceae') || f.includes('legume')) {
    return 'Fixes soil nitrogen';
  }
  if (f.includes('poaceae') || f.includes('cereal') || f.includes('gramineae')) {
    return 'Builds root biomass';
  }
  if (f.includes('brassicaceae') || f.includes('amaryllidaceae') || f.includes('solanaceae')) {
    return 'Breaks pest cycle';
  }
  if (f.includes('convolvulaceae') || f.includes('euphorbiaceae') || f.includes('root') || f.includes('tuber')) {
    return 'Improves soil structure';
  }
  if (f.includes('pedaliaceae') || f.includes('malvaceae') || f.includes('oilseed') || f.includes('asteraceae')) {
    return 'Deep moisture capture';
  }
  return 'Balances soil nutrients';
}

function deriveRotationBadge(slots: readonly SlotDto[], index: number): string {
  if (index === 0) return 'Highest yield & fit';
  const families = slots
    .map((slot) => (slot.family ?? '').trim().toLowerCase())
    .filter(Boolean);
  if (families.some((family) => family.includes('fabaceae') || family.includes('legume'))) {
    return 'Improves nitrogen';
  }
  if (new Set(families).size >= 3) {
    return 'Breaks pest cycle';
  }
  return 'Balanced cycle';
}

function mapSlot(slot: SlotDto, index: number): MappedSlot {
  const sowDate = parseCalendarDate(slot.sowing_date);
  const harvDate = parseCalendarDate(slot.harvest_nominal_date);
  const sowingDate = formatDate(slot.sowing_date);
  const harvestDate = formatDate(slot.harvest_nominal_date);
  const dateSpan = `${sowingDate} → ${harvestDate}`;
  const growthDays = slot.growth_cycle_days
    ? `${slot.growth_cycle_days.nominal}d (${slot.growth_cycle_days.minimum}–${slot.growth_cycle_days.maximum}d)`
    : undefined;
  const order = index + 1;
  const status: MappedSlot['status'] = index === 0 ? 'Current' : index === 1 ? 'Upcoming' : 'Planned';
  const durationDays = getSlotDurationDays(slot, sowDate, harvDate);
  const shortSeason = sowDate && harvDate
    ? `${formatShortMonth(sowDate)} - ${formatShortMonth(harvDate)}`
    : slot.window
      ? slot.window.replace(/\s*\(next year\)/i, '')
      : `Cycle ${order}`;
  const fullSeason = sowDate && harvDate
    ? `${formatDayMonth(sowDate)} – ${formatDayMonth(harvDate)} · ${durationDays}d`
    : (slot.window || dateSpan);
  const actionPrefix = '';
  const actionHighlight = slot.crop_name;
  const waterPercent = slot.kc_max != null
    ? Math.round(Math.min(95, Math.max(25, slot.kc_max * 65)))
    : 55;
  const soilBenefit = deriveSoilBenefit(slot.family);
  return {
    cropId: slot.crop_id,
    cropName: slot.crop_name,
    family: slot.family ?? undefined,
    window: slot.window ?? undefined,
    sowingDate,
    harvestDate,
    dateSpan,
    harvestWindow: formatHarvestWindow(slot.harvest_window),
    growthDays,
    stages: mapStages(slot.stages ?? undefined),
    kcMax: slot.kc_max ?? undefined,
    delaySlackDays: slot.delay_slack_days ?? undefined,
    turnaroundBufferDays: slot.turnaround_buffer_after_days ?? undefined,
    safeExpiryDate: slot.safe_expiry_date ? formatDate(slot.safe_expiry_date) : undefined,
    hardExpiryDate: slot.hard_expiry_date ? formatDate(slot.hard_expiry_date) : undefined,
    daysUntilSafeExpiry: slot.days_until_safe_expiry ?? undefined,
    daysUntilHardExpiry: slot.days_until_hard_expiry ?? undefined,
    collisionProbabilityPct: slot.collision_probability_pct ?? undefined,
    order,
    status,
    shortSeason,
    fullSeason,
    actionPrefix,
    actionHighlight,
    yieldLabel: '4.5 t/ha',
    waterPercent,
    soilBenefit,
  };
}

function mapRotation(rot: RotationOptionDto, index: number): RotationOption {
  const tl = rot.timeline;
  const collision = tl.collision_probability_pct ?? tl.uncertainty_cone?.collision_probability_pct ?? undefined;
  const slots = tl.slots.map((slot, slotIndex) => mapSlot(slot, slotIndex));
  const isBest = index === 0 || rot.rank === 1;
  const cropCount = slots.length;
  const hasExplicitCycleDays = tl.slots.some((slot) => slot.growth_cycle_days?.nominal != null);
  const totalDays = hasExplicitCycleDays
    ? tl.slots.reduce((sum, slot) => sum + (slot.growth_cycle_days?.nominal ?? 95), 0)
    : cropCount * 95;
  const firstSow = tl.slots.length > 0 ? parseCalendarDate(tl.slots[0].sowing_date) : null;
  const lastHarv = tl.slots.length > 0 ? parseCalendarDate(tl.slots[tl.slots.length - 1].harvest_nominal_date) : null;
  const cropUnit = cropCount === 1 ? '1 crop' : `${cropCount} crops`;
  const period = slots.length > 0
    ? (firstSow && lastHarv
      ? `${formatMonthYear(firstSow)} – ${formatMonthYear(lastHarv)} · ${cropUnit}`
      : `${slots[0].sowingDate} – ${slots[slots.length - 1].harvestDate} · ${cropUnit}`)
    : '';
  const title = index === 0 ? 'Best Rotation' : `Alternative ${index + 1}`;
  const badge = rot.is_custom ? 'Custom rotation' : deriveRotationBadge(tl.slots, index);
  const families = tl.slots
    .map((slot) => (slot.family ?? '').trim().toLowerCase())
    .filter(Boolean);
  const hasLegume = families.some((family) => family.includes('fabaceae') || family.includes('legume'));
  const uniqueFamilies = new Set(families);
  const filterScores: Record<RotationFilterId, number> = {
    default: Math.round(rot.filter_scores?.default ?? rot.score),
    water: Math.round(
      rot.filter_scores?.water ??
        Math.min(
          100,
          Math.max(
            40,
            (10 - (rot.easiness_matrix?.factors?.water_irrigation_dependency ?? 3.5)) * 7 +
              (rot.components?.climate_suitability ?? 25) * 0.8,
          ),
        ),
    ),
    soil: Math.round(
      rot.filter_scores?.soil ??
        Math.min(
          100,
          Math.max(
            40,
            (10 - (rot.easiness_matrix?.factors?.soil_nutrient_intervention ?? 3.5)) * 7 +
              (rot.components?.transition_synergy ?? 20),
          ),
        ),
    ),
    pest: Math.round(
      rot.filter_scores?.pest ??
        Math.min(
          100,
          Math.max(
            40,
            (10 - (rot.easiness_matrix?.factors?.pest_pathogen_vigilance ?? 3.0)) * 7 +
              (rot.components?.transition_synergy ?? 20),
          ),
        ),
    ),
    ease: Math.round(rot.filter_scores?.ease ?? rot.ease_adjusted_score ?? rot.score),
  };
  const filterBadges: Record<RotationFilterId, string> = {
    default: rot.is_custom ? 'Custom rotation' : index === 0 ? 'Highest yield & fit' : 'Balanced cycle',
    water: filterScores.water >= 75 ? 'Low water · Rainfed safe' : 'Moderate water use',
    soil: hasLegume ? '+N Fixer · Soil recovery' : 'Balanced nutrients',
    pest: uniqueFamilies.size >= 3 ? '0 shared pests · 3+ families' : 'Family rotation break',
    ease: `${rot.timeline?.turnaround_summary?.buffer_days ?? 14}d buffer · Easy prep`,
  };
  const customComparison = rot.custom_comparison
    ? {
        gapPts: Math.round(rot.custom_comparison.gap_pts ?? 0),
        reason: rot.custom_comparison.reason ?? '',
      }
    : undefined;
  const smartSwap = rot.smart_swap
    ? {
        replaceCropId: rot.smart_swap.replace_crop_id,
        replaceCropName: rot.smart_swap.replace_crop_name,
        withCropId: rot.smart_swap.with_crop_id,
        withCropName: rot.smart_swap.with_crop_name,
        gainPts: rot.smart_swap.gain_pts,
        reason: rot.smart_swap.reason,
      }
    : undefined;
  return {
    id: rot.id,
    name: rot.name,
    rank: rot.rank,
    easeRank: rot.ease_rank,
    score: rot.score,
    rating: rot.rating,
    overallStatus: rot.overall_status ?? tl.overall_status,
    summary: rot.summary,
    easeAdjustedScore: rot.ease_adjusted_score,
    feasible: tl.feasible ?? true,
    totalAgronomicScore: tl.total_agronomic_score ?? rot.score,
    safeExpiryDate: tl.safe_expiry_date ? formatDate(tl.safe_expiry_date) : undefined,
    hardExpiryDate: tl.hard_expiry_date ? formatDate(tl.hard_expiry_date) : undefined,
    daysUntilSafeExpiry: tl.days_until_safe_expiry ?? undefined,
    daysUntilHardExpiry: tl.days_until_hard_expiry ?? undefined,
    collisionProbabilityPct: collision,
    turnaroundSummary: tl.turnaround_summary
      ? {
          bufferDays: tl.turnaround_summary.buffer_days,
          status: tl.turnaround_summary.status,
          advisory: tl.turnaround_summary.advisory,
        }
      : undefined,
    uncertaintyCone: tl.uncertainty_cone
      ? {
          slot1SpanDays: tl.uncertainty_cone.slot_1_span_days,
          slot2SpanDays: tl.uncertainty_cone.slot_2_span_days,
          collisionProbabilityPct: tl.uncertainty_cone.collision_probability_pct,
        }
      : undefined,
    slots,
    period,
    title,
    badge,
    isBest,
    cropCount,
    totalDays,
    isCustom: Boolean(rot.is_custom),
    filterScores,
    filterBadges,
    customComparison,
    smartSwap,
  };
}

export function rankRotationsByFilter(
  rotations: readonly RotationOption[],
  filter: RotationFilterId,
): RotationOption[] {
  if (rotations.length === 0) return [];
  const sorted = [...rotations].sort((a, b) => {
    const diff = b.filterScores[filter] - a.filterScores[filter];
    if (diff !== 0) return diff;
    return b.score - a.score;
  });
  const top = sorted[0];
  return sorted.map((r, idx) => {
    let customComparison = r.customComparison;
    if (r.isCustom) {
      if (idx === 0) {
        customComparison = {
          gapPts: 0,
          reason: `★ #1 Best choice for ${filter === 'default' ? 'overall fit' : filter} in this region`,
        };
      } else {
        customComparison = {
          gapPts: Math.round(r.filterScores[filter] - top.filterScores[filter]),
          reason:
            r.customComparison?.reason ||
            `-${Math.round(top.filterScores[filter] - r.filterScores[filter])} pts vs #1 ${top.slots[0]?.cropName ?? ''} plan`,
        };
      }
    }
    return {
      ...r,
      rank: idx + 1,
      isBest: idx === 0,
      score: r.filterScores[filter],
      badge: r.filterBadges[filter],
      ...(customComparison !== undefined ? { customComparison } : {}),
    };
  });
}

export function mapPlan(dto: PlanDto): Plan | null {
  if (!dto) return null;
  const rotations = (dto.rotations ?? []).map((rot, index) => mapRotation(rot, index));
  const crop = mapCrop(dto.crop);

  let timeline: PlanSeason[] = dto.timeline.map((season) => {
    const seasonCrop = mapCrop(season.crop);
    const sowingDate = season.sowingDate ? formatDate(season.sowingDate) : undefined;
    const harvestDate = season.harvestDate ? formatDate(season.harvestDate) : undefined;
    return {
      id: season.id,
      season: season.season,
      label: season.year ? `${season.season} ${season.year}` : season.season,
      crop: seasonCrop,
      summary: strings.cropSubtitle(seasonCrop.category, seasonCrop.cropYield),
      note: season.note,
      dateSpan: sowingDate && harvestDate ? `${sowingDate} → ${harvestDate}` : undefined,
      harvestWindow: formatHarvestWindow(season.harvestWindow),
      family: season.family ?? undefined,
      growthDays: season.growthDays ?? undefined,
      stages: mapStages(season.stages ?? undefined),
      turnaroundBufferDays: season.turnaroundBufferDays ?? undefined,
      delaySlackDays: season.delaySlackDays ?? undefined,
      safeExpiryDate: season.safeExpiryDate ? formatDate(season.safeExpiryDate) : undefined,
      hardExpiryDate: season.hardExpiryDate ? formatDate(season.hardExpiryDate) : undefined,
      collisionProbabilityPct: season.collisionProbabilityPct ?? undefined,
      kcMax: season.kcMax ?? undefined,
    };
  });

  if (!timeline.length && rotations.length > 0 && rotations[0].slots.length > 0) {
    timeline = rotations[0].slots.map((slot, idx) => ({
      id: `${rotations[0].id}-slot-${idx + 1}`,
      season: slot.window || slot.shortSeason,
      label: slot.window || slot.fullSeason,
      crop: {
        ...crop,
        id: slot.cropId,
        name: slot.cropName,
        category: slot.family ?? crop.category,
      },
      summary: slot.growthDays ? `${slot.family ?? crop.category} · ${slot.growthDays}` : (slot.family ?? crop.category),
      note: slot.turnaroundBufferDays != null
        ? `${formatNumber(slot.turnaroundBufferDays)}d buffer`
        : rotations[0].rating,
      dateSpan: slot.dateSpan,
      harvestWindow: slot.harvestWindow,
      family: slot.family,
      growthDays: slot.growthDays,
      stages: slot.stages,
      turnaroundBufferDays: slot.turnaroundBufferDays,
      delaySlackDays: slot.delaySlackDays,
      safeExpiryDate: slot.safeExpiryDate,
      hardExpiryDate: slot.hardExpiryDate,
      collisionProbabilityPct: slot.collisionProbabilityPct,
      kcMax: slot.kcMax,
    }));
  }

  if (!timeline.length) return null;

  return {
    area: formatUnit(dto.hectares, strings.units.hectares, 1),
    strategy: dto.strategyTag,
    mode: dto.mode ?? (rotations.length > 0 ? 'continuous' : 'standard'),
    crop,
    first: timeline[0],
    nextCrop: rotations[0]?.slots[1]?.cropName ?? timeline[1]?.crop.name,
    timeline,
    rotations,
  };
}
