import { useQuery } from '@tanstack/react-query'
import { AlertTriangle, ArrowLeft, Loader2 } from 'lucide-react'
import { Link, useParams } from 'react-router-dom'

import { getBulkUploadBatch } from '../../api/hr'
import { formatDateTime } from '../../lib/format'
import { BulkChildResultsTable, DownloadResultsButton } from './BulkChildResultsTable'

export function HRBulkUploadHistoryDetailPage() {
  const { bulkUploadId } = useParams<{ bulkUploadId: string }>()

  const { data, isPending, isError } = useQuery({
    queryKey: ['bulk-upload-history', bulkUploadId],
    queryFn: () => getBulkUploadBatch(Number(bulkUploadId)),
  })

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <Link
        to="/hr/children/bulk/history"
        className="flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-700"
      >
        <ArrowLeft className="h-4 w-4" aria-hidden="true" />
        Back to Bulk Upload History
      </Link>

      {isPending && (
        <div className="flex items-center gap-2 text-slate-600">
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
          Loading…
        </div>
      )}

      {isError && (
        <div className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
          Could not load this upload — it may not exist.
        </div>
      )}

      {data && (
        <>
          <div>
            <h1 className="text-2xl font-semibold text-slate-900">
              Upload from {formatDateTime(data.uploaded_date)}
            </h1>
            <p className="mt-1 text-slate-600">
              Uploaded by {data.uploaded_by}
              {data.uploaded_file_name && <> from &ldquo;{data.uploaded_file_name}&rdquo;</>} —{' '}
              {data.succeeded_count} of {data.total_rows} row(s) succeeded, {data.failed_count}{' '}
              failed.
            </p>
          </div>

          <BulkChildResultsTable results={data.results} />

          <DownloadResultsButton
            results={data.results}
            filename={`bulk-add-children-${data.bulk_upload_id}.csv`}
          />
        </>
      )}
    </div>
  )
}
