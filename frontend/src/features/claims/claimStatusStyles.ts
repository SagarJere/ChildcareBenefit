import type { Claim } from '../../api/claims'

// Shared by ClaimStatusBadge and any other view that needs to stay
// visually consistent with it (e.g. the Claims Summary report's status
// counts) — the same status should always carry the same color everywhere
// in the app. Kept in its own file, not ClaimStatusBadge.tsx, so that
// component file only exports the component (React Fast Refresh needs
// this to work reliably).
export const STYLES: Record<Claim['claim_status'], string> = {
  Draft: 'bg-slate-100 text-slate-600',
  Submitted: 'bg-blue-100 text-blue-700',
  HRReview: 'bg-amber-100 text-amber-700',
  Approved: 'bg-emerald-100 text-emerald-700',
  Rejected: 'bg-red-100 text-red-700',
  SentBack: 'bg-orange-100 text-orange-700',
}

export const LABELS: Record<Claim['claim_status'], string> = {
  Draft: 'Draft',
  Submitted: 'Submitted',
  HRReview: 'HR Review',
  Approved: 'Approved',
  Rejected: 'Rejected',
  SentBack: 'Sent Back',
}
