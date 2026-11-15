import { formatDate, parseCalendarDate } from '@/utils/format';

export type ExpiryThresholds = {
  expirySafetyDays: number;
  collisionThresholdPct: number;
  weatherVolatility: number;
};

export type ExpiryUrgency = 'safe' | 'tight' | 'critical';

export type ExpirySlotInput = {
  cropName?: string;
  sowingDate?: string;
  harvestDate?: string;
  rawSowingDate?: string;
  rawHarvestDate?: string;
  safeExpiryDate?: string;
  hardExpiryDate?: string;
  rawSafeExpiryDate?: string;
  rawHardExpiryDate?: string;
  daysUntilSafeExpiry?: number | null;
  daysUntilHardExpiry?: number | null;
  delaySlackDays?: number | null;
  turnaroundBufferDays?: number | null;
  collisionProbabilityPct?: number | null;
  growthDays?: string;
  growthCycleDays?: { minimum: number; nominal: number; maximum: number } | null;
  uncertaintyCone?: {
    earlyEndDate?: string;
    nominalEndDate?: string;
    lateEndDate?: string;
    spanDays?: number;
    rawEarlyEndDate?: string;
    rawNominalEndDate?: string;
    rawLateEndDate?: string;
  } | null;
};

export type ExpiryBarMetrics = {
  hasDates: boolean;
  safeZonePct: number;
  cautionZonePct: number;
  criticalZonePct: number;
  safeMarkerPct: number;
  hardMarkerPct: number;
  earlyMarkerPct: number;
  nominalMarkerPct: number;
  lateMarkerPct: number;
  uncertaintySpanDays: number;
};

export type SlotExpiryEvaluation = {
  urgency: ExpiryUrgency;
  badgeText: string;
  countdownLabel: string;
  safeCountdownLabel: string;
  hardCountdownLabel: string;
  collisionLabel: string;
  slackLabel: string;
  headline: string;
  explanation: string;
  thresholdNote: string;
  barMetrics: ExpiryBarMetrics;
};

export type ExpiryRotationInput = {
  name?: string;
  daysUntilSafeExpiry?: number | null;
  daysUntilHardExpiry?: number | null;
  safeExpiryDate?: string;
  hardExpiryDate?: string;
  collisionProbabilityPct?: number | null;
  turnaroundExpiryPressure?: number | null;
  turnaroundSummary?: {
    bufferDays: number;
    status: string;
    advisory: string;
  } | null;
  slots?: readonly ExpirySlotInput[];
};

export type RotationExpiryEvaluation = {
  urgency: ExpiryUrgency;
  badgeText: string;
  shortPill: string;
  collisionPct: number;
  minDaysUntilSafeExpiry?: number;
  minDaysUntilHardExpiry?: number;
  pressureScore?: number;
  pressureLabel?: string;
  headline: string;
  advisory: string;
};

export type LiveExpiryInput = {
  t_now_day: number;
  current_date?: string;
  growth_lag_days: number;
  active_stage?: string;
  expected_ndvi?: number;
  observed_ndvi?: number | null;
  safe_expiry_date?: string | null;
  hard_expiry_date?: string | null;
  days_until_safe_expiry?: number | null;
  days_until_hard_expiry?: number | null;
  sigma_at_harvest_days: number;
};

export type LiveExpiryShiftEvaluation = {
  urgency: ExpiryUrgency;
  lagDirection: 'ahead' | 'on_schedule' | 'behind';
  lagSummary: string;
  volatilitySummary: string;
  safeCountdownLabel: string;
  hardCountdownLabel: string;
  headline: string;
  explanation: string;
};

export type ThresholdPreviewExplanation = {
  summary: string;
  bufferDetail: string;
  collisionDetail: string;
  volatilityDetail: string;
};

function clampPct(value: number): number {
  if (!Number.isFinite(value)) return 0;
  return Math.max(0, Math.min(100, Math.round(value)));
}

/**
 * Formats day countdowns without confusing negative signs (e.g. "-3d" -> "3d overdue").
 */
export function formatExpiryCountdown(
  days: number | null | undefined,
  kind: 'safe' | 'hard' = 'safe',
): string {
  if (days === null || days === undefined || !Number.isFinite(days)) {
    return 'No fixed cutoff';
  }
  const rounded = Math.round(days);
  if (rounded < 0) {
    const overdue = Math.abs(rounded);
    return kind === 'hard' ? `${overdue}d overdue` : `${overdue}d past safe`;
  }
  if (rounded === 0) {
    return 'Due today';
  }
  return `${rounded}d left`;
}

