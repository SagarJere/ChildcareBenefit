import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { isAxiosError } from 'axios'
import {
  AlertCircle,
  ArrowLeft,
  CheckCircle2,
  Download,
  History,
  Loader2,
  Send,
  XCircle,
} from 'lucide-react'
import { Fragment, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { toast } from 'sonner'

import { approveClaim, downloadHRAttachment, getHRClaimDetail, rejectClaim, sendBackClaim } from '../../api/hr'
import { CollapsibleSection } from '../../components/CollapsibleSection'
import { EligibilitySummary } from '../children/EligibilitySummary'
import { formatCurrency, formatDate, formatMonthYear } from '../../lib/format'
import { ClaimHistoryModal } from './ClaimHistoryModal'
import { ClaimStatusBadge } from '../claims/ClaimStatusBadge'

type ActionMode = 'approve' | 'reject' | 'sendback' | null

function extractErrorMessage(error: unknown): string {
  if (isAxiosError(error)) {
    const backendMessage = error.response?.data?.message
    if (typeof backendMessage === 'string') {
      return backendMessage
    }
  }
  return 'Something went wrong. Please try again.'
}

export function HRClaimDetailPage() {
  const { claimId } = useParams<{ claimId: string }>()
  const queryClient = useQueryClient()
  const numericClaimId = Number(claimId)

  const [actionMode, setActionMode] = useState<ActionMode>(null)
  const [approvedAmount, setApprovedAmount] = useState('')
  const [remarks, setRemarks] = useState('')
  const [isHistoryOpen, setIsHistoryOpen] = useState(false)

  const claimQuery = useQuery({
    queryKey: ['hr-claim', numericClaimId],
    queryFn: () => getHRClaimDetail(numericClaimId),
  })

  const invalidateAndReset = async () => {
    await queryClient.invalidateQueries({ queryKey: ['hr-claim', numericClaimId] })
    await queryClient.invalidateQueries({ queryKey: ['hr-claims'] })
    setActionMode(null)
    setRemarks('')
  }

  const approveMutation = useMutation({
    mutationFn: () => approveClaim(numericClaimId, approvedAmount, remarks || undefined),
    onSuccess: async () => {
      toast.success('Claim approved.')
      await invalidateAndReset()
    },
    onError: (error) => toast.error(extractErrorMessage(error)),
  })

  const rejectMutation = useMutation({
    mutationFn: () => rejectClaim(numericClaimId, remarks),
    onSuccess: async () => {
      toast.success('Claim rejected.')
      await invalidateAndReset()
    },
    onError: (error) => toast.error(extractErrorMessage(error)),
  })

  const sendBackMutation = useMutation({
    mutationFn: () => sendBackClaim(numericClaimId, remarks),
    onSuccess: async () => {
      toast.success('Claim sent back to the employee.')
      await invalidateAndReset()
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
  const isReviewable = claim.claim_status === 'Submitted'
  const attachmentTypes = new Set(claim.attachments.map((a) => a.attachment_type))
  // Informational only — document upload is not mandatory for now (see
  // DECISIONS_LOG.md item 38), so this no longer blocks approval.
  const hasBothDocuments =
    attachmentTypes.has('RECEIPT_INVOICE') && attachmentTypes.has('PAYMENT_PROOF')
  // The approved amount can't exceed the invoice OR the child's remaining
  // eligibility balance for this financial year — see DECISIONS_LOG.md
  // item 44. Capping the input here avoids a round-trip just to learn
  // that; the backend still enforces both independently.
  const maxApprovable = claim.eligibility
    ? Math.min(Number(claim.invoice_amount), Number(claim.eligibility.remaining_amount))
    : Number(claim.invoice_amount)

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <Link to="/hr/claims" className="flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-700">
        <ArrowLeft className="h-4 w-4" aria-hidden="true" />
        Back to Queue
      </Link>

      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Claim #{claim.claim_id}</h1>
          <p className="mt-1 flex flex-wrap items-center gap-x-2 text-slate-600">
            <span>
              {claim.employee_name} ({claim.employee_id}) — {claim.child_name}
            </span>
            <button
              type="button"
              onClick={() => setIsHistoryOpen(true)}
              className="flex items-center gap-1 text-sm font-medium text-indigo-700 hover:underline"
            >
              <History className="h-3.5 w-3.5" aria-hidden="true" />
              View claim history
            </button>
          </p>
        </div>
        <ClaimStatusBadge status={claim.claim_status} />
      </div>

      {isHistoryOpen && (
        <ClaimHistoryModal
          employeeId={claim.employee_id}
          childId={claim.child_id}
          childName={claim.child_name}
          currentClaimId={claim.claim_id}
          onClose={() => setIsHistoryOpen(false)}
        />
      )}

      <div className="rounded-lg border-l-4 border-l-indigo-500 border-y border-r border-slate-200 bg-indigo-50/40 p-5 shadow-sm">
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
          {claim.submitted_date && (
            <>
              <dt className="text-slate-500">Submitted date</dt>
              <dd className="text-right font-medium text-slate-900">
                {formatDate(claim.submitted_date.slice(0, 10))}
              </dd>
            </>
          )}
        </dl>
        {claim.comments && (
          <div className="mt-4 border-t border-slate-100 pt-3">
            <h3 className="text-sm font-medium text-slate-700">Employee comments</h3>
            <p className="mt-1 text-sm text-slate-600">{claim.comments}</p>
          </div>
        )}
      </div>

      <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="mb-3 font-medium text-slate-900">Documents</h2>
        {claim.requires_documents && !hasBothDocuments && (
          <p className="mb-3 text-sm text-amber-700">
            This claim is for the child's 13th month or later and is missing a recommended
            document (receipt/invoice and/or payment proof). Documents are optional for now, so
            this does not block approval.
          </p>
        )}
        {claim.attachments.length === 0 ? (
          <p className="text-sm text-slate-500">No documents attached.</p>
        ) : (
          <ul className="space-y-2">
            {claim.attachments.map((attachment) => (
              <li
                key={attachment.attachment_id}
                className="flex items-center justify-between rounded-md border border-slate-200 p-2.5 text-sm"
              >
                <span>
                  <span className="font-medium text-slate-800">
                    {attachment.attachment_type === 'RECEIPT_INVOICE' ? 'Receipt / Invoice' : 'Payment Proof'}
                  </span>{' '}
                  <span className="text-slate-500">— {attachment.original_file_name}</span>
                </span>
                <button
                  type="button"
                  onClick={() =>
                    downloadHRAttachment(
                      claim.claim_id,
                      attachment.attachment_id,
                      attachment.original_file_name,
                    ).catch((error) => toast.error(extractErrorMessage(error)))
                  }
                  className="flex items-center gap-1 text-indigo-700 hover:underline"
                >
                  <Download className="h-3.5 w-3.5" aria-hidden="true" />
                  Download
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>

      {claim.eligibility && (
        <CollapsibleSection title="Eligibility" defaultOpen={false}>
          <EligibilitySummary
            financialYear={claim.eligibility.financial_year}
            eligibilityStartDate={claim.eligibility.eligibility_start_date}
            eligibilityEndDate={claim.eligibility.eligibility_end_date}
            eligibleMonths={claim.eligibility.eligible_months}
            monthlyBenefitAmount={claim.eligibility.monthly_benefit_amount}
            allottedAmount={claim.eligibility.allotted_amount}
            remainingAmount={claim.eligibility.remaining_amount}
          />
        </CollapsibleSection>
      )}

      {claim.payout_schedule.length > 0 && (
        <CollapsibleSection title="Payout Schedule" defaultOpen={false}>
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
        </CollapsibleSection>
      )}

      {claim.approval_history.length > 0 && (
        <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="mb-3 font-medium text-slate-900">History</h2>
          <ul className="space-y-3 text-sm">
            {claim.approval_history.map((entry) => (
              <li key={entry.approval_history_id} className="border-l-2 border-slate-200 pl-3">
                <div className="font-medium text-slate-800">
                  {entry.action} by {entry.action_by}
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

      {isReviewable && (
        <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="mb-3 font-medium text-slate-900">Take action</h2>

          {!actionMode && (
            <div className="flex flex-wrap gap-2">
              <button
                type="button"
                onClick={() => {
                  setApprovedAmount(maxApprovable.toString())
                  setActionMode('approve')
                }}
                className="flex items-center gap-1.5 rounded-md bg-emerald-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-emerald-700"
              >
                <CheckCircle2 className="h-4 w-4" aria-hidden="true" />
                Approve
              </button>
              <button
                type="button"
                onClick={() => setActionMode('reject')}
                className="flex items-center gap-1.5 rounded-md bg-red-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-red-700"
              >
                <XCircle className="h-4 w-4" aria-hidden="true" />
                Reject
              </button>
              <button
                type="button"
                onClick={() => setActionMode('sendback')}
                className="flex items-center gap-1.5 rounded-md bg-amber-500 px-4 py-2 text-sm font-medium text-white transition hover:bg-amber-600"
              >
                <Send className="h-4 w-4" aria-hidden="true" />
                Send Back
              </button>
            </div>
          )}

          {actionMode === 'approve' && (
            <div className="space-y-3">
              <div>
                <label htmlFor="approvedAmount" className="block text-sm font-medium text-slate-700">
                  Approved amount (₹)
                </label>
                <input
                  id="approvedAmount"
                  type="number"
                  step="0.01"
                  min="0.01"
                  max={maxApprovable}
                  value={approvedAmount}
                  onChange={(e) => setApprovedAmount(e.target.value)}
                  className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                />
                {claim.eligibility && (
                  <p className="mt-1 text-xs text-slate-500">
                    Remaining balance for {claim.eligibility.financial_year}:{' '}
                    {formatCurrency(claim.eligibility.remaining_amount)}
                  </p>
                )}
              </div>
              <div>
                <label htmlFor="approveRemarks" className="block text-sm font-medium text-slate-700">
                  Remarks (optional)
                </label>
                <textarea
                  id="approveRemarks"
                  value={remarks}
                  onChange={(e) => setRemarks(e.target.value)}
                  rows={2}
                  className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                />
              </div>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => setActionMode(null)}
                  className="rounded-md px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  disabled={
                    approveMutation.isPending ||
                    !approvedAmount ||
                    Number(approvedAmount) > maxApprovable ||
                    Number(approvedAmount) <= 0
                  }
                  onClick={() => approveMutation.mutate()}
                  className="flex items-center gap-1.5 rounded-md bg-emerald-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-emerald-700 disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {approveMutation.isPending && <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />}
                  Confirm Approval
                </button>
              </div>
            </div>
          )}

          {(actionMode === 'reject' || actionMode === 'sendback') && (
            <div className="space-y-3">
              <div>
                <label htmlFor="remarks" className="block text-sm font-medium text-slate-700">
                  Remarks (required)
                </label>
                <textarea
                  id="remarks"
                  value={remarks}
                  onChange={(e) => setRemarks(e.target.value)}
                  rows={2}
                  className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
                />
              </div>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => setActionMode(null)}
                  className="rounded-md px-4 py-2 text-sm font-medium text-slate-600 hover:bg-slate-100"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  disabled={
                    (actionMode === 'reject' ? rejectMutation.isPending : sendBackMutation.isPending) ||
                    remarks.trim().length === 0
                  }
                  onClick={() =>
                    actionMode === 'reject' ? rejectMutation.mutate() : sendBackMutation.mutate()
                  }
                  className={`flex items-center gap-1.5 rounded-md px-4 py-2 text-sm font-medium text-white transition disabled:cursor-not-allowed disabled:opacity-60 ${
                    actionMode === 'reject' ? 'bg-red-600 hover:bg-red-700' : 'bg-amber-500 hover:bg-amber-600'
                  }`}
                >
                  {(actionMode === 'reject' ? rejectMutation.isPending : sendBackMutation.isPending) && (
                    <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                  )}
                  {actionMode === 'reject' ? 'Confirm Rejection' : 'Confirm Send Back'}
                </button>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
