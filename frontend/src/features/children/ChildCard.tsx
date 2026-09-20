import { Cake } from 'lucide-react'

import type { Child } from '../../api/children'
import { calculateAge, formatDate } from '../../lib/format'
import { EligibilitySummary } from './EligibilitySummary'

export function ChildCard({ child }: { child: Child }) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4 shadow-sm">
      <div className="flex items-start justify-between gap-3">
        <div>
          <h3 className="font-semibold text-slate-900">{child.child_name}</h3>
          <p className="mt-0.5 flex items-center gap-1.5 text-sm text-slate-500">
            <Cake className="h-3.5 w-3.5" aria-hidden="true" />
            {formatDate(child.child_dob)} · {calculateAge(child.child_dob)} old
          </p>
        </div>
        <span className="shrink-0 rounded-full bg-slate-100 px-2 py-0.5 text-xs font-medium text-slate-600">
          {child.child_id}
        </span>
      </div>

      <div className="mt-4 border-t border-slate-100 pt-3">
        {child.eligibility ? (
          <EligibilitySummary
            financialYear={child.eligibility.financial_year}
            eligibilityStartDate={child.eligibility.eligibility_start_date}
            eligibilityEndDate={child.eligibility.eligibility_end_date}
            eligibleMonths={child.eligibility.eligible_months}
            monthlyBenefitAmount={child.eligibility.monthly_benefit_amount}
            allottedAmount={child.eligibility.allotted_amount}
            remainingAmount={child.eligibility.remaining_amount}
          />
        ) : (
          <p className="text-sm text-slate-400">No eligibility on record for this financial year.</p>
        )}
      </div>
    </div>
  )
}
