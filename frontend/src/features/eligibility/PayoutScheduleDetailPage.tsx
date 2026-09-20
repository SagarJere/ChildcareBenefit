import { useQuery } from '@tanstack/react-query'
import { AlertCircle, ArrowLeft, Loader2 } from 'lucide-react'
import { Link, useParams, useSearchParams } from 'react-router-dom'

import { getPayoutSchedule } from '../../api/eligibility'
import { formatCurrency, formatMonthYear } from '../../lib/format'

export function PayoutScheduleDetailPage() {
  const { childId } = useParams<{ childId: string }>()
  const [searchParams] = useSearchParams()
  const financialYear = searchParams.get('fy') ?? ''

  const { data, isPending, isError } = useQuery({
    queryKey: ['payout-schedule', childId, financialYear],
    queryFn: () => getPayoutSchedule(childId!, financialYear),
    enabled: Boolean(childId && financialYear),
  })

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <Link
        to="/eligibility"
        className="flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-700"
      >
        <ArrowLeft className="h-4 w-4" aria-hidden="true" />
        Back to Eligibility Report
      </Link>

      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Monthly Payout Schedule</h1>
        <p className="mt-1 text-slate-600">Financial year {financialYear}</p>
      </div>

      {isPending && (
        <div className="flex items-center gap-2 text-slate-600">
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
          Loading…
        </div>
      )}

      {isError && (
        <div className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
          Could not load the payout schedule for this child and financial year.
        </div>
      )}

      {data && (
        <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white shadow-sm">
          <table className="min-w-full divide-y divide-slate-100 text-sm">
            <thead className="bg-slate-50 text-left text-xs font-medium uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-3">Month</th>
                <th className="px-4 py-3">Entitlement</th>
                <th className="px-4 py-3">Opening Balance</th>
                <th className="px-4 py-3">Available</th>
                <th className="px-4 py-3">Allocated</th>
                <th className="px-4 py-3">Adjustment</th>
                <th className="px-4 py-3">Payout</th>
                <th className="px-4 py-3">Closing Balance</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {data.map((row) => (
                <tr key={row.month}>
                  <td className="px-4 py-3 font-medium text-slate-900">
                    {formatMonthYear(row.month)}
                  </td>
                  <td className="px-4 py-3 text-slate-600">
                    {formatCurrency(row.entitlement_amount)}
                  </td>
                  <td className="px-4 py-3 text-slate-600">
                    {formatCurrency(row.opening_balance)}
                  </td>
                  <td className="px-4 py-3 text-slate-600">
                    {formatCurrency(row.total_available_amount)}
                  </td>
                  <td className="px-4 py-3 text-emerald-700">
                    {formatCurrency(row.claim_allocated_amount)}
                  </td>
                  <td className="px-4 py-3 text-slate-600">
                    {Number(row.adjustment_amount) === 0
                      ? '—'
                      : formatCurrency(row.adjustment_amount)}
                  </td>
                  <td className="px-4 py-3 font-medium text-slate-900">
                    {formatCurrency(row.calculated_payout_amount)}
                  </td>
                  <td className="px-4 py-3 text-slate-600">
                    {formatCurrency(row.closing_balance)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
