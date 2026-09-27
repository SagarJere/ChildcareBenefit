import { useQuery } from '@tanstack/react-query'
import { AlertTriangle, History, Loader2 } from 'lucide-react'
import { Link } from 'react-router-dom'

import { getBulkUploadHistory } from '../../api/hr'
import { formatDateTime } from '../../lib/format'

export function HRBulkUploadHistoryPage() {
  const { data, isPending, isError } = useQuery({
    queryKey: ['bulk-upload-history'],
    queryFn: getBulkUploadHistory,
  })

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Bulk Upload History</h1>
        <p className="mt-1 text-slate-600">
          Every bulk-add-children file that's actually been committed, with the outcome of every
          row — the record to point to if a later question comes up about what was uploaded and
          what happened to it.
        </p>
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
          Could not load upload history.
        </div>
      )}

      {data && data.length === 0 && (
        <div className="flex flex-col items-center gap-3 rounded-lg border border-dashed border-slate-300 bg-white px-6 py-12 text-center">
          <History className="h-8 w-8 text-slate-300" aria-hidden="true" />
          <p className="text-slate-600">No bulk uploads have been committed yet.</p>
        </div>
      )}

      {data && data.length > 0 && (
        <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white shadow-sm">
          <table className="min-w-full divide-y divide-slate-100 text-sm">
            <thead className="bg-slate-50 text-left text-xs font-medium uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-3">Uploaded</th>
                <th className="px-4 py-3">By</th>
                <th className="px-4 py-3">File</th>
                <th className="px-4 py-3">Rows</th>
                <th className="px-4 py-3">Succeeded</th>
                <th className="px-4 py-3">Failed</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {data.map((batch) => (
                <tr key={batch.bulk_upload_id} className="hover:bg-slate-50">
                  <td className="px-4 py-3">
                    <Link
                      to={`/hr/children/bulk/history/${batch.bulk_upload_id}`}
                      className="font-medium text-indigo-700 hover:underline"
                    >
                      {formatDateTime(batch.uploaded_date)}
                    </Link>
                  </td>
                  <td className="px-4 py-3 text-slate-600">{batch.uploaded_by}</td>
                  <td className="px-4 py-3 text-slate-600">{batch.uploaded_file_name ?? '—'}</td>
                  <td className="px-4 py-3 text-slate-600">{batch.total_rows}</td>
                  <td className="px-4 py-3 font-medium text-emerald-700">
                    {batch.succeeded_count}
                  </td>
                  <td className="px-4 py-3 font-medium text-red-700">{batch.failed_count}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
