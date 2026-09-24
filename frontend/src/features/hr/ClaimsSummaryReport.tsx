import { useQuery } from '@tanstack/react-query'
import {
  CheckCircle2,
  Clock,
  Download,
  FileText,
  Inbox,
  Layers,
  Loader2,
  Receipt,
  Send,
  XCircle,
} from 'lucide-react'
import type { ComponentType } from 'react'
import { useState } from 'react'

import type { Claim } from '../../api/claims'
import { downloadReportCsv, getClaimsSummary, type ClaimsSummaryFilters } from '../../api/reports'
import { EmployeeAutocomplete } from '../../components/EmployeeAutocomplete'
import { formatCurrency, formatDate } from '../../lib/format'
import { ClaimStatusBadge } from '../claims/ClaimStatusBadge'
import { LABELS, STYLES } from '../claims/claimStatusStyles'
import { ClaimDetailModal } from './ClaimDetailModal'

const STATUS_OPTIONS = ['Draft', 'Submitted', 'Approved', 'Rejected', 'SentBack']

// Fixed display order (matches ClaimStatusBadge's own declaration order),
// not object-key order — count_by_status only ever contains whichever
// statuses actually occur in the filtered results, in no guaranteed order.
const STATUS_ORDER: Claim['claim_status'][] = [
  'Draft',
  'Submitted',
  'HRReview',
  'Approved',
  'Rejected',
  'SentBack',
]

const STATUS_ICONS: Record<Claim['claim_status'], ComponentType<{ className?: string }>> = {
  Draft: FileText,
  Submitted: Inbox,
  HRReview: Clock,
  Approved: CheckCircle2,
  Rejected: XCircle,
  SentBack: Send,
}

function StatTile({
  icon: Icon,
  label,
  value,
  valueClassName = 'text-slate-900',
}: {
  icon: ComponentType<{ className?: string }>
  label: string
  value: string
  valueClassName?: string
}) {
  return (
    <div className="flex items-center gap-3 rounded-lg border border-slate-200 bg-white p-4">
      <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-slate-100">
        <Icon className="h-4.5 w-4.5 text-slate-500" aria-hidden="true" />
      </div>
      <div>
        <div className="text-xs font-medium text-slate-500">{label}</div>
        <div className={`text-lg font-semibold ${valueClassName}`}>{value}</div>
      </div>
    </div>
  )
}

