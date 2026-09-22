import { useQuery } from '@tanstack/react-query'
import { Download, Loader2 } from 'lucide-react'
import { useState } from 'react'

import { downloadReportCsv, getPayoutReport, type PayoutReportFilters } from '../../api/reports'
import { EmployeeAutocomplete } from '../../components/EmployeeAutocomplete'
import { FinancialYearSelect } from '../../components/FinancialYearSelect'
import { PayoutReportTable } from '../../components/PayoutReportTable'
import { formatCurrency } from '../../lib/format'

export function PayoutReport() {
  const [filters, setFilters] = useState<PayoutReportFilters>({})

  const { data, isPending, isError } = useQuery({
    queryKey: ['report-payout', filters],
    queryFn: () => getPayoutReport(filters),
  })

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end gap-3 rounded-lg border border-slate-200 bg-white p-4">
        <FinancialYearSelect
          id="payoutFyFilter"
          label="Financial year"
          value={filters.financial_year ?? ''}
          onChange={(financial_year) =>
            setFilters((f) => ({ ...f, financial_year: financial_year || undefined }))
          }
        />
        <EmployeeAutocomplete
          id="payoutEmployeeFilter"
          label="Employee"
          value={filters.employee_id ?? ''}
          onChange={(employee_id) =>
            setFilters((f) => ({ ...f, employee_id: employee_id || undefined }))
          }
        />
        <div>
          <label htmlFor="payoutChildFilter" className="block text-xs font-medium text-slate-500">
            Child ID
          </label>
          <input
            id="payoutChildFilter"
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
              '/hr/reports/payout',
              filters as Record<string, string | undefined>,
              'payout-report.csv',
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
