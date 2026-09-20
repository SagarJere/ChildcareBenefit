import { formatCurrency, formatDate } from '../../lib/format'

interface EligibilitySummaryProps {
  financialYear: string
  eligibilityStartDate: string
  eligibilityEndDate: string | null
  eligibleMonths: number
  monthlyBenefitAmount: string
  allottedAmount: string
  remainingAmount?: string
}

export function EligibilitySummary({
  financialYear,
  eligibilityStartDate,
  eligibilityEndDate,
  eligibleMonths,
  monthlyBenefitAmount,
  allottedAmount,
  remainingAmount,
}: EligibilitySummaryProps) {
  if (eligibleMonths === 0) {
    return (
      <p className="text-sm text-amber-700">
        Not eligible for FY {financialYear} — the child has already passed the six-year benefit
        limit.
      </p>
    )
  }

  return (
    <dl className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-sm">
      <dt className="text-slate-500">Financial year</dt>
      <dd className="text-right font-medium text-slate-900">{financialYear}</dd>

      <dt className="text-slate-500">Eligible period</dt>
      <dd className="text-right font-medium text-slate-900">
        {formatDate(eligibilityStartDate)}
        {eligibilityEndDate ? ` – ${formatDate(eligibilityEndDate)}` : ''}
      </dd>

      <dt className="text-slate-500">Eligible months</dt>
      <dd className="text-right font-medium text-slate-900">{eligibleMonths}</dd>

      <dt className="text-slate-500">Monthly amount</dt>
      <dd className="text-right font-medium text-slate-900">
        {formatCurrency(monthlyBenefitAmount)}
      </dd>

      <dt className="text-slate-500">Total allotted</dt>
      <dd className="text-right font-semibold text-indigo-700">
        {formatCurrency(allottedAmount)}
      </dd>

      {remainingAmount !== undefined && (
        <>
          <dt className="text-slate-500">Remaining</dt>
          <dd className="text-right font-medium text-emerald-700">
            {formatCurrency(remainingAmount)}
          </dd>
        </>
      )}
    </dl>
  )
}
