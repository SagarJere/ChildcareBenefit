import type { Claim } from '../../api/claims'
import { LABELS, STYLES } from './claimStatusStyles'

export function ClaimStatusBadge({ status }: { status: Claim['claim_status'] }) {
  return (
    <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${STYLES[status]}`}>
      {LABELS[status]}
    </span>
  )
}
