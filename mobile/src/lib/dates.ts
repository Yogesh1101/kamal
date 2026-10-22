/**
 * The backend sends dates as "YYYY-MM-DD" with no time zone.
 * `new Date("2026-10-01")` would read that as UTC midnight, which can land on the
 * previous day in some zones, so dates are built from their parts (local time).
 */

export function parseDate(isoDate: string): Date {
  const [year, month, day] = isoDate.split('-').map(Number);
  return new Date(year, month - 1, day);
}

export function toIsoDate(date: Date): string {
  const mm = String(date.getMonth() + 1).padStart(2, '0');
  const dd = String(date.getDate()).padStart(2, '0');
  return `${date.getFullYear()}-${mm}-${dd}`;
}

export function formatDate(isoDate: string): string {
  return parseDate(isoDate).toLocaleDateString(undefined, {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  });
}

export function describeDaysLeft(daysLeft: number): string {
  if (daysLeft < -1) return `Expired ${-daysLeft} days ago`;
  if (daysLeft === -1) return 'Expired yesterday';
  if (daysLeft === 0) return 'Expires today';
  if (daysLeft === 1) return 'Expires tomorrow';
  return `${daysLeft} days left`;
}

/** Which theme colour to show an expiry in. */
export function expiryTone(daysLeft: number): 'danger' | 'warning' | 'textSecondary' {
  if (daysLeft <= 0) return 'danger';
  if (daysLeft <= 3) return 'warning';
  return 'textSecondary';
}
