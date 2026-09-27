import { useMutation, useQueryClient } from '@tanstack/react-query'
import { isAxiosError } from 'axios'
import { AlertCircle, CheckCircle2, Download, Loader2, Upload } from 'lucide-react'
import { useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { toast } from 'sonner'

import { commitBulkAddChildren, previewBulkAddChildren, type BulkAddChildrenResponse } from '../../api/hr'
import { BulkChildResultsTable, DownloadResultsButton } from './BulkChildResultsTable'

function extractErrorMessage(error: unknown): string {
  if (isAxiosError(error)) {
    const backendMessage = error.response?.data?.message
    if (typeof backendMessage === 'string') {
      return backendMessage
    }
  }
  return 'Something went wrong. Please try again.'
}

function downloadTemplate() {
  const csv = 'employee_id,child_name,child_dob\n91000001,Example Child,2023-01-01\n'
  const blob = new Blob([csv], { type: 'text/csv' })
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = 'add-children-template.csv'
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.URL.revokeObjectURL(url)
}

export function HRBulkAddChildPage() {
  const queryClient = useQueryClient()
  const fileInputRef = useRef<HTMLInputElement>(null)

  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<BulkAddChildrenResponse | null>(null)
  const [committed, setCommitted] = useState<BulkAddChildrenResponse | null>(null)

  const previewMutation = useMutation({
    mutationFn: (f: File) => previewBulkAddChildren(f),
    onSuccess: (data) => setPreview(data),
    onError: (error) => toast.error(extractErrorMessage(error)),
  })

  const commitMutation = useMutation({
    mutationFn: (f: File) => commitBulkAddChildren(f),
    onSuccess: async (data) => {
      await queryClient.invalidateQueries({ queryKey: ['children'] })
      setCommitted(data)
    },
    onError: (error) => toast.error(extractErrorMessage(error)),
  })

  function resetAll() {
    setFile(null)
    setPreview(null)
    setCommitted(null)
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Bulk Add Children</h1>
        <p className="mt-1 text-slate-600">
          Upload a CSV to add children for several employees at once. Every row goes through
          the same rules as adding one child at a time — including the two-child limit — so one
          bad row won't block the rest of the file.
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-4">
        <button
          type="button"
          onClick={downloadTemplate}
          className="flex items-center gap-1.5 text-sm font-medium text-indigo-700 hover:underline"
        >
          <Download className="h-4 w-4" aria-hidden="true" />
          Download CSV template
        </button>
        <Link
          to="/hr/children/bulk/history"
          className="text-sm font-medium text-indigo-700 hover:underline"
        >
          View past uploads
        </Link>
      </div>

      {!committed && (
        <div className="space-y-4 rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <div>
            <label htmlFor="bulkFile" className="block text-sm font-medium text-slate-700">
              CSV file
            </label>
            <p className="mt-1 text-sm text-slate-500">
              Columns: <code>employee_id</code>, <code>child_name</code>, <code>child_dob</code>{' '}
              (YYYY-MM-DD or DD-MM-YYYY).
            </p>
            <input
              id="bulkFile"
              ref={fileInputRef}
              type="file"
              accept=".csv,text/csv"
              onChange={(e) => {
                setFile(e.target.files?.[0] ?? null)
                setPreview(null)
              }}
              className="mt-2 block w-full text-sm text-slate-600"
            />
          </div>

          {!preview && (
            <button
              type="button"
              disabled={!file || previewMutation.isPending}
              onClick={() => file && previewMutation.mutate(file)}
              className="flex items-center gap-1.5 rounded-md bg-indigo-700 px-4 py-2 text-sm font-medium text-white transition hover:bg-indigo-800 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {previewMutation.isPending ? (
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
              ) : (
                <Upload className="h-4 w-4" aria-hidden="true" />
              )}
              Preview
            </button>
          )}
        </div>
      )}

      {preview && !committed && (
        <div className="space-y-4">
          <div className="flex items-start gap-2 rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
            This is a preview only — nothing has been added yet. {preview.succeeded} of{' '}
            {preview.total_rows} row(s) will succeed if you confirm.
          </div>

          <BulkChildResultsTable results={preview.results} />

          <div className="flex gap-2">
            <button
              type="button"
              onClick={resetAll}
              className="rounded-md px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100"
            >
              Choose a different file
            </button>
            <button
              type="button"
              disabled={preview.succeeded === 0 || commitMutation.isPending}
              onClick={() => file && commitMutation.mutate(file)}
              className="flex items-center gap-1.5 rounded-md bg-indigo-700 px-4 py-2 text-sm font-medium text-white transition hover:bg-indigo-800 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {commitMutation.isPending && (
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
              )}
              Confirm and add {preview.succeeded} child
              {preview.succeeded === 1 ? '' : 'ren'}
            </button>
          </div>
        </div>
      )}

      {committed && (
        <div className="space-y-4">
          <div className="flex items-start gap-2 rounded-md border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-800">
            <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
            Added {committed.succeeded} of {committed.total_rows} child
            {committed.total_rows === 1 ? '' : 'ren'}.
          </div>

          <BulkChildResultsTable results={committed.results} />

          <DownloadResultsButton results={committed.results} filename="bulk-add-children-results.csv" />

          <button
            type="button"
            onClick={resetAll}
            className="rounded-md border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            Upload another file
          </button>
        </div>
      )}
    </div>
  )
}
