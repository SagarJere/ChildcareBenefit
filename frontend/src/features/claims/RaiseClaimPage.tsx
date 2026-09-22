import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { isAxiosError } from 'axios'
import {
  AlertCircle,
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  FileCheck2,
  Loader2,
  Upload,
} from 'lucide-react'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link, useNavigate } from 'react-router-dom'
import { toast } from 'sonner'

import type { AttachmentType, Claim } from '../../api/claims'
import { createClaim, submitClaim, uploadAttachment } from '../../api/claims'
import { listChildren } from '../../api/children'
import {
  formatCurrency,
  formatDate,
  formatDateObject,
  hasCrossedSixYearLimit,
  sixYearCutoffDate,
  sixthBirthdayDate,
} from '../../lib/format'
import { EligibilitySummary } from '../children/EligibilitySummary'
import { invoiceDetailsSchema, type InvoiceDetailsFormValues } from './claimSchema'

const STEP_LABELS = [
  'Select child',
  'Invoice details',
  'Upload documents',
  'Eligibility',
  'Review & submit',
]

function extractErrorMessage(error: unknown): string {
  if (isAxiosError(error)) {
    const backendMessage = error.response?.data?.message
    if (typeof backendMessage === 'string') {
      return backendMessage
    }
  }
  return 'Something went wrong. Please try again.'
}

function StepIndicator({ step }: { step: number }) {
  return (
    <ol className="flex flex-wrap gap-2 text-xs font-medium">
      {STEP_LABELS.map((label, index) => {
        const stepNumber = index + 1
        const isCurrent = stepNumber === step
        const isDone = stepNumber < step
        return (
          <li
            key={label}
            className={`flex items-center gap-1.5 rounded-full px-3 py-1 ${
              isCurrent
                ? 'bg-indigo-700 text-white'
                : isDone
                  ? 'bg-emerald-100 text-emerald-700'
                  : 'bg-slate-100 text-slate-500'
            }`}
          >
            {isDone && <CheckCircle2 className="h-3.5 w-3.5" aria-hidden="true" />}
            {stepNumber}. {label}
          </li>
        )
      })}
    </ol>
  )
}

