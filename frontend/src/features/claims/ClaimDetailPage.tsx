import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { isAxiosError } from 'axios'
import {
  AlertCircle,
  ArrowLeft,
  FileCheck2,
  Loader2,
  Send,
  Upload,
} from 'lucide-react'
import { Fragment, useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { toast } from 'sonner'

import type { AttachmentType } from '../../api/claims'
import { getClaim, submitClaim, updateClaim, uploadAttachment } from '../../api/claims'
import { formatCurrency, formatDate, formatMonthYear } from '../../lib/format'
import { ClaimStatusBadge } from './ClaimStatusBadge'
import { invoiceDetailsSchema, type InvoiceDetailsFormValues } from './claimSchema'

const EDITABLE_STATUSES = new Set(['Draft', 'SentBack'])

function extractErrorMessage(error: unknown): string {
  if (isAxiosError(error)) {
    const backendMessage = error.response?.data?.message
    if (typeof backendMessage === 'string') {
      return backendMessage
    }
  }
  return 'Something went wrong. Please try again.'
}

export function ClaimDetailPage() {
  const { claimId } = useParams<{ claimId: string }>()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const numericClaimId = Number(claimId)

  const [uploadingType, setUploadingType] = useState<AttachmentType | null>(null)

  const claimQuery = useQuery({
    queryKey: ['claim', numericClaimId],
    queryFn: () => getClaim(numericClaimId),
  })

  const invalidate = () =>
    Promise.all([
      queryClient.invalidateQueries({ queryKey: ['claim', numericClaimId] }),
      queryClient.invalidateQueries({ queryKey: ['claims'] }),
    ])

  const updateMutation = useMutation({
    mutationFn: (values: InvoiceDetailsFormValues) =>
      updateClaim(numericClaimId, {
        invoice_date: values.invoiceDate,
        invoice_number: values.invoiceNumber,
        invoice_amount: values.invoiceAmount,
        comments: values.comments?.trim() || undefined,
      }),
    onSuccess: async () => {
      await invalidate()
      toast.success('Claim updated.')
    },
    onError: (error) => toast.error(extractErrorMessage(error)),
  })

  const uploadMutation = useMutation({
    mutationFn: ({ type, file }: { type: AttachmentType; file: File }) =>
      uploadAttachment(numericClaimId, type, file),
    onMutate: ({ type }) => setUploadingType(type),
    onSuccess: async (attachment) => {
      await invalidate()
      toast.success(`${attachment.original_file_name} uploaded.`)
    },
    onError: (error) => toast.error(extractErrorMessage(error)),
    onSettled: () => setUploadingType(null),
  })

  const submitMutation = useMutation({
    mutationFn: () => submitClaim(numericClaimId),
    onSuccess: async () => {
      await invalidate()
      toast.success('Claim submitted successfully.')
      navigate('/claims')
    },
    onError: (error) => toast.error(extractErrorMessage(error)),
  })

  if (claimQuery.isPending) {
    return (
      <div className="flex items-center gap-2 text-slate-600">
        <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
        Loading claim…
      </div>
    )
  }

  if (claimQuery.isError || !claimQuery.data) {
    return (
      <div className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">
        <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
        Could not load this claim.
      </div>
    )
  }

  const claim = claimQuery.data
  const isEditable = EDITABLE_STATUSES.has(claim.claim_status)
  const latestSentBack = [...claim.approval_history]
    .reverse()
    .find((entry) => entry.action === 'SentBack')

  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <Link to="/claims" className="flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-700">
        <ArrowLeft className="h-4 w-4" aria-hidden="true" />
        Back to My Claims
      </Link>

      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Claim #{claim.claim_id}</h1>
          <p className="mt-1 text-slate-600">{claim.child_name}</p>
        </div>
        <ClaimStatusBadge status={claim.claim_status} />
      </div>

      {claim.claim_status === 'SentBack' && latestSentBack && (
        <div className="flex items-start gap-2 rounded-md border border-orange-200 bg-orange-50 p-3 text-sm text-orange-800">
          <Send className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
          <span>
            HR sent this claim back{latestSentBack.remarks && `: "${latestSentBack.remarks}"`}.
            Correct the details below and resubmit.
          </span>
        </div>
      )}

      <ClaimDetailsForm
        claim={claim}
        isEditable={isEditable}
        onSave={(values) => updateMutation.mutate(values)}
        isSaving={updateMutation.isPending}
      />

      <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="mb-3 font-medium text-slate-900">Documents</h2>
        {!claim.requires_documents && (
          <p className="mb-3 text-sm text-slate-600">
            This claim is within the child's first 12 months, so no documents are required.
          </p>
        )}
        {isEditable ? (
          <div className="space-y-3">
            {(['RECEIPT_INVOICE', 'PAYMENT_PROOF'] as const).map((type) => {
              const uploaded = claim.attachments.find((a) => a.attachment_type === type)
              return (
                <div
                  key={type}
                  className="flex items-center justify-between rounded-md border border-slate-200 p-3"
                >
                  <div className="flex items-center gap-2 text-sm">
                    {uploaded ? (
                      <FileCheck2 className="h-4 w-4 text-emerald-600" aria-hidden="true" />
                    ) : (
                      <Upload className="h-4 w-4 text-slate-400" aria-hidden="true" />
                    )}
                    <span className="font-medium text-slate-800">
                      {type === 'RECEIPT_INVOICE' ? 'Receipt / Invoice' : 'Payment Proof'}
                    </span>
                    {uploaded && (
                      <span className="text-slate-500">— {uploaded.original_file_name}</span>
                    )}
                  </div>
                  <label className="cursor-pointer rounded-md bg-slate-100 px-3 py-1.5 text-sm font-medium text-slate-700 hover:bg-slate-200">
                    {uploadingType === type ? (
                      <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                    ) : uploaded ? (
                      'Replace'
                    ) : (
                      'Upload'
                    )}
                    <input
                      type="file"
                      accept=".pdf,.jpg,.jpeg,.png"
                      className="hidden"
                      onChange={(event) => {
                        const file = event.target.files?.[0]
                        if (file) {
                          uploadMutation.mutate({ type, file })
                        }
                        event.target.value = ''
                      }}
                    />
                  </label>
                </div>
              )
            })}
          </div>
        ) : claim.attachments.length === 0 ? (
          <p className="text-sm text-slate-500">No documents attached.</p>
        ) : (
          <ul className="space-y-2">
            {claim.attachments.map((attachment) => (
              <li
                key={attachment.attachment_id}
                className="flex items-center gap-2 rounded-md border border-slate-200 p-2.5 text-sm"
              >
                <FileCheck2 className="h-4 w-4 text-emerald-600" aria-hidden="true" />
                <span className="font-medium text-slate-800">
                  {attachment.attachment_type === 'RECEIPT_INVOICE' ? 'Receipt / Invoice' : 'Payment Proof'}
                </span>
                <span className="text-slate-500">— {attachment.original_file_name}</span>
              </li>
            ))}
          </ul>
        )}
      </div>

      {claim.payout_schedule.length > 0 && (
        <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="mb-3 font-medium text-slate-900">Payout Schedule</h2>
          <p className="mb-3 text-sm text-slate-600">
            This claim's approved amount is expected to pay out across these months.
          </p>
          <dl className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-sm">
            {claim.payout_schedule.map((entry) => (
              <Fragment key={entry.month}>
                <dt className="text-slate-500">{formatMonthYear(entry.month)}</dt>
                <dd className="text-right font-medium text-slate-900">
                  {formatCurrency(entry.allocated_amount)}
                </dd>
              </Fragment>
            ))}
          </dl>
        </div>
      )}

      {claim.approval_history.length > 0 && (
        <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="mb-3 font-medium text-slate-900">History</h2>
          <ul className="space-y-3 text-sm">
            {claim.approval_history.map((entry) => (
              <li key={entry.approval_history_id} className="border-l-2 border-slate-200 pl-3">
                <div className="font-medium text-slate-800">
                  {entry.action === 'SentBack' ? 'Sent Back' : entry.action} by HR
                </div>
                <div className="text-slate-500">{formatDate(entry.action_date.slice(0, 10))}</div>
                {entry.approved_amount && (
                  <div className="text-slate-600">
                    Approved amount: {formatCurrency(entry.approved_amount)}
                  </div>
                )}
                {entry.remarks && <div className="text-slate-600">"{entry.remarks}"</div>}
              </li>
            ))}
          </ul>
        </div>
      )}

      {isEditable && (
        <div className="flex justify-end">
          <button
            type="button"
            disabled={submitMutation.isPending}
            onClick={() => submitMutation.mutate()}
            className="flex items-center gap-1.5 rounded-md bg-indigo-700 px-4 py-2 text-sm font-medium text-white transition hover:bg-indigo-800 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {submitMutation.isPending && <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />}
            Submit Claim
          </button>
        </div>
      )}
    </div>
  )
}