function parseCycleBounds(slot: ExpirySlotInput): {
  minimum?: number;
  nominal?: number;
  maximum?: number;
  spanDays: number;
} {
  if (slot.growthCycleDays) {
    const { minimum, nominal, maximum } = slot.growthCycleDays;
    return {
      minimum,
      nominal,
      maximum,
      spanDays: slot.uncertaintyCone?.spanDays ?? Math.max(0, maximum - minimum),
    };
  }

  if (slot.growthDays) {
    const parenMatch = /(\d+)d\s*\((\d+)[–-](\d+)d\)/i.exec(slot.growthDays);
    if (parenMatch) {
      const nominal = Number(parenMatch[1]);
      const minimum = Number(parenMatch[2]);
      const maximum = Number(parenMatch[3]);
      return {
        minimum,
        nominal,
        maximum,
        spanDays: slot.uncertaintyCone?.spanDays ?? Math.max(0, maximum - minimum),
      };
    }
    const rangeMatch = /(\d+)[–-](\d+)d/i.exec(slot.growthDays);
    if (rangeMatch) {
      const minimum = Number(rangeMatch[1]);
      const maximum = Number(rangeMatch[2]);
      const nomMatch = /nom\s*(\d+)d/i.exec(slot.growthDays);
      const nominal = nomMatch ? Number(nomMatch[1]) : Math.round((minimum + maximum) / 2);
      return {
        minimum,
        nominal,
        maximum,
        spanDays: slot.uncertaintyCone?.spanDays ?? Math.max(0, maximum - minimum),
      };
    }
  }

  const sow = slot.rawSowingDate ? parseCalendarDate(slot.rawSowingDate) : null;
  const early = slot.uncertaintyCone?.rawEarlyEndDate
    ? parseCalendarDate(slot.uncertaintyCone.rawEarlyEndDate)
    : null;
  const nom = slot.uncertaintyCone?.rawNominalEndDate
    ? parseCalendarDate(slot.uncertaintyCone.rawNominalEndDate)
    : null;
  const late = slot.uncertaintyCone?.rawLateEndDate
    ? parseCalendarDate(slot.uncertaintyCone.rawLateEndDate)
    : null;

  const msPerDay = 1000 * 60 * 60 * 24;
  if (sow && early && late) {
    const minimum = Math.round((early.getTime() - sow.getTime()) / msPerDay);
    const maximum = Math.round((late.getTime() - sow.getTime()) / msPerDay);
    const nominal = nom ? Math.round((nom.getTime() - sow.getTime()) / msPerDay) : Math.round((minimum + maximum) / 2);
    return {
      minimum,
      nominal,
      maximum,
      spanDays: slot.uncertaintyCone?.spanDays ?? Math.max(0, maximum - minimum),
    };
  }

  return {
    spanDays: Math.max(0, Math.round(slot.uncertaintyCone?.spanDays ?? 0)),
  };
}

function buildBarMetrics(
  slot: ExpirySlotInput,
  cycle: { minimum?: number; nominal?: number; maximum?: number; spanDays: number },
): ExpiryBarMetrics {
  const daysSafe = slot.daysUntilSafeExpiry;
  const daysHard = slot.daysUntilHardExpiry;
  const hasDates = daysSafe !== null && daysSafe !== undefined || daysHard !== null && daysHard !== undefined;

  let safeZonePct = 70;
  let cautionZonePct = 20;
  let criticalZonePct = 10;

  if (hasDates) {
    const safeVal = daysSafe ?? daysHard ?? 0;
    const hardVal = daysHard ?? safeVal;
    const safeSpan = Math.max(0, safeVal);
    const hardSpan = Math.max(safeSpan, hardVal);
    const cautionSpan = Math.max(0, hardSpan - safeSpan);
    const tailSpan = Math.max(4, Math.round(Math.max(hardSpan, 14) * 0.18));
    const totalRunway = Math.max(1, hardSpan + tailSpan);

    safeZonePct = clampPct((safeSpan / totalRunway) * 100);
    cautionZonePct = clampPct((cautionSpan / totalRunway) * 100);
    if (safeZonePct + cautionZonePct > 100) {
      cautionZonePct = Math.max(0, 100 - safeZonePct);
    }
    criticalZonePct = Math.max(0, 100 - safeZonePct - cautionZonePct);
  }

  const safeMarkerPct = safeZonePct;
  const hardMarkerPct = clampPct(safeZonePct + cautionZonePct);

  let earlyMarkerPct = 20;
  let nominalMarkerPct = 50;
  let lateMarkerPct = 80;
  if (
    cycle.minimum !== undefined &&
    cycle.nominal !== undefined &&
    cycle.maximum !== undefined &&
    cycle.maximum > cycle.minimum
  ) {
    earlyMarkerPct = 15;
    lateMarkerPct = 85;
    nominalMarkerPct = clampPct(
      15 + ((cycle.nominal - cycle.minimum) / (cycle.maximum - cycle.minimum)) * 70,
    );
  }

  return {
    hasDates,
    safeZonePct,
    cautionZonePct,
    criticalZonePct,
    safeMarkerPct,
    hardMarkerPct,
    earlyMarkerPct,
    nominalMarkerPct,
    lateMarkerPct,
    uncertaintySpanDays: cycle.spanDays,
  };
}

