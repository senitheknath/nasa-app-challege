import { z } from 'zod';
import { strings } from '@/i18n/strings';
import { formatDate, formatNumber, formatUnit, parseCalendarDate } from '@/utils/format';
import { fieldSchema } from '../area/model';
import { cropSchema, mapCrop, type Crop } from '../crop/model';

export const planRequestSchema = fieldSchema.extend({
  strategyId: z.string().min(1),
  cropId: z.string().min(1).optional(),
  sowingDate: z.iso.date().refine((value) => parseCalendarDate(value) !== null),
  latitude: z.number().optional(),
  longitude: z.number().optional(),
  boundary: z.array(z.object({ latitude: z.number(), longitude: z.number() })).optional(),
  areaHa: z.number().nullable().optional(),
  irrigation: z.enum(['rainfed', 'irrigated']).optional(),
});

export const stageSchema = z.object({
  stage: z.string(),
  description: z.string().optional(),
  start_date: z.string(),
  end_date: z.string(),
  duration_days: z.number(),
});

export const slotSchema = z.object({
  crop_id: z.string(),
  crop_name: z.string(),
  family: z.string().optional(),
  window: z.string().optional(),
  sowing_date: z.string(),
  harvest_nominal_date: z.string(),
  harvest_window: z.string().optional(),
  growth_cycle_days: z.object({
    minimum: z.number(),
    nominal: z.number(),
    maximum: z.number(),
  }).optional(),
  stages: z.array(stageSchema).optional(),
  kc_max: z.number().optional(),
  delay_slack_days: z.number().optional(),
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
  sowingDate: z.string().optional(),
  harvestDate: z.string().optional(),
  harvestWindow: z.string().optional(),
  family: z.string().optional(),
  growthDays: z.string().optional(),
  stages: z.array(stageSchema).optional(),
  turnaroundBufferDays: z.number().nullable().optional(),
  delaySlackDays: z.number().optional(),
  safeExpiryDate: z.string().nullable().optional(),
  hardExpiryDate: z.string().nullable().optional(),
  collisionProbabilityPct: z.number().nullable().optional(),
  kcMax: z.number().optional(),
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

function mapSlot(slot: SlotDto): MappedSlot {
  const sowingDate = formatDate(slot.sowing_date);
  const harvestDate = formatDate(slot.harvest_nominal_date);
  const growthDays = slot.growth_cycle_days
    ? `${slot.growth_cycle_days.nominal}d (${slot.growth_cycle_days.minimum}–${slot.growth_cycle_days.maximum}d)`
    : undefined;
  return {
    cropId: slot.crop_id,
    cropName: slot.crop_name,
    family: slot.family,
    window: slot.window,
    sowingDate,
    harvestDate,
    dateSpan: `${sowingDate} → ${harvestDate}`,
    harvestWindow: slot.harvest_window,
    growthDays,
    stages: mapStages(slot.stages),
    kcMax: slot.kc_max,
    delaySlackDays: slot.delay_slack_days,
    turnaroundBufferDays: slot.turnaround_buffer_after_days ?? undefined,
    safeExpiryDate: slot.safe_expiry_date ? formatDate(slot.safe_expiry_date) : undefined,
    hardExpiryDate: slot.hard_expiry_date ? formatDate(slot.hard_expiry_date) : undefined,
    daysUntilSafeExpiry: slot.days_until_safe_expiry ?? undefined,
    daysUntilHardExpiry: slot.days_until_hard_expiry ?? undefined,
    collisionProbabilityPct: slot.collision_probability_pct ?? undefined,
  };
}

function mapRotation(rot: RotationOptionDto): RotationOption {
  const tl = rot.timeline;
  const collision = tl.collision_probability_pct ?? tl.uncertainty_cone?.collision_probability_pct ?? undefined;
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
    slots: tl.slots.map(mapSlot),
  };
}

export function mapPlan(dto: PlanDto): Plan | null {
  if (!dto) return null;
  const rotations = (dto.rotations ?? []).map(mapRotation);
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
      harvestWindow: season.harvestWindow,
      family: season.family,
      growthDays: season.growthDays,
      stages: mapStages(season.stages),
      turnaroundBufferDays: season.turnaroundBufferDays ?? undefined,
      delaySlackDays: season.delaySlackDays,
      safeExpiryDate: season.safeExpiryDate ? formatDate(season.safeExpiryDate) : undefined,
      hardExpiryDate: season.hardExpiryDate ? formatDate(season.hardExpiryDate) : undefined,
      collisionProbabilityPct: season.collisionProbabilityPct ?? undefined,
      kcMax: season.kcMax,
    };
  });

  if (!timeline.length && rotations.length > 0 && rotations[0].slots.length > 0) {
    timeline = rotations[0].slots.map((slot, idx) => ({
      id: `${rotations[0].id}-slot-${idx + 1}`,
      season: slot.window || `Slot ${idx + 1}`,
      label: slot.window || `Cycle ${idx + 1}`,
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
