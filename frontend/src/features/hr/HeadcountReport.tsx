import { useQuery } from '@tanstack/react-query'
import { Download, Loader2 } from 'lucide-react'

import { downloadReportCsv, getHeadcount } from '../../api/reports'

export function HeadcountReport() {
  const { data, isPending, isError } = useQuery({
    queryKey: ['report-headcount'],
    queryFn: getHeadcount,
  })

  return (
    <div className="space-y-4">
      <div className="flex justify-end">
        <button
          type="button"
          onClick={() => downloadReportCsv('/hr/reports/headcount', {}, 'headcount-summary.csv')}
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
      {isError && <p className="text-red-700">Could not load this report.</p>}

      {data && (
        <>
          <div className="grid grid-cols-2 gap-4 sm:grid-cols-4">
            {[
              ['Employees with children', data.total_employees_with_children],
              ['Total children', data.total_children],
              ['Employees with 1 child', data.employees_with_one_child],
              ['Employees with 2 children', data.employees_with_two_children],
            ].map(([label, value]) => (
              <div key={label} className="rounded-lg border border-slate-200 bg-white p-4">
                <div className="text-xs text-slate-500">{label}</div>
                <div className="text-2xl font-semibold text-slate-900">{value}</div>
              </div>
            ))}
          </div>

          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
            <div className="rounded-lg border border-slate-200 bg-white p-4">
              <h3 className="mb-2 text-sm font-medium text-slate-700">
                By enrollment financial year
              </h3>
              <table className="w-full text-sm">
                <tbody className="divide-y divide-slate-100">
                  {data.by_financial_year.map((entry) => (
                    <tr key={entry.financial_year}>
                      <td className="py-1.5 text-slate-600">{entry.financial_year}</td>
                      <td className="py-1.5 text-right font-medium text-slate-900">
                        {entry.child_count}
                      </td>
                    </tr>
                  ))}
                  {data.by_financial_year.length === 0 && (
                    <tr>
                      <td className="py-3 text-center text-slate-400" colSpan={2}>
                        No data.
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>

            <div className="rounded-lg border border-slate-200 bg-white p-4">
              <h3 className="mb-2 text-sm font-medium text-slate-700">By age</h3>
              <table className="w-full text-sm">
                <tbody className="divide-y divide-slate-100">
                  {data.by_age_bracket.map((entry) => (
                    <tr key={entry.age_bracket}>
                      <td className="py-1.5 text-slate-600">{entry.age_bracket} years</td>
                      <td className="py-1.5 text-right font-medium text-slate-900">
                        {entry.child_count}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  )
}