/**
 * Evaluates a single crop slot against the user's configured expiry & collision thresholds
 * and produces plain-English explanations and visual timeline bar metrics.
 */
export function evaluateSlotExpiry(
  slot: ExpirySlotInput,
  thresholds: ExpiryThresholds,
  nextCropName?: string,
): SlotExpiryEvaluation {
  const collisionPct = Math.max(0, Math.round((slot.collisionProbabilityPct ?? 0) * 10) / 10);
  const daysSafe = slot.daysUntilSafeExpiry ?? null;
  const daysHard = slot.daysUntilHardExpiry ?? null;
  const cycle = parseCycleBounds(slot);
  const barMetrics = buildBarMetrics(slot, cycle);

  const isCritical =
    (daysHard !== null && daysHard <= 0) ||
    collisionPct >= thresholds.collisionThresholdPct;

  const isTight =
    !isCritical &&
    ((daysSafe !== null && (daysSafe < thresholds.expirySafetyDays || daysSafe <= 0)) ||
      collisionPct > 0);

  const urgency: ExpiryUrgency = isCritical ? 'critical' : isTight ? 'tight' : 'safe';

  const safeCountdownLabel = formatExpiryCountdown(daysSafe, 'safe');
  const hardCountdownLabel = formatExpiryCountdown(daysHard, 'hard');
  const countdownLabel =
    daysHard !== null && daysHard <= 0
      ? hardCountdownLabel
      : daysSafe !== null
        ? safeCountdownLabel
        : hardCountdownLabel;

  let badgeText: string;
  if (daysHard !== null && daysHard < 0) {
    badgeText = `Overdue ${Math.abs(Math.round(daysHard))}d`;
  } else if (daysHard !== null && daysHard === 0) {
    badgeText = 'Cutoff today';
  } else if (urgency === 'critical' && collisionPct >= thresholds.collisionThresholdPct) {
    badgeText = `Risk ${Math.round(collisionPct)}%`;
  } else if (urgency === 'tight') {
    if (daysSafe !== null && daysSafe < 0) {
      badgeText = `${Math.abs(Math.round(daysSafe))}d past safe`;
    } else if (daysSafe !== null && daysSafe === 0) {
      badgeText = 'Safe today';
    } else if (daysSafe !== null) {
      badgeText = `Tight ${Math.round(daysSafe)}d`;
    } else {
      badgeText = `Risk ${Math.round(collisionPct)}%`;
    }
  } else if (daysSafe !== null && daysSafe > 0) {
    badgeText = `Safe +${Math.round(daysSafe)}d`;
  } else {
    badgeText = 'Safe';
  }

  const collisionLabel = `${Math.round(collisionPct)}% collision risk`;
  const slackLabel =
    slot.delaySlackDays != null
      ? slot.delaySlackDays > 0
        ? `${Math.round(slot.delaySlackDays)}d delay slack`
        : '0d delay slack'
      : 'Flexible slack';

  const nextTarget = nextCropName ? nextCropName : 'the next season';

  let headline: string;
  if (urgency === 'critical') {
    if (daysHard !== null && daysHard <= 0) {
      headline = `Critical: ${hardCountdownLabel} — harvest overlaps ${nextTarget}`;
    } else {
      headline = `Critical: ${Math.round(collisionPct)}% harvest collision risk (≥ ${thresholds.collisionThresholdPct}% alert)`;
    }
  } else if (urgency === 'tight') {
    if (daysSafe !== null && daysSafe <= 0) {
      headline = `Caution zone: ${safeCountdownLabel} — slow weather risks delaying ${nextTarget}`;
    } else if (daysSafe !== null && daysSafe < thresholds.expirySafetyDays) {
      headline = `Tight margin: ${Math.round(daysSafe)}d to safe cutoff (below ${thresholds.expirySafetyDays}d buffer)`;
    } else {
      headline = `Tight margin: ${Math.round(collisionPct)}% overlap risk if maturity runs late`;
    }
  } else if (daysSafe !== null) {
    headline = `Safe window: ${Math.round(daysSafe)}d runway before safe cutoff`;
  } else {
    headline = 'Safe window: ample time before follow-up planting';
  }

  const cycleSpanDesc =
    cycle.minimum !== undefined && cycle.maximum !== undefined
      ? `a ${cycle.minimum}–${cycle.maximum}d maturity spread`
      : cycle.spanDays > 0
        ? `a ${cycle.spanDays}d harvest uncertainty spread`
        : 'normal seasonal maturity spread';

  const safeDateText = slot.safeExpiryDate ? ` (${slot.safeExpiryDate})` : '';
  const hardDateText = slot.hardExpiryDate ? ` (${slot.hardExpiryDate})` : '';
  const cropLabel = slot.cropName || 'This crop';

  const explanationParts: string[] = [
    `${cropLabel} has ${cycleSpanDesc} plus your ${thresholds.expirySafetyDays}d safety turnaround buffer before ${nextTarget}.`,
    `Safe Expiry${safeDateText} assumes slow maturity, so planting or finishing by then keeps harvest out of ${nextTarget}'s prep window.`,
    `Hard Expiry${hardDateText} uses nominal maturity; slipping past it removes turnaround cushion and triggers ${Math.round(collisionPct)}% collision risk (alert threshold: ${thresholds.collisionThresholdPct}%).`,
  ];

  const thresholdNote = `Active thresholds: ${thresholds.expirySafetyDays}d safety buffer · ${thresholds.collisionThresholdPct}% collision alert · σ=${thresholds.weatherVolatility.toFixed(2)}`;

  return {
    urgency,
    badgeText,
    countdownLabel,
    safeCountdownLabel,
    hardCountdownLabel,
    collisionLabel,
    slackLabel,
    headline,
    explanation: explanationParts.join(' '),
    thresholdNote,
    barMetrics,
  };
}

