import { useQuery } from '@tanstack/react-query'
import { Download, Loader2 } from 'lucide-react'
import { useState } from 'react'

import {
  downloadReportCsv,
  getEligibilityUtilization,
  type EligibilityUtilizationFilters,
} from '../../api/reports'
import { EmployeeAutocomplete } from '../../components/EmployeeAutocomplete'
import { FinancialYearSelect } from '../../components/FinancialYearSelect'
import { formatCurrency } from '../../lib/format'

export function EligibilityUtilizationReport() {
  const [filters, setFilters] = useState<EligibilityUtilizationFilters>({})

  const { data, isPending, isError } = useQuery({
    queryKey: ['report-eligibility-utilization', filters],
    queryFn: () => getEligibilityUtilization(filters),
  })

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end gap-3 rounded-lg border border-slate-200 bg-white p-4">
        <FinancialYearSelect
          id="fyFilter"
          label="Financial year"
          value={filters.financial_year ?? ''}
          onChange={(financial_year) =>
            setFilters((f) => ({ ...f, financial_year: financial_year || undefined }))
          }
        />
        <EmployeeAutocomplete
          id="employeeFilterUtil"
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
              '/hr/reports/eligibility-utilization',
              filters as Record<string, string | undefined>,
              'eligibility-utilization.csv',
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
          <div className="flex flex-wrap gap-4 rounded-lg border border-slate-200 bg-white p-4 text-sm">
            <div>
              <div className="text-slate-500">Total allotted</div>
              <div className="font-semibold text-slate-900">
                {formatCurrency(data.totals.total_allotted_amount)}
              </div>
            </div>
            <div>
              <div className="text-slate-500">Total in progress</div>
              <div className="font-semibold text-amber-700">
                {formatCurrency(data.totals.total_in_progress_amount)}
              </div>
            </div>
            <div>
              <div className="text-slate-500">Total approved</div>
              <div className="font-semibold text-emerald-700">
                {formatCurrency(data.totals.total_approved_amount)}
              </div>
            </div>
          </div>

          <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
            <table className="min-w-full divide-y divide-slate-100 text-sm">
              <thead className="bg-slate-50 text-left text-xs font-medium uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-4 py-3">Employee</th>
                  <th className="px-4 py-3">Child</th>
                  <th className="px-4 py-3">FY</th>
                  <th className="px-4 py-3">Allotted</th>
                  <th className="px-4 py-3">In Progress</th>
                  <th className="px-4 py-3">Approved</th>
                  <th className="px-4 py-3">Remaining*</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {data.rows.map((row) => (
                  <tr key={row.eligibility_id}>
                    <td className="px-4 py-3 text-slate-800">{row.employee_name}</td>
                    <td className="px-4 py-3 text-slate-600">{row.child_name}</td>
                    <td className="px-4 py-3 text-slate-600">{row.financial_year}</td>
                    <td className="px-4 py-3 text-slate-600">
                      {formatCurrency(row.allotted_amount)}
                    </td>
                    <td className="px-4 py-3 text-amber-700">
                      {formatCurrency(row.in_progress_amount)}
                    </td>
                    <td className="px-4 py-3 text-emerald-700">
                      {formatCurrency(row.approved_amount)}
                    </td>
                    <td className="px-4 py-3 text-slate-600">
                      {formatCurrency(row.remaining_after_approved)}
                    </td>
                  </tr>
                ))}
                {data.rows.length === 0 && (
                  <tr>
                    <td colSpan={7} className="px-4 py-6 text-center text-slate-400">
                      No eligibility records match these filters.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </div>
          <p className="text-xs text-slate-400">
            *Remaining after approved claims only — does not reserve against claims still in
            progress.
          </p>
        </>
      )}
    </div>
  )
}
