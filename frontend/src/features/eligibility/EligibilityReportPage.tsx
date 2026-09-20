import { useQuery } from '@tanstack/react-query'
import { AlertTriangle, Loader2 } from 'lucide-react'
import { Link } from 'react-router-dom'

import { getEligibilityReport } from '../../api/eligibility'
import { calculateAge, formatCurrency, formatDate } from '../../lib/format'

export function EligibilityReportPage() {
  const { data, isPending, isError } = useQuery({
    queryKey: ['eligibility-report'],
    queryFn: getEligibilityReport,
  })

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Eligibility &amp; Payout</h1>
        <p className="mt-1 text-slate-600">
          Allotted, utilized, in-progress, and balance amounts for each child, by financial year.
          Open "Monthly Schedule" on a row to see exactly which months a child's approved claims
          pay out in.
        </p>
      </div>

      {isPending && (
        <div className="flex items-center gap-2 text-slate-600">
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
          Loading…
        </div>
      )}

      {isError && (
        <div className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
          Could not load the eligibility report. Please try again shortly.
        </div>
      )}

      {data && data.rows.length === 0 && (
        <div className="rounded-lg border border-dashed border-slate-300 bg-white px-6 py-12 text-center text-slate-600">
          No eligibility records yet. Add a child from "My Children" to get started.
        </div>
      )}

      {data && data.rows.length > 0 && (
        <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white shadow-sm">
          <table className="min-w-full divide-y divide-slate-100 text-sm">
            <thead className="bg-slate-50 text-left text-xs font-medium uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-3">Child</th>
                <th className="px-4 py-3">Age</th>
                <th className="px-4 py-3">Financial Year</th>
                <th className="px-4 py-3">Allotted</th>
                <th className="px-4 py-3">Utilized</th>
                <th className="px-4 py-3">In Progress</th>
                <th className="px-4 py-3">Balance</th>
                <th className="px-4 py-3">Last Modified</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {data.rows.map((row) => (
                <tr key={row.eligibility_id}>
                  <td className="px-4 py-3 font-medium text-slate-900">{row.child_name}</td>
                  <td className="px-4 py-3 text-slate-600">{calculateAge(row.child_dob)}</td>
                  <td className="px-4 py-3 text-slate-600">{row.financial_year}</td>
                  <td className="px-4 py-3 text-slate-600">
                    {formatCurrency(row.allotted_amount)}
                  </td>
                  <td className="px-4 py-3 text-emerald-700">
                    {formatCurrency(row.utilized_amount)}
                  </td>
                  <td className="px-4 py-3 text-amber-700">
                    {formatCurrency(row.in_progress_amount)}
                  </td>
                  <td className="px-4 py-3 font-medium text-slate-900">
                    {formatCurrency(row.balance_amount)}
                  </td>
                  <td className="px-4 py-3 text-slate-500">
                    {formatDate(row.last_modified_date.slice(0, 10))}
                  </td>
                  <td className="px-4 py-3 text-right">
                    <Link
                      to={`/eligibility/${row.child_id}/schedule?fy=${row.financial_year}`}
                      className="font-medium text-indigo-700 hover:underline"
                    >
                      Monthly Schedule
                    </Link>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      <p className="text-xs text-slate-400">
        Balance is Allotted minus Utilized, and does not reserve against claims still In Progress.
      </p>
    </div>
  )
}
