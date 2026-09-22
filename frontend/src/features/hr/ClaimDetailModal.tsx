import { useQuery } from '@tanstack/react-query'
import { AlertCircle, ArrowRight, Download, Loader2 } from 'lucide-react'
import { Fragment } from 'react'
import { Link } from 'react-router-dom'
import { toast } from 'sonner'
import { isAxiosError } from 'axios'

import { downloadHRAttachment, getHRClaimDetail } from '../../api/hr'
import { CollapsibleSection } from '../../components/CollapsibleSection'
import { Modal } from '../../components/Modal'
import { formatCurrency, formatDate, formatMonthYear } from '../../lib/format'
import { EligibilitySummary } from '../children/EligibilitySummary'
import { ClaimStatusBadge } from '../claims/ClaimStatusBadge'

function extractErrorMessage(error: unknown): string {
  if (isAxiosError(error)) {
    const backendMessage = error.response?.data?.message
    if (typeof backendMessage === 'string') {
      return backendMessage
    }
  }
  return 'Something went wrong. Please try again.'
}

/** A read-only claim-detail popup for use from report pages — shows the
 * same information as the full HR claim detail page (invoice, documents,
 * eligibility, payout schedule, approval history), minus the approve/
 * reject/send-back actions, which stay on the dedicated page it links
 * out to. */
export function ClaimDetailModal({
  claimId,
  onClose,
}: {
  claimId: number
  onClose: () => void
}) {
  const { data: claim, isPending, isError } = useQuery({
    queryKey: ['hr-claim', claimId],
    queryFn: () => getHRClaimDetail(claimId),
  })

  return (
    <Modal title={`Claim #${claimId}`} onClose={onClose}>
      {isPending && (
        <div className="flex items-center gap-2 text-slate-600">
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
          Loading…
        </div>
      )}
      {isError && (
        <div className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
          Could not load this claim.
        </div>
      )}
      {claim && (
        <div className="space-y-5">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-sm text-slate-600">
              {claim.employee_name} ({claim.employee_id}) — {claim.child_name}
            </p>
            <ClaimStatusBadge status={claim.claim_status} />
          </div>

          <div className="rounded-lg border-l-4 border-l-indigo-500 border-y border-r border-slate-200 bg-indigo-50/40 p-4">
            <h3 className="mb-2 text-sm font-medium text-slate-900">Invoice</h3>
            <dl className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-sm">
              <dt className="text-slate-500">Invoice date</dt>
              <dd className="text-right font-medium text-slate-900">
                {formatDate(claim.invoice_date)}
              </dd>
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
              <div className="mt-3 border-t border-slate-200 pt-3">
                <h4 className="text-xs font-medium text-slate-700">Employee comments</h4>
                <p className="mt-1 text-sm text-slate-600">{claim.comments}</p>
              </div>
            )}
          </div>

          <div>
            <h3 className="mb-2 text-sm font-medium text-slate-900">Documents</h3>
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
                        {attachment.attachment_type === 'RECEIPT_INVOICE'
                          ? 'Receipt / Invoice'
                          : 'Payment Proof'}
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
            <div>
              <h3 className="mb-2 text-sm font-medium text-slate-900">History</h3>
              <ul className="space-y-3 text-sm">
                {claim.approval_history.map((entry) => (
                  <li key={entry.approval_history_id} className="border-l-2 border-slate-200 pl-3">
                    <div className="font-medium text-slate-800">
                      {entry.action} by {entry.action_by}
                    </div>
                    <div className="text-slate-500">
                      {formatDate(entry.action_date.slice(0, 10))}
                    </div>
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

          <Link
            to={`/hr/claims/${claim.claim_id}`}
            onClick={onClose}
            className="flex items-center gap-1 text-sm font-medium text-indigo-700 hover:underline"
          >
            Open full claim page
            <ArrowRight className="h-3.5 w-3.5" aria-hidden="true" />
          </Link>
        </div>
      )}
    </Modal>
  )
}