/**
 * Evaluates overall expiry & collision risk across a multi-crop rotation option.
 */
export function evaluateRotationExpiry(
  rotation: ExpiryRotationInput,
  thresholds: ExpiryThresholds,
): RotationExpiryEvaluation {
  const slots = rotation.slots ?? [];
  const slotCollisions = slots
    .map((s) => s.collisionProbabilityPct)
    .filter((v): v is number => typeof v === 'number' && Number.isFinite(v));
  const collisionPct = Math.max(
    0,
    Math.round(
      Math.max(rotation.collisionProbabilityPct ?? 0, ...slotCollisions) * 10,
    ) / 10,
  );

  const safeCandidates = [
    rotation.daysUntilSafeExpiry,
    ...slots.map((s) => s.daysUntilSafeExpiry),
  ].filter((v): v is number => typeof v === 'number' && Number.isFinite(v));

  const hardCandidates = [
    rotation.daysUntilHardExpiry,
    ...slots.map((s) => s.daysUntilHardExpiry),
  ].filter((v): v is number => typeof v === 'number' && Number.isFinite(v));

  const minDaysUntilSafeExpiry = safeCandidates.length > 0 ? Math.min(...safeCandidates) : undefined;
  const minDaysUntilHardExpiry = hardCandidates.length > 0 ? Math.min(...hardCandidates) : undefined;

  const turnaroundStatus = rotation.turnaroundSummary?.status?.toLowerCase();
  const isCritical =
    (minDaysUntilHardExpiry !== undefined && minDaysUntilHardExpiry <= 0) ||
    collisionPct >= thresholds.collisionThresholdPct ||
    turnaroundStatus === 'collision';

  const isTight =
    !isCritical &&
    ((minDaysUntilSafeExpiry !== undefined &&
      (minDaysUntilSafeExpiry < thresholds.expirySafetyDays || minDaysUntilSafeExpiry <= 0)) ||
      collisionPct > 0 ||
      turnaroundStatus === 'tight');

  const urgency: ExpiryUrgency = isCritical ? 'critical' : isTight ? 'tight' : 'safe';

  const shortPill =
    urgency === 'critical'
      ? minDaysUntilHardExpiry !== undefined && minDaysUntilHardExpiry <= 0
        ? formatExpiryCountdown(minDaysUntilHardExpiry, 'hard')
        : `Risk ${Math.round(collisionPct)}%`
      : urgency === 'tight'
        ? minDaysUntilSafeExpiry !== undefined && minDaysUntilSafeExpiry > 0
          ? `Tight ${Math.round(minDaysUntilSafeExpiry)}d`
          : `Risk ${Math.round(collisionPct)}%`
        : minDaysUntilSafeExpiry !== undefined && minDaysUntilSafeExpiry > 0
          ? `Safe +${Math.round(minDaysUntilSafeExpiry)}d`
          : 'Safe';

  const badgeText =
    urgency === 'critical'
      ? minDaysUntilHardExpiry !== undefined && minDaysUntilHardExpiry <= 0
        ? `${formatExpiryCountdown(minDaysUntilHardExpiry, 'hard')} · ${Math.round(collisionPct)}% risk`
        : `Critical · ${Math.round(collisionPct)}% collision`
      : urgency === 'tight'
        ? minDaysUntilSafeExpiry !== undefined && minDaysUntilSafeExpiry > 0
          ? `Tight +${Math.round(minDaysUntilSafeExpiry)}d · ${Math.round(collisionPct)}% risk`
          : `Tight · ${Math.round(collisionPct)}% risk`
        : minDaysUntilSafeExpiry !== undefined && minDaysUntilSafeExpiry > 0
          ? `Safe +${Math.round(minDaysUntilSafeExpiry)}d · ${Math.round(collisionPct)}% risk`
          : `Safe · ${Math.round(collisionPct)}% risk`;

  const pressureScore =
    rotation.turnaroundExpiryPressure !== null && rotation.turnaroundExpiryPressure !== undefined
      ? Number(rotation.turnaroundExpiryPressure.toFixed(1))
      : undefined;

  const pressureLabel =
    pressureScore !== undefined
      ? pressureScore <= 2.5
        ? `Low expiry pressure (${pressureScore.toFixed(1)}/10)`
        : pressureScore <= 5.5
          ? `Moderate expiry pressure (${pressureScore.toFixed(1)}/10)`
          : `High expiry pressure (${pressureScore.toFixed(1)}/10)`
      : undefined;

  const bufferDays = rotation.turnaroundSummary?.bufferDays;
  const bufferNote =
    bufferDays !== undefined
      ? `${bufferDays}d planned turnaround between slots`
      : `${thresholds.expirySafetyDays}d safety buffer applied`;

  let headline: string;
  if (urgency === 'critical') {
    headline = `High rotation expiry risk (${Math.round(collisionPct)}% peak collision)`;
  } else if (urgency === 'tight') {
    headline = `Tight rotation transitions — monitor harvest timing closely`;
  } else {
    headline = `Smooth transitions — stays inside your ${thresholds.expirySafetyDays}d safety margin`;
  }

  const advisoryParts: string[] = [
    rotation.turnaroundSummary?.advisory || bufferNote,
    `Peak slot collision risk is ${Math.round(collisionPct)}% against your ${thresholds.collisionThresholdPct}% alert threshold.`,
  ];
  if (pressureLabel) {
    advisoryParts.push(`${pressureLabel}.`);
  }

  return {
    urgency,
    badgeText,
    shortPill,
    collisionPct,
    minDaysUntilSafeExpiry,
    minDaysUntilHardExpiry,
    pressureScore,
    pressureLabel,
    headline,
    advisory: advisoryParts.join(' '),
  };
}

