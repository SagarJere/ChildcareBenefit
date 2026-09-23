import { useQuery } from '@tanstack/react-query'
import { Download, Loader2 } from 'lucide-react'
import { useState } from 'react'

import {
  downloadReportCsv,
  getFirstYearPayoutReport,
  getPayoutReport,
  type PayoutReportFilters,
} from '../../api/reports'
import { EmployeeAutocomplete } from '../../components/EmployeeAutocomplete'
import { FinancialYearSelect } from '../../components/FinancialYearSelect'
import { PayoutReportTable } from '../../components/PayoutReportTable'
import { formatCurrency } from '../../lib/format'

interface PayoutReportProps {
  /** "claim" (default): the original report, driven by approved claims
   * (months 14+). "first_year": the child's first-13-months auto-paid
   * amounts, with no claim involved. */
  source?: 'claim' | 'first_year'
}

const SOURCE_CONFIG = {
  claim: {
    queryKey: 'report-payout',
    fetch: getPayoutReport,
    path: '/hr/reports/payout',
    filename: 'payout-report.csv',
    idPrefix: 'payout',
    totalLabel: 'Total payout',
  },
  first_year: {
    queryKey: 'report-payout-first-year',
    fetch: getFirstYearPayoutReport,
    path: '/hr/reports/payout/first-year',
    filename: 'first-year-payout-report.csv',
    idPrefix: 'firstYearPayout',
    totalLabel: 'Total first year payout',
  },
} as const

export function PayoutReport({ source = 'claim' }: PayoutReportProps) {
  const [filters, setFilters] = useState<PayoutReportFilters>({})
  const config = SOURCE_CONFIG[source]

  const { data, isPending, isError } = useQuery({
    queryKey: [config.queryKey, filters],
    queryFn: () => config.fetch(filters),
  })

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end gap-3 rounded-lg border border-slate-200 bg-white p-4">
        <FinancialYearSelect
          id={`${config.idPrefix}FyFilter`}
          label="Financial year"
          value={filters.financial_year ?? ''}
          onChange={(financial_year) =>
            setFilters((f) => ({ ...f, financial_year: financial_year || undefined }))
          }
        />
        <EmployeeAutocomplete
          id={`${config.idPrefix}EmployeeFilter`}
          label="Employee"
          value={filters.employee_id ?? ''}
          onChange={(employee_id) =>
            setFilters((f) => ({ ...f, employee_id: employee_id || undefined }))
          }
        />
        <div>
          <label
            htmlFor={`${config.idPrefix}ChildFilter`}
            className="block text-xs font-medium text-slate-500"
          >
            Child ID
          </label>
          <input
            id={`${config.idPrefix}ChildFilter`}
            type="text"
            value={filters.child_id ?? ''}
            onChange={(e) => setFilters((f) => ({ ...f, child_id: e.target.value || undefined }))}
            className="mt-1 rounded-md border border-slate-300 px-2 py-1.5 text-sm"
          />
        </div>
        <button
          type="button"
          onClick={() =>
            downloadReportCsv(
              config.path,
              filters as Record<string, string | undefined>,
              config.filename,
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
          <div className="rounded-lg border border-slate-200 bg-white p-4 text-sm">
            <div className="text-slate-500">{config.totalLabel}</div>
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
