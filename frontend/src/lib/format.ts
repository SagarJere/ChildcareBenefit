const currencyFormatter = new Intl.NumberFormat('en-IN', {
  style: 'currency',
  currency: 'INR',
  maximumFractionDigits: 0,
})

const dateFormatter = new Intl.DateTimeFormat('en-IN', {
  day: '2-digit',
  month: 'short',
  year: 'numeric',
})

const monthYearFormatter = new Intl.DateTimeFormat('en-IN', {
  month: 'short',
  year: 'numeric',
})

export function formatCurrency(amount: string | number): string {
  return currencyFormatter.format(Number(amount))
}

export function formatDate(isoDate: string): string {
  return dateFormatter.format(new Date(`${isoDate}T00:00:00`))
}

/** Formats an ISO date as just its month and year (e.g. "Sep 2026") —
 * used for payout schedule months, which are always the first of a
 * calendar month. */
export function formatMonthYear(isoDate: string): string {
  return monthYearFormatter.format(new Date(`${isoDate}T00:00:00`))
}

/** Formats a Date object directly (as opposed to an ISO date string) —
 * used for dates computed client-side, like the six-year cutoff. Uses
 * local date parts, not `toISOString()`, which would shift the date
 * across timezones ahead of UTC. */
export function formatDateObject(d: Date): string {
  return dateFormatter.format(d)
}

/** Adds whole years to a date, clamping Feb 29 to Feb 28 if the target
 * year isn't a leap year — mirrors the backend's `_add_years_clamped` in
 * app/services/eligibility_calculator.py exactly. */
function addYearsClamped(d: Date, years: number): Date {
  const originalMonth = d.getMonth()
  const candidate = new Date(d.getFullYear() + years, originalMonth, d.getDate())
  if (candidate.getMonth() !== originalMonth) {
    // Rolled into the next month (e.g. Feb 29 -> Mar 1) — clamp back to
    // the last day of the intended month.
    candidate.setDate(0)
  }
  return candidate
}

function lastDayOfMonth(d: Date): Date {
  return new Date(d.getFullYear(), d.getMonth() + 1, 0)
}

/** The child's 6th birthday date (DOB + 6 years, Feb 29 clamped). */
export function sixthBirthdayDate(isoDob: string): Date {
  const dob = new Date(`${isoDob}T00:00:00`)
  return addYearsClamped(dob, 6)
}

/** The last date the child is eligible for the benefit: the last day of
 * the calendar month containing their 6th birthday (confirmed business
 * decision — see DECISIONS_LOG.md item 12). Mirrors the backend's
 * `calculate_eligibility` six-year cutoff exactly, so this always agrees
 * with what the server would compute. */
export function sixYearCutoffDate(isoDob: string): Date {
  return lastDayOfMonth(sixthBirthdayDate(isoDob))
}

export function hasCrossedSixYearLimit(isoDob: string, asOf: Date = new Date()): boolean {
  const asOfDateOnly = new Date(asOf.getFullYear(), asOf.getMonth(), asOf.getDate())
  return asOfDateOnly > sixYearCutoffDate(isoDob)
}

/** The financial year label (e.g. "2026-27") containing the given date —
 * April through March, mirroring the backend's
 * `eligibility_calculator.compute_financial_year` exactly. */
export function currentFinancialYearLabel(asOf: Date = new Date()): string {
  const startYear = asOf.getMonth() >= 3 ? asOf.getFullYear() : asOf.getFullYear() - 1
  return `${startYear}-${String(startYear + 1).slice(-2)}`
}

export function calculateAge(isoDob: string): string {
  const dob = new Date(`${isoDob}T00:00:00`)
  const now = new Date()

  let years = now.getFullYear() - dob.getFullYear()
  let months = now.getMonth() - dob.getMonth()
  if (now.getDate() < dob.getDate()) {
    months -= 1
  }
  if (months < 0) {
    years -= 1
    months += 12
  }

  if (years <= 0) {
    return `${months} ${months === 1 ? 'month' : 'months'}`
  }
  return `${years} ${years === 1 ? 'year' : 'years'}${months > 0 ? `, ${months} mo` : ''}`
}
