import { useQuery } from '@tanstack/react-query'
import { AlertTriangle, Download, Loader2 } from 'lucide-react'
import type { ReactNode } from 'react'

import { downloadReportCsv } from '../../api/reports'
import { getMyFirstYearPayoutReport, getMyPayoutReport } from '../../api/eligibility'
import type { PayoutReportResponse } from '../../api/reports'
import { PayoutReportTable } from '../../components/PayoutReportTable'
import { formatCurrency } from '../../lib/format'

function PayoutSection({
  title,
  description,
  emptyMessage,
  data,
  isPending,
  isError,
  onExport,
}: {
  title: string
  description: string
  emptyMessage: string
  data: PayoutReportResponse | undefined
  isPending: boolean
  isError: boolean
  onExport: () => void
}): ReactNode {
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div>
          <h2 className="text-lg font-semibold text-slate-900">{title}</h2>
          <p className="mt-1 text-sm text-slate-600">{description}</p>
        </div>
        <button
          type="button"
          onClick={onExport}
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
          Could not load this report. Please try again shortly.
        </div>
      )}

      {data && data.rows.length === 0 && (
        <div className="rounded-lg border border-dashed border-slate-300 bg-white px-6 py-8 text-center text-slate-600">
          {emptyMessage}
        </div>
      )}

      {data && data.rows.length > 0 && (
        <>
          <div className="rounded-lg border border-slate-200 bg-white p-4 text-sm">
            <div className="text-slate-500">Total</div>
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

export function MyPayoutPage() {
  const firstYearQuery = useQuery({
    queryKey: ['my-first-year-payout-report'],
    queryFn: () => getMyFirstYearPayoutReport(),
  })
  const claimQuery = useQuery({
    queryKey: ['my-payout-report'],
    queryFn: () => getMyPayoutReport(),
  })

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">My Payout</h1>
        <p className="mt-1 text-slate-600">
          Your childcare benefit payout, scoped to your own children — first year payout (auto-
          paid, no claim needed) and claim payout, each broken down by month, April through March.
        </p>
      </div>

      <PayoutSection
        title="First Year Payout"
        description="Your child's first 13 months of life — paid automatically, no claim needed."
        emptyMessage="No first-year payout — this applies to a child's first 13 months only."
        data={firstYearQuery.data}
        isPending={firstYearQuery.isPending}
        isError={firstYearQuery.isError}
        onExport={() =>
          downloadReportCsv(
            '/eligibility/payout-report/first-year',
            {},
            'my-first-year-payout.csv',
          )
        }
      />

      <div className="border-t border-slate-200 pt-8">
        <PayoutSection
          title="Claim Payout"
          description="Your approved claims — the same view HR sees, scoped to your own children."
          emptyMessage="No payouts yet — nothing here until HR approves one of your claims."
          data={claimQuery.data}
          isPending={claimQuery.isPending}
          isError={claimQuery.isError}
          onExport={() => downloadReportCsv('/eligibility/payout-report', {}, 'my-payout.csv')}
        />
      </div>
    </div>
  )
}
