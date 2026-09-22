import { useQuery } from '@tanstack/react-query'
import { AlertTriangle, ClipboardList, Loader2 } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'

import { listHRClaims } from '../../api/hr'
import { EmployeeAutocomplete } from '../../components/EmployeeAutocomplete'
import { ClaimStatusBadge } from '../claims/ClaimStatusBadge'
import { formatCurrency, formatDate } from '../../lib/format'

const STATUS_TABS = ['Submitted', 'Approved', 'Rejected', 'SentBack', 'All'] as const

interface OtherFilters {
  employee_id?: string
  date_from?: string
  date_to?: string
}

export function HRClaimsPage() {
  const [statusTab, setStatusTab] = useState<(typeof STATUS_TABS)[number]>('Submitted')
  const [otherFilters, setOtherFilters] = useState<OtherFilters>({})

  const { data: claims, isPending, isError } = useQuery({
    queryKey: ['hr-claims', statusTab, otherFilters],
    queryFn: () =>
      listHRClaims({
        ...(statusTab === 'All' ? {} : { status: statusTab }),
        ...otherFilters,
      }),
  })

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Claim Approval Queue</h1>
        <p className="mt-1 text-slate-600">Review and act on employee childcare benefit claims.</p>
      </div>

      <div className="flex flex-wrap gap-1">
        {STATUS_TABS.map((tab) => (
          <button
            key={tab}
            type="button"
            onClick={() => setStatusTab(tab)}
            className={`rounded-full px-3 py-1 text-sm font-medium transition ${
              statusTab === tab
                ? 'bg-indigo-700 text-white'
                : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
            }`}
          >
            {tab === 'SentBack' ? 'Sent Back' : tab}
          </button>
        ))}
      </div>

      <div className="flex flex-wrap items-end gap-3 rounded-lg border border-slate-200 bg-white p-4">
        <EmployeeAutocomplete
          id="hrQueueEmployeeFilter"
          label="Employee"
          value={otherFilters.employee_id ?? ''}
          onChange={(employee_id) =>
            setOtherFilters((f) => ({ ...f, employee_id: employee_id || undefined }))
          }
        />
        <div>
          <label htmlFor="hrQueueDateFrom" className="block text-xs font-medium text-slate-500">
            Invoice from
          </label>
          <input
            id="hrQueueDateFrom"
            type="date"
            value={otherFilters.date_from ?? ''}
            onChange={(e) =>
              setOtherFilters((f) => ({ ...f, date_from: e.target.value || undefined }))
            }
            className="mt-1 rounded-md border border-slate-300 px-2 py-1.5 text-sm"
          />
        </div>
        <div>
          <label htmlFor="hrQueueDateTo" className="block text-xs font-medium text-slate-500">
            Invoice to
          </label>
          <input
            id="hrQueueDateTo"
            type="date"
            value={otherFilters.date_to ?? ''}
            onChange={(e) =>
              setOtherFilters((f) => ({ ...f, date_to: e.target.value || undefined }))
            }
            className="mt-1 rounded-md border border-slate-300 px-2 py-1.5 text-sm"
          />
        </div>
        {(otherFilters.employee_id || otherFilters.date_from || otherFilters.date_to) && (
          <button
            type="button"
            onClick={() => setOtherFilters({})}
            className="rounded-md px-3 py-1.5 text-sm font-medium text-slate-500 hover:bg-slate-100"
          >
            Clear filters
          </button>
        )}
      </div>

      {isPending && (
        <div className="flex items-center gap-2 text-slate-600">
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
          Loading claims…
        </div>
      )}

      {isError && (
        <div className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
          Could not load claims. Please try again shortly.
        </div>
      )}

      {claims && claims.length === 0 && (
        <div className="flex flex-col items-center gap-3 rounded-lg border border-dashed border-slate-300 bg-white px-6 py-12 text-center">
          <ClipboardList className="h-8 w-8 text-slate-300" aria-hidden="true" />
          <p className="text-slate-600">No claims in this view.</p>
        </div>
      )}

      {claims && claims.length > 0 && (
        <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white shadow-sm">
          <table className="min-w-full divide-y divide-slate-100 text-sm">
            <thead className="bg-slate-50 text-left text-xs font-medium uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-3">Employee</th>
                <th className="px-4 py-3">Child</th>
                <th className="px-4 py-3">Invoice</th>
                <th className="px-4 py-3">Invoice Date</th>
                <th className="px-4 py-3">Amount</th>
                <th className="px-4 py-3">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {claims.map((claim) => (
                <tr key={claim.claim_id} className="hover:bg-slate-50">
                  <td className="px-4 py-3">
                    <Link
                      to={`/hr/claims/${claim.claim_id}`}
                      className="font-medium text-indigo-700 hover:underline"
                    >
                      {claim.employee_name}
                    </Link>
                    <div className="text-xs text-slate-400">{claim.employee_id}</div>
                  </td>
                  <td className="px-4 py-3 text-slate-600">{claim.child_name}</td>
                  <td className="px-4 py-3 text-slate-600">{claim.invoice_number}</td>
                  <td className="px-4 py-3 text-slate-600">{formatDate(claim.invoice_date)}</td>
                  <td className="px-4 py-3 text-slate-600">
                    {formatCurrency(claim.invoice_amount)}
                  </td>
                  <td className="px-4 py-3">
                    <ClaimStatusBadge status={claim.claim_status} />
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
