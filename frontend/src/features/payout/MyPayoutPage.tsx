import { useQuery } from '@tanstack/react-query'
import { AlertTriangle, Download, Loader2 } from 'lucide-react'

import { downloadReportCsv } from '../../api/reports'
import { getMyPayoutReport } from '../../api/eligibility'
import { PayoutReportTable } from '../../components/PayoutReportTable'
import { formatCurrency } from '../../lib/format'

export function MyPayoutPage() {
  const { data, isPending, isError } = useQuery({
    queryKey: ['my-payout-report'],
    queryFn: () => getMyPayoutReport(),
  })

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">My Payout</h1>
          <p className="mt-1 text-slate-600">
            Your approved claims broken down by month, April through March — the same view HR
            sees, scoped to your own children.
          </p>
        </div>
        <button
          type="button"
          onClick={() => downloadReportCsv('/eligibility/payout-report', {}, 'my-payout.csv')}
          className="flex items-center gap-1.5 rounded-md bg-slate-100 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-200"
        >
          <Download className="h-4 w-4" aria-hidden="true" />
          Export CSV
        </button>
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
          Could not load your payout report. Please try again shortly.
        </div>
      )}

      {data && data.rows.length === 0 && (
        <div className="rounded-lg border border-dashed border-slate-300 bg-white px-6 py-12 text-center text-slate-600">
          No payouts yet — nothing here until HR approves one of your claims.
        </div>
      )}

      {data && data.rows.length > 0 && (
        <>
          <div className="rounded-lg border border-slate-200 bg-white p-4 text-sm">
            <div className="text-slate-500">Total payout</div>
            <div className="font-semibold text-slate-900">
              {formatCurrency(data.totals.total_payout)}
            </div>
          </div>
          <PayoutReportTable rows={data.rows} />
        </>
      )}
    </div>
  )
}
