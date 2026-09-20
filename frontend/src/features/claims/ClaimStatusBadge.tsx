import type { Claim } from '../../api/claims'

const STYLES: Record<Claim['claim_status'], string> = {
  Draft: 'bg-slate-100 text-slate-600',
  Submitted: 'bg-blue-100 text-blue-700',
  HRReview: 'bg-amber-100 text-amber-700',
  Approved: 'bg-emerald-100 text-emerald-700',
  Rejected: 'bg-red-100 text-red-700',
  SentBack: 'bg-orange-100 text-orange-700',
}

const LABELS: Record<Claim['claim_status'], string> = {
  Draft: 'Draft',
  Submitted: 'Submitted',
  HRReview: 'HR Review',
  Approved: 'Approved',
  Rejected: 'Rejected',
  SentBack: 'Sent Back',
}

export function ClaimStatusBadge({ status }: { status: Claim['claim_status'] }) {
  return (
    <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${STYLES[status]}`}>
      {LABELS[status]}
    </span>
  )
}
