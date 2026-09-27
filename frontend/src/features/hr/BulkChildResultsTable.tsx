import { CheckCircle2, Download, XCircle } from 'lucide-react'

import type { BulkChildRowResult } from '../../api/hr'
import { downloadBulkResultsCsv } from './bulkChildResultsCsv'

export function BulkChildResultsTable({ results }: { results: BulkChildRowResult[] }) {
  return (
    <div className="overflow-x-auto rounded-lg border border-slate-200">
      <table className="min-w-full divide-y divide-slate-100 text-sm">
        <thead className="bg-slate-50 text-left text-xs font-medium uppercase tracking-wide text-slate-500">
          <tr>
            <th className="px-3 py-2">Row</th>
            <th className="px-3 py-2">Employee ID</th>
            <th className="px-3 py-2">Child</th>
            <th className="px-3 py-2">DOB</th>
            <th className="px-3 py-2">Status</th>
            <th className="px-3 py-2">Details</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {results.map((row) => (
            <tr key={row.row_number} className={row.status === 'failed' ? 'bg-red-50' : undefined}>
              <td className="px-3 py-2 text-slate-500">{row.row_number}</td>
              <td className="px-3 py-2 text-slate-700">{row.employee_id}</td>
              <td className="px-3 py-2 text-slate-700">{row.child_name}</td>
              <td className="px-3 py-2 text-slate-700">{row.child_dob}</td>
              <td className="px-3 py-2">
                {row.status === 'created' ? (
                  <span className="flex items-center gap-1 font-medium text-emerald-700">
                    <CheckCircle2 className="h-3.5 w-3.5" aria-hidden="true" />
                    Success
                  </span>
                ) : (
                  <span className="flex items-center gap-1 font-medium text-red-700">
                    <XCircle className="h-3.5 w-3.5" aria-hidden="true" />
                    Failed
                  </span>
                )}
              </td>
              <td className="px-3 py-2 text-slate-500">{row.message ?? '—'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

export function DownloadResultsButton({
  results,
  filename,
}: {
  results: BulkChildRowResult[]
  filename: string
}) {
  return (
    <button
      type="button"
      onClick={() => downloadBulkResultsCsv(results, filename)}
      className="flex items-center gap-1.5 text-sm font-medium text-indigo-700 hover:underline"
    >
      <Download className="h-4 w-4" aria-hidden="true" />
      Download results as CSV
    </button>
  )
}
