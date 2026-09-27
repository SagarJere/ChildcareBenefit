import { useQuery } from '@tanstack/react-query'
import { CheckCircle2, Download, Loader2, XCircle } from 'lucide-react'
import { useState } from 'react'

import { downloadReportCsv, getChildDetails, type ChildDetailsFilters } from '../../api/reports'
import { EmployeeAutocomplete } from '../../components/EmployeeAutocomplete'
import { calculateAge, formatDate, formatDateTime } from '../../lib/format'

export function ChildDetailsReport() {
  const [filters, setFilters] = useState<ChildDetailsFilters>({})

  const { data, isPending, isError } = useQuery({
    queryKey: ['report-child-details', filters],
    queryFn: () => getChildDetails(filters),
  })

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end gap-3 rounded-lg border border-slate-200 bg-white p-4">
        <EmployeeAutocomplete
          id="employeeFilterChildDetails"
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
              '/hr/reports/child-details',
              filters as Record<string, string | undefined>,
              'child-details.csv',
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
        <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
          <table className="min-w-full divide-y divide-slate-100 text-sm">
            <thead className="bg-slate-50 text-left text-xs font-medium uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-3">Employee ID</th>
                <th className="px-4 py-3">Employee</th>
                <th className="px-4 py-3">Child ID</th>
                <th className="px-4 py-3">Seq</th>
                <th className="px-4 py-3">Child Name</th>
                <th className="px-4 py-3">DOB</th>
                <th className="px-4 py-3">Age</th>
                <th className="px-4 py-3">Active</th>
                <th className="px-4 py-3">Created</th>
                <th className="px-4 py-3">Created By</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {data.rows.map((row) => (
                <tr key={row.child_id}>
                  <td className="px-4 py-3 text-slate-600">{row.employee_id}</td>
                  <td className="px-4 py-3 text-slate-800">{row.employee_name}</td>
                  <td className="px-4 py-3 text-slate-600">{row.child_id}</td>
                  <td className="px-4 py-3 text-slate-600">{row.child_sequence_no}</td>
                  <td className="px-4 py-3 text-slate-800">{row.child_name}</td>
                  <td className="px-4 py-3 text-slate-600">{formatDate(row.child_dob)}</td>
                  <td className="px-4 py-3 text-slate-600">{calculateAge(row.child_dob)}</td>
                  <td className="px-4 py-3">
                    {row.is_active ? (
                      <span className="flex items-center gap-1 font-medium text-emerald-700">
                        <CheckCircle2 className="h-3.5 w-3.5" aria-hidden="true" />
                        Active
                      </span>
                    ) : (
                      <span className="flex items-center gap-1 font-medium text-slate-400">
                        <XCircle className="h-3.5 w-3.5" aria-hidden="true" />
                        Inactive
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-slate-500">
                    {formatDateTime(row.created_date)}
                  </td>
                  <td className="px-4 py-3 text-slate-500">{row.created_by}</td>
                </tr>
              ))}
              {data.rows.length === 0 && (
                <tr>
                  <td colSpan={10} className="px-4 py-6 text-center text-slate-400">
                    No children match these filters.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
