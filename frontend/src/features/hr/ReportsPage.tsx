import { ArrowLeft } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'

import { ChildDetailsReport } from './ChildDetailsReport'
import { ClaimsSummaryReport } from './ClaimsSummaryReport'
import { EligibilityUtilizationReport } from './EligibilityUtilizationReport'
import { HeadcountReport } from './HeadcountReport'
import { PayoutReport } from './PayoutReport'

const TABS = [
  { key: 'claims', label: 'Claims Summary' },
  { key: 'eligibility', label: 'Eligibility Utilization' },
  { key: 'payout', label: 'Payout' },
  { key: 'firstYearPayout', label: 'First Year Payout' },
  { key: 'headcount', label: 'Headcount' },
  { key: 'childDetails', label: 'Child Details' },
] as const

type TabKey = (typeof TABS)[number]['key']

export function ReportsPage() {
  const [tab, setTab] = useState<TabKey>('claims')

  return (
    <div className="space-y-6">
      <Link
        to="/hr/dashboard"
        className="flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-700"
      >
        <ArrowLeft className="h-4 w-4" aria-hidden="true" />
        Back to HR Dashboard
      </Link>

      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Reports</h1>
        <p className="mt-1 text-slate-600">
          Claims, eligibility utilization, payout, first year payout, headcount, and child
          details.
        </p>
      </div>

      <div className="flex gap-1 overflow-x-auto border-b border-slate-200">
        {TABS.map((t) => (
          <button
            key={t.key}
            type="button"
            onClick={() => setTab(t.key)}
            className={`shrink-0 whitespace-nowrap px-3 py-2 text-sm font-medium ${
              tab === t.key
                ? 'border-b-2 border-indigo-700 text-indigo-700'
                : 'text-slate-500 hover:text-slate-700'
            }`}
          >
            {t.label}
          </button>
        ))}
      </div>

      {tab === 'claims' && <ClaimsSummaryReport />}
      {tab === 'eligibility' && <EligibilityUtilizationReport />}
      {tab === 'payout' && <PayoutReport source="claim" />}
      {tab === 'firstYearPayout' && <PayoutReport source="first_year" />}
      {tab === 'headcount' && <HeadcountReport />}
      {tab === 'childDetails' && <ChildDetailsReport />}
    </div>
  )
}