export function RaiseClaimPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const [step, setStep] = useState(1)
  const [selectedChildId, setSelectedChildId] = useState<string | null>(null)
  const [claim, setClaim] = useState<Claim | null>(null)
  const [uploadingType, setUploadingType] = useState<AttachmentType | null>(null)

  const childrenQuery = useQuery({ queryKey: ['children'], queryFn: listChildren })
  const selectedChild = childrenQuery.data?.find((c) => c.child_id === selectedChildId) ?? null

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<InvoiceDetailsFormValues>({
    resolver: zodResolver(invoiceDetailsSchema),
    defaultValues: { invoiceDate: '', invoiceNumber: '', invoiceAmount: '', comments: '' },
  })

  const createMutation = useMutation({
    mutationFn: (values: InvoiceDetailsFormValues) =>
      createClaim({
        child_id: selectedChildId!,
        invoice_date: values.invoiceDate,
        invoice_number: values.invoiceNumber,
        invoice_amount: values.invoiceAmount,
        comments: values.comments?.trim() || undefined,
      }),
    onSuccess: (created) => {
      setClaim(created)
      setStep(3)
    },
    onError: (error) => toast.error(extractErrorMessage(error)),
  })

  const uploadMutation = useMutation({
    mutationFn: ({ type, file }: { type: AttachmentType; file: File }) =>
      uploadAttachment(claim!.claim_id, type, file),
    onMutate: ({ type }) => setUploadingType(type),
    onSuccess: (attachment) => {
      setClaim((prev) => (prev ? { ...prev, attachments: [...prev.attachments, attachment] } : prev))
      toast.success(`${attachment.original_file_name} uploaded.`)
    },
    onError: (error) => toast.error(extractErrorMessage(error)),
    onSettled: () => setUploadingType(null),
  })

  const submitMutation = useMutation({
    mutationFn: () => submitClaim(claim!.claim_id),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['claims'] })
      toast.success('Claim submitted successfully.')
      navigate('/claims')
    },
    onError: (error) => toast.error(extractErrorMessage(error)),
  })

  return (
    <div className="mx-auto max-w-4xl space-y-6">
      <Link to="/claims" className="flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-700">
        <ArrowLeft className="h-4 w-4" aria-hidden="true" />
        Back to My Claims
      </Link>

      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Raise Claim</h1>
        <StepIndicator step={step} />
      </div>

      <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        {step === 1 && (
          <div className="space-y-4">
            <h2 className="font-medium text-slate-900">Select a child</h2>
            {childrenQuery.isPending && (
              <div className="flex items-center gap-2 text-slate-500">
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                Loading children…
              </div>
            )}
            {childrenQuery.data?.length === 0 && (
              <p className="text-sm text-slate-600">
                You have no children on record. Add a child first from{' '}
                <Link to="/children" className="text-indigo-700 underline">
                  My Children
                </Link>
                .
              </p>
            )}
            <div className="space-y-2">
              {childrenQuery.data?.map((child) => {
                const agedOut = hasCrossedSixYearLimit(child.child_dob)
                return (
                  <label
                    key={child.child_id}
                    className={`flex cursor-pointer items-center gap-3 rounded-md border px-3 py-2.5 transition ${
                      selectedChildId === child.child_id
                        ? 'border-indigo-500 bg-indigo-50'
                        : 'border-slate-200 hover:bg-slate-50'
                    }`}
                  >
                    <input
                      type="radio"
                      name="child"
                      className="h-4 w-4"
                      checked={selectedChildId === child.child_id}
                      onChange={() => setSelectedChildId(child.child_id)}
                    />
                    <span className="text-sm">
                      <span className="font-medium text-slate-900">{child.child_name}</span>{' '}
                      <span className="text-slate-500">· {formatDate(child.child_dob)}</span>
                      {agedOut && (
                        <span className="ml-2 inline-flex items-center gap-1 rounded-full bg-amber-100 px-2 py-0.5 text-xs font-medium text-amber-700">
                          <AlertTriangle className="h-3 w-3" aria-hidden="true" />
                          Already turned 6
                        </span>
                      )}
                    </span>
                  </label>
                )
              })}
            </div>

            {selectedChild && hasCrossedSixYearLimit(selectedChild.child_dob) && (
              <div className="flex items-start gap-2 rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
                <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
                <span>
                  {selectedChild.child_name} turned 6 on{' '}
                  {formatDateObject(sixthBirthdayDate(selectedChild.child_dob))}. Benefit
                  eligibility ended {formatDateObject(sixYearCutoffDate(selectedChild.child_dob))}{' '}
                  and no new eligibility is accruing. You can still raise a claim here for an
                  invoice dated on or before that.
                </span>
              </div>
            )}

            <button
              type="button"
              disabled={!selectedChildId}
              onClick={() => setStep(2)}
              className="flex items-center gap-1.5 rounded-md bg-indigo-700 px-4 py-2 text-sm font-medium text-white transition hover:bg-indigo-800 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Next
              <ArrowRight className="h-4 w-4" aria-hidden="true" />
            </button>
          </div>
        )}

        {step === 2 && (
          <form
            onSubmit={handleSubmit((values) => createMutation.mutate(values))}
            noValidate
            className="space-y-4"
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
                onWheel={(e) => e.currentTarget.blur()}
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

            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setStep(1)}
                className="rounded-md px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100"
              >
                Back
              </button>
              <button
                type="submit"
                disabled={createMutation.isPending}
                className="flex items-center gap-1.5 rounded-md bg-indigo-700 px-4 py-2 text-sm font-medium text-white transition hover:bg-indigo-800 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {createMutation.isPending && (
                  <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                )}
                Next
                <ArrowRight className="h-4 w-4" aria-hidden="true" />
              </button>
            </div>
          </form>
        )}

        {step === 3 && claim && (
          <div className="space-y-4">
            <h2 className="font-medium text-slate-900">Upload documents</h2>
            {!claim.requires_documents ? (
              <p className="text-sm text-slate-600">
                This claim is within the child's first 12 months, so no documents are required.
                You may continue.
              </p>
            ) : (
              <p className="text-sm text-slate-600">
                This claim is for the child's 13th month or later. A receipt/invoice and payment
                proof are recommended, but uploading them is optional for now — you may continue
                without them.
              </p>
            )}

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

            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setStep(2)}
                className="rounded-md px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100"
              >
                Back
              </button>
              <button
                type="button"
                onClick={() => setStep(4)}
                className="flex items-center gap-1.5 rounded-md bg-indigo-700 px-4 py-2 text-sm font-medium text-white transition hover:bg-indigo-800"
              >
                Next
                <ArrowRight className="h-4 w-4" aria-hidden="true" />
              </button>
            </div>
          </div>
        )}

        {step === 4 && selectedChild && (
          <div className="space-y-4">
            <h2 className="font-medium text-slate-900">Eligibility for {selectedChild.child_name}</h2>
            {selectedChild.eligibility ? (
              <EligibilitySummary
                financialYear={selectedChild.eligibility.financial_year}
                eligibilityStartDate={selectedChild.eligibility.eligibility_start_date}
                eligibilityEndDate={selectedChild.eligibility.eligibility_end_date}
                eligibleMonths={selectedChild.eligibility.eligible_months}
                monthlyBenefitAmount={selectedChild.eligibility.monthly_benefit_amount}
                allottedAmount={selectedChild.eligibility.allotted_amount}
                remainingAmount={selectedChild.eligibility.remaining_amount}
              />
            ) : (
              <p className="text-sm text-slate-500">No eligibility on record for this child.</p>
            )}
            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setStep(3)}
                className="rounded-md px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100"
              >
                Back
              </button>
              <button
                type="button"
                onClick={() => setStep(5)}
                className="flex items-center gap-1.5 rounded-md bg-indigo-700 px-4 py-2 text-sm font-medium text-white transition hover:bg-indigo-800"
              >
                Next
                <ArrowRight className="h-4 w-4" aria-hidden="true" />
              </button>
            </div>
          </div>
        )}

        {step === 5 && claim && selectedChild && (
          <div className="space-y-4">
            <h2 className="font-medium text-slate-900">Review & submit</h2>
            <dl className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-sm">
              <dt className="text-slate-500">Child</dt>
              <dd className="text-right font-medium text-slate-900">{selectedChild.child_name}</dd>
              <dt className="text-slate-500">Invoice date</dt>
              <dd className="text-right font-medium text-slate-900">
                {formatDate(claim.invoice_date)}
              </dd>
              <dt className="text-slate-500">Invoice number</dt>
              <dd className="text-right font-medium text-slate-900">{claim.invoice_number}</dd>
              <dt className="text-slate-500">Amount</dt>
              <dd className="text-right font-medium text-slate-900">
                {formatCurrency(claim.invoice_amount)}
              </dd>
              <dt className="text-slate-500">Documents</dt>
              <dd className="text-right font-medium text-slate-900">
                {claim.attachments.length === 0
                  ? 'None'
                  : claim.attachments.map((a) => a.original_file_name).join(', ')}
              </dd>
              {claim.comments && (
                <>
                  <dt className="text-slate-500">Comments</dt>
                  <dd className="text-right font-medium text-slate-900">{claim.comments}</dd>
                </>
              )}
            </dl>

            <div className="flex gap-2">
              <button
                type="button"
                onClick={() => setStep(4)}
                className="rounded-md px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100"
              >
                Back
              </button>
              <button
                type="button"
                disabled={submitMutation.isPending}
                onClick={() => submitMutation.mutate()}
                className="flex items-center gap-1.5 rounded-md bg-indigo-700 px-4 py-2 text-sm font-medium text-white transition hover:bg-indigo-800 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {submitMutation.isPending && (
                  <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                )}
                Submit Claim
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