export function ClaimsSummaryReport() {
  const [filters, setFilters] = useState<ClaimsSummaryFilters>({})
  const [viewClaimId, setViewClaimId] = useState<number | null>(null)

  const { data, isPending, isError } = useQuery({
    queryKey: ['report-claims-summary', filters],
    queryFn: () => getClaimsSummary(filters),
  })

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end gap-3 rounded-lg border border-slate-200 bg-white p-4">
        <div>
          <label htmlFor="dateFrom" className="block text-xs font-medium text-slate-500">
            Invoice from
          </label>
          <input
            id="dateFrom"
            type="date"
            value={filters.date_from ?? ''}
            onChange={(e) => setFilters((f) => ({ ...f, date_from: e.target.value || undefined }))}
            className="mt-1 rounded-md border border-slate-300 px-2 py-1.5 text-sm"
          />
        </div>
        <div>
          <label htmlFor="dateTo" className="block text-xs font-medium text-slate-500">
            Invoice to
          </label>
          <input
            id="dateTo"
            type="date"
            value={filters.date_to ?? ''}
            onChange={(e) => setFilters((f) => ({ ...f, date_to: e.target.value || undefined }))}
            className="mt-1 rounded-md border border-slate-300 px-2 py-1.5 text-sm"
          />
        </div>
        <div>
          <label htmlFor="statusFilter" className="block text-xs font-medium text-slate-500">
            Status
          </label>
          <select
            id="statusFilter"
            value={filters.status ?? ''}
            onChange={(e) => setFilters((f) => ({ ...f, status: e.target.value || undefined }))}
            className="mt-1 rounded-md border border-slate-300 px-2 py-1.5 text-sm"
          >
            <option value="">All</option>
            {STATUS_OPTIONS.map((s) => (
              <option key={s} value={s}>
                {s}
              </option>
            ))}
          </select>
        </div>
        <EmployeeAutocomplete
          id="employeeFilter"
          label="Employee"
          value={filters.employee_id ?? ''}
          onChange={(employee_id) =>
            setFilters((f) => ({ ...f, employee_id: employee_id || undefined }))
          }
        />
        <button
          type="button"
          onClick={() =>
            downloadReportCsv(
              '/hr/reports/claims-summary',
              filters as Record<string, string | undefined>,
              'claims-summary.csv',
            )
          }
          className="ml-auto flex items-center gap-1.5 rounded-md bg-slate-100 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-200"
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
      {isError && <p className="text-red-700">Could not load this report.</p>}

      {data && (
        <>
          <div className="grid grid-cols-1 gap-3 sm:grid-cols-3">
            <StatTile icon={Layers} label="Total claims" value={data.totals.total_claims.toLocaleString('en-IN')} />
            <StatTile
              icon={Receipt}
              label="Total invoice amount"
              value={formatCurrency(data.totals.total_invoice_amount)}
            />
            <StatTile
              icon={CheckCircle2}
              label="Total approved amount"
              value={formatCurrency(data.totals.total_approved_amount)}
              valueClassName="text-emerald-700"
            />
          </div>

          <div className="flex flex-wrap gap-2">
            {STATUS_ORDER.filter((status) => status in data.totals.count_by_status).map(
              (status) => {
                const Icon = STATUS_ICONS[status]
                return (
                  <div
                    key={status}
                    className={`flex items-center gap-1.5 rounded-full py-1 pl-2.5 pr-3 text-sm font-medium ${STYLES[status]}`}
                  >
                    <Icon className="h-3.5 w-3.5" aria-hidden="true" />
                    <span>{LABELS[status]}</span>
                    <span className="font-semibold">{data.totals.count_by_status[status]}</span>
                  </div>
                )
              },
            )}
          </div>

          <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
            <table className="min-w-full divide-y divide-slate-100 text-sm">
              <thead className="bg-slate-50 text-left text-xs font-medium uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-4 py-3">Employee ID</th>
                  <th className="px-4 py-3">Employee</th>
                  <th className="px-4 py-3">Child ID</th>
                  <th className="px-4 py-3">Child</th>
                  <th className="px-4 py-3">Invoice</th>
                  <th className="px-4 py-3">Invoice Date</th>
                  <th className="px-4 py-3">Amount</th>
                  <th className="px-4 py-3">Institution</th>
                  <th className="px-4 py-3">Status</th>
                  <th className="px-4 py-3">Submitted</th>
                  <th className="px-4 py-3">Approved</th>
                  <th className="px-4 py-3" />
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {data.rows.map((row) => (
                  <tr key={row.claim_id}>
                    <td className="px-4 py-3 text-slate-600">{row.employee_id}</td>
                    <td className="px-4 py-3 text-slate-800">{row.employee_name}</td>
                    <td className="px-4 py-3 text-slate-600">{row.child_id}</td>
                    <td className="px-4 py-3 text-slate-600">{row.child_name}</td>
                    <td className="px-4 py-3 text-slate-600">{row.invoice_number}</td>
                    <td className="px-4 py-3 text-slate-600">{formatDate(row.invoice_date)}</td>
                    <td className="px-4 py-3 text-slate-600">
                      {formatCurrency(row.invoice_amount)}
                    </td>
                    <td className="px-4 py-3 text-slate-600">{row.institution_name ?? '—'}</td>
                    <td className="px-4 py-3">
                      <ClaimStatusBadge status={row.claim_status} />
                    </td>
                    <td className="px-4 py-3 text-slate-500">
                      {row.submitted_date ? formatDate(row.submitted_date.slice(0, 10)) : '—'}
                    </td>
                    <td className="px-4 py-3 text-slate-500">
                      {row.approved_date ? formatDate(row.approved_date.slice(0, 10)) : '—'}
                    </td>
                    <td className="px-4 py-3 text-right">
                      <button
                        type="button"
                        onClick={() => setViewClaimId(row.claim_id)}
                        className="font-medium text-indigo-700 hover:underline"
                      >
                        View details
                      </button>
                    </td>
                  </tr>
                ))}
                {data.rows.length === 0 && (
                  <tr>
                    <td colSpan={12} className="px-4 py-6 text-center text-slate-400">
                      No claims match these filters.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
        </>
      )}
      {viewClaimId !== null && (
        <ClaimDetailModal claimId={viewClaimId} onClose={() => setViewClaimId(null)} />
      )}
    </div>
  )
}
