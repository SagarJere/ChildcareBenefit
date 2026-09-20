import { useQuery } from '@tanstack/react-query'
import { Loader2 } from 'lucide-react'
import { Link } from 'react-router-dom'

import { listHRClaims } from '../../api/hr'
import { formatCurrency, formatDate } from '../../lib/format'
import { Modal } from '../../components/Modal'
import { ClaimStatusBadge } from '../claims/ClaimStatusBadge'

interface ClaimHistoryModalProps {
  employeeId: string
  childId: string
  childName: string
  currentClaimId: number
  onClose: () => void
}

export function ClaimHistoryModal({
  employeeId,
  childId,
  childName,
  currentClaimId,
  onClose,
}: ClaimHistoryModalProps) {
  const { data, isPending, isError } = useQuery({
    queryKey: ['hr-claim-history', employeeId, childId],
    queryFn: () => listHRClaims({ employee_id: employeeId, child_id: childId }),
  })

  return (
    <Modal title={`Claim history — ${childName}`} onClose={onClose}>
      {isPending && (
        <div className="flex items-center gap-2 text-slate-600">
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
          Loading…
        </div>
      )}
      {isError && <p className="text-sm text-red-700">Could not load claim history.</p>}
      {data && data.length === 0 && (
        <p className="text-sm text-slate-500">No other claims for this child.</p>
      )}
      {data && data.length > 0 && (
        <ul className="space-y-2">
          {data.map((claim) => (
            <li
              key={claim.claim_id}
              className={`rounded-md border p-3 text-sm ${
                claim.claim_id === currentClaimId
                  ? 'border-indigo-300 bg-indigo-50'
                  : 'border-slate-200'
              }`}
            >
              <div className="flex items-center justify-between gap-2">
                <Link
                  to={`/hr/claims/${claim.claim_id}`}
                  onClick={onClose}
                  className="font-medium text-indigo-700 hover:underline"
                >
                  Claim #{claim.claim_id}
                  {claim.claim_id === currentClaimId && ' (this claim)'}
                </Link>
                <ClaimStatusBadge status={claim.claim_status} />
              </div>
              <div className="mt-1 flex flex-wrap gap-x-4 text-slate-600">
                <span>Invoice {claim.invoice_number}</span>
                <span>{formatDate(claim.invoice_date)}</span>
                <span>{formatCurrency(claim.invoice_amount)}</span>
              </div>
            </li>
          ))}
        </ul>
      )}
    </Modal>
  )
}
