const locale = 'en-LK';

export function formatNumber(value: number, decimals = 0) {
  return new Intl.NumberFormat(locale, { minimumFractionDigits: decimals, maximumFractionDigits: decimals }).format(value);
}

export function formatUnit(value: number, unit: string, decimals = 0) {
  return formatNumber(value, decimals) + ' ' + unit;
}

export function formatPercent(value: number) {
  return new Intl.NumberFormat(locale, { style: 'percent', maximumFractionDigits: 1 }).format(value / 100);
}

export function formatCurrency(value: number, currency = 'LKR') {
  return new Intl.NumberFormat(locale, { style: 'currency', currency }).format(value);
}

export function calendarDate(date = new Date(), offset = 0) {
  const local = new Date(date);
  local.setDate(local.getDate() + offset);
  return [String(local.getFullYear()).padStart(4, '0'), String(local.getMonth() + 1).padStart(2, '0'),
    String(local.getDate()).padStart(2, '0')].join('-');
}

export function lastYalaDate(date = new Date()) {
  // The planner's Yala season runs from April through September.
  const start = new Date(date);
  start.setFullYear(date.getFullYear() - (date.getMonth() < 9 ? 1 : 0), 3, 1);
  return calendarDate(start);
}

export function parseCalendarDate(value: string) {
  if (!/^\d{4}-\d{2}-\d{2}$/.test(value)) return null;
  const [year, month, day] = value.split('-').map(Number);
  // Use a local calendar day. UTC shifts dates on devices west of Greenwich.
  const result = new Date(2000, 0, 1);
  result.setFullYear(year, month - 1, day);
  return result.getFullYear() === year && result.getMonth() === month - 1 && result.getDate() === day ? result : null;
}

export function formatDate(value: string) {
  const date = parseCalendarDate(value);
  return date ? new Intl.DateTimeFormat(locale, { year: 'numeric', month: 'short', day: 'numeric' }).format(date) : value;
}