/**
 * Explains how live NDVI growth lag and configured weather volatility shift Safe/Hard expiry in Live Monitor.
 */
export function explainLiveExpiryShift(
  liveState: LiveExpiryInput,
  thresholds: ExpiryThresholds,
): LiveExpiryShiftEvaluation {
  const lag = Math.round(liveState.growth_lag_days || 0);
  const sigma = Number((liveState.sigma_at_harvest_days ?? 0).toFixed(1));
  const daysSafe = liveState.days_until_safe_expiry ?? null;
  const daysHard = liveState.days_until_hard_expiry ?? null;

  const lagDirection: LiveExpiryShiftEvaluation['lagDirection'] =
    lag > 0 ? 'behind' : lag < 0 ? 'ahead' : 'on_schedule';

  const lagSummary =
    lag > 0
      ? `${lag}d behind nominal schedule`
      : lag < 0
        ? `${Math.abs(lag)}d ahead of nominal schedule`
        : 'On nominal schedule (0d lag)';

  const volatilitySummary = `±${sigma.toFixed(1)}d harvest spread at σ=${thresholds.weatherVolatility.toFixed(2)}`;

  const safeCountdownLabel = formatExpiryCountdown(daysSafe, 'safe');
  const hardCountdownLabel = formatExpiryCountdown(daysHard, 'hard');

  const isCritical =
    (daysHard !== null && daysHard <= 0) ||
    (daysSafe !== null && daysSafe <= -thresholds.expirySafetyDays);
  const isTight =
    !isCritical &&
    ((daysSafe !== null && (daysSafe < thresholds.expirySafetyDays || daysSafe <= 0)) ||
      (daysHard !== null && sigma > Math.max(1, daysHard)));
  const urgency: ExpiryUrgency = isCritical ? 'critical' : isTight ? 'tight' : 'safe';

  const safeDateLabel = liveState.safe_expiry_date ? formatDate(liveState.safe_expiry_date) : 'Safe cutoff';
  const hardDateLabel = liveState.hard_expiry_date ? formatDate(liveState.hard_expiry_date) : 'Hard cutoff';

  let headline: string;
  if (urgency === 'critical') {
    headline = `Live drift alert: ${hardCountdownLabel} to hard cutoff`;
  } else if (urgency === 'tight') {
    headline = `Live margin tightening: ${safeCountdownLabel} to safe cutoff`;
  } else {
    headline = `Live trajectory healthy: ${safeCountdownLabel} to safe cutoff`;
  }

  const lagShiftSentence =
    lag > 0
      ? `Observed canopy progress is ${lag}d slower than nominal, which pulls both Safe Expiry (${safeDateLabel}) and Hard Expiry (${hardDateLabel}) ${lag}d earlier because your crop now needs extra days to clear the field.`
      : lag < 0
        ? `Observed canopy progress is ${Math.abs(lag)}d faster than nominal, which pushes Safe Expiry (${safeDateLabel}) and Hard Expiry (${hardDateLabel}) ${Math.abs(lag)}d later and adds extra turnaround cushion.`
        : `Observed canopy progress matches the nominal curve (0d lag), keeping Safe Expiry (${safeDateLabel}) and Hard Expiry (${hardDateLabel}) unshifted.`;

  const volSentence =
    `Your Weather Volatility (σ=${thresholds.weatherVolatility.toFixed(2)}) widens the 3D maturity cone to ±${sigma.toFixed(1)}d at harvest, evaluated against your ${thresholds.expirySafetyDays}d safety buffer.`;

  return {
    urgency,
    lagDirection,
    lagSummary,
    volatilitySummary,
    safeCountdownLabel,
    hardCountdownLabel,
    headline,
    explanation: `${lagShiftSentence} ${volSentence}`,
  };
}

/**
 * Generates a plain-English live preview of how the user's configured thresholds behave across Plan & Monitor.
 */
export function explainThresholdsPreview(thresholds: ExpiryThresholds): ThresholdPreviewExplanation {
  const volLabel =
    thresholds.weatherVolatility >= 0.25
      ? 'wide (cautious)'
      : thresholds.weatherVolatility <= 0.12
        ? 'tight (steady weather)'
        : 'standard';

  const bufferDetail = `Requires at least ${thresholds.expirySafetyDays}d between harvest and next-crop sowing when ranking rotations and flagging tight Safe Expiry warnings.`;
  const collisionDetail = `Turns slot & rotation alerts red whenever late-harvest overlap probability reaches ${thresholds.collisionThresholdPct}% or higher.`;
  const volatilityDetail = `Sets a ${volLabel} ±σ=${thresholds.weatherVolatility.toFixed(2)} uncertainty cone around future growth trajectories in the 3D Live Monitor.`;

  return {
    summary: `${thresholds.expirySafetyDays}d safety buffer · ${thresholds.collisionThresholdPct}% collision alert · σ=${thresholds.weatherVolatility.toFixed(2)} volatility`,
    bufferDetail,
    collisionDetail,
    volatilityDetail,
  };
}
