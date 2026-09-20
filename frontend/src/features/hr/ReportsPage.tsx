import { useState } from 'react'

import { ClaimsSummaryReport } from './ClaimsSummaryReport'
import { EligibilityUtilizationReport } from './EligibilityUtilizationReport'
import { HeadcountReport } from './HeadcountReport'
import { PayoutReport } from './PayoutReport'

const TABS = [
  { key: 'claims', label: 'Claims Summary' },
  { key: 'eligibility', label: 'Eligibility Utilization' },
  { key: 'payout', label: 'Payout' },
  { key: 'headcount', label: 'Headcount' },
] as const

type TabKey = (typeof TABS)[number]['key']

export function ReportsPage() {
  const [tab, setTab] = useState<TabKey>('claims')

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Reports</h1>
        <p className="mt-1 text-slate-600">
          Claims, eligibility utilization, payout, and headcount.
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
      {tab === 'payout' && <PayoutReport />}
      {tab === 'headcount' && <HeadcountReport />}
    </div>
  )
}