function ClaimDetailsForm({
  claim,
  isEditable,
  onSave,
  isSaving,
}: {
  claim: {
    invoice_date: string
    invoice_number: string
    invoice_amount: string
    comments: string | null
  }
  isEditable: boolean
  onSave: (values: InvoiceDetailsFormValues) => void
  isSaving: boolean
}) {
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<InvoiceDetailsFormValues>({
    resolver: zodResolver(invoiceDetailsSchema),
    defaultValues: {
      invoiceDate: claim.invoice_date,
      invoiceNumber: claim.invoice_number,
      invoiceAmount: claim.invoice_amount,
      comments: claim.comments ?? '',
    },
  })

  if (!isEditable) {
    return (
      <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="mb-3 font-medium text-slate-900">Invoice</h2>
        <dl className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-sm">
          <dt className="text-slate-500">Invoice date</dt>
          <dd className="text-right font-medium text-slate-900">{formatDate(claim.invoice_date)}</dd>
          <dt className="text-slate-500">Invoice number</dt>
          <dd className="text-right font-medium text-slate-900">{claim.invoice_number}</dd>
          <dt className="text-slate-500">Invoice amount</dt>
          <dd className="text-right font-medium text-slate-900">
            {formatCurrency(claim.invoice_amount)}
          </dd>
        </dl>
        {claim.comments && (
          <div className="mt-4 border-t border-slate-100 pt-3">
            <h3 className="text-sm font-medium text-slate-700">Comments</h3>
            <p className="mt-1 text-sm text-slate-600">{claim.comments}</p>
          </div>
        )}
      </div>
    )
  }

  return (
    <form
      onSubmit={handleSubmit(onSave)}
      noValidate
      className="space-y-4 rounded-lg border border-slate-200 bg-white p-5 shadow-sm"
    >
      <h2 className="font-medium text-slate-900">Invoice details</h2>

      <div>
        <label htmlFor="invoiceDate" className="block text-sm font-medium text-slate-700">
          Invoice date
        </label>
        <input
          id="invoiceDate"
          type="date"
          max={new Date().toISOString().slice(0, 10)}
          className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          {...register('invoiceDate')}
        />
        {errors.invoiceDate && (
          <p className="mt-1 flex items-center gap-1 text-sm text-red-600">
            <AlertCircle className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
            {errors.invoiceDate.message}
          </p>
        )}
      </div>

      <div>
        <label htmlFor="invoiceNumber" className="block text-sm font-medium text-slate-700">
          Invoice number
        </label>
        <input
          id="invoiceNumber"
          type="text"
          className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          {...register('invoiceNumber')}
        />
        {errors.invoiceNumber && (
          <p className="mt-1 flex items-center gap-1 text-sm text-red-600">
            <AlertCircle className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
            {errors.invoiceNumber.message}
          </p>
        )}
      </div>

      <div>
        <label htmlFor="invoiceAmount" className="block text-sm font-medium text-slate-700">
          Invoice amount (₹)
        </label>
        <input
          id="invoiceAmount"
          type="number"
          step="0.01"
          min="0.01"
          className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          {...register('invoiceAmount')}
        />
        {errors.invoiceAmount && (
          <p className="mt-1 flex items-center gap-1 text-sm text-red-600">
            <AlertCircle className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
            {errors.invoiceAmount.message}
          </p>
        )}
      </div>

      <div>
        <label htmlFor="comments" className="block text-sm font-medium text-slate-700">
          Comments <span className="font-normal text-slate-400">(optional)</span>
        </label>
        <textarea
          id="comments"
          rows={3}
          maxLength={1000}
          className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
          {...register('comments')}
        />
        {errors.comments && (
          <p className="mt-1 flex items-center gap-1 text-sm text-red-600">
            <AlertCircle className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
            {errors.comments.message}
          </p>
        )}
      </div>

      <div className="flex justify-end">
        <button
          type="submit"
          disabled={isSaving}
          className="flex items-center gap-1.5 rounded-md bg-slate-700 px-4 py-2 text-sm font-medium text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {isSaving && <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />}
          Save changes
        </button>
      </div>
    </form>
  )
}
