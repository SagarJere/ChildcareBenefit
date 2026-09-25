import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { isAxiosError } from 'axios'
import { AlertTriangle, FileText, Loader2, Pause, Plus, Trash2 } from 'lucide-react'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { toast } from 'sonner'

import { deleteClaim, listClaims } from '../../api/claims'
import { getPayoutSettings } from '../../api/payoutSettings'
import { formatCurrency, formatDate } from '../../lib/format'
import { ClaimStatusBadge } from './ClaimStatusBadge'

function extractErrorMessage(error: unknown): string {
  if (isAxiosError(error)) {
    const backendMessage = error.response?.data?.message
    if (typeof backendMessage === 'string') {
      return backendMessage
    }
  }
  return 'Something went wrong. Please try again.'
}

export function ClaimsPage() {
  const queryClient = useQueryClient()
  const [confirmingClaimId, setConfirmingClaimId] = useState<number | null>(null)

  const { data: claims, isPending, isError } = useQuery({
    queryKey: ['claims'],
    queryFn: listClaims,
  })

  const { data: payoutSettings } = useQuery({
    queryKey: ['payout-settings'],
    queryFn: getPayoutSettings,
  })
  const claimsBlocked = payoutSettings?.claims_blocked ?? false

  const deleteMutation = useMutation({
    mutationFn: (claimId: number) => deleteClaim(claimId),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['claims'] })
      toast.success('Claim deleted.')
      setConfirmingClaimId(null)
    },
    onError: (error) => {
      toast.error(extractErrorMessage(error))
      setConfirmingClaimId(null)
    },
  })

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">My Claims</h1>
          <p className="mt-1 text-slate-600">Raise and track childcare benefit claims.</p>
        </div>
        {claimsBlocked ? (
          <span className="flex items-center gap-1.5 rounded-md bg-slate-100 px-4 py-2 text-sm font-medium text-slate-400">
            <Plus className="h-4 w-4" aria-hidden="true" />
            Raise Claim
          </span>
        ) : (
          <Link
            to="/claims/new"
            className="flex items-center gap-1.5 rounded-md bg-indigo-700 px-4 py-2 text-sm font-medium text-white transition hover:bg-indigo-800"
          >
            <Plus className="h-4 w-4" aria-hidden="true" />
            Raise Claim
          </Link>
        )}
      </div>

      {claimsBlocked && (
        <div className="flex items-start gap-2 rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
          <Pause className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
          HR has temporarily paused new claims. You can't create or submit a claim right now, but
          existing Drafts can still be edited.
        </div>
      )}

      {isPending && (
        <div className="flex items-center gap-2 text-slate-600">
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
          Loading claims…
        </div>
      )}

      {isError && (
        <div className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
          Could not load your claims. Please try again shortly.
        </div>
      )}

      {claims && claims.length === 0 && (
        <div className="flex flex-col items-center gap-3 rounded-lg border border-dashed border-slate-300 bg-white px-6 py-12 text-center">
          <FileText className="h-8 w-8 text-slate-300" aria-hidden="true" />
          <p className="text-slate-600">You haven't raised any claims yet.</p>
          {!claimsBlocked && (
            <Link
              to="/claims/new"
              className="flex items-center gap-1.5 rounded-md bg-indigo-700 px-4 py-2 text-sm font-medium text-white transition hover:bg-indigo-800"
            >
              <Plus className="h-4 w-4" aria-hidden="true" />
              Raise your first claim
            </Link>
          )}
        </div>
      )}

      {claims && claims.length > 0 && (
        <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white shadow-sm">
          <table className="min-w-full divide-y divide-slate-100 text-sm">
            <thead className="bg-slate-50 text-left text-xs font-medium uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-3">Child</th>
                <th className="px-4 py-3">Invoice</th>
                <th className="px-4 py-3">Date</th>
                <th className="px-4 py-3">Amount</th>
                <th className="px-4 py-3">Status</th>
                <th className="px-4 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {claims.map((claim) => {
                const isEditable = claim.claim_status === 'Draft' || claim.claim_status === 'SentBack'
                const isDraft = claim.claim_status === 'Draft'
                const isConfirming = confirmingClaimId === claim.claim_id
                return (
                  <tr key={claim.claim_id}>
                    <td className="px-4 py-3 font-medium text-slate-900">{claim.child_name}</td>
                    <td className="px-4 py-3 text-slate-600">{claim.invoice_number}</td>
                    <td className="px-4 py-3 text-slate-600">{formatDate(claim.invoice_date)}</td>
                    <td className="px-4 py-3 text-slate-600">
                      {formatCurrency(claim.invoice_amount)}
                    </td>
                    <td className="px-4 py-3">
                      <ClaimStatusBadge status={claim.claim_status} />
                    </td>
                    <td className="px-4 py-3">
                      <div className="flex items-center justify-end gap-3">
                        {isConfirming ? (
                          <>
                            <span className="text-xs text-slate-500">Delete this claim?</span>
                            <button
                              type="button"
                              disabled={deleteMutation.isPending}
                              onClick={() => deleteMutation.mutate(claim.claim_id)}
                              className="flex items-center gap-1 font-medium text-red-600 hover:underline disabled:cursor-not-allowed disabled:opacity-60"
                            >
                              {deleteMutation.isPending && (
                                <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
                              )}
                              Confirm
                            </button>
                            <button
                              type="button"
                              onClick={() => setConfirmingClaimId(null)}
                              className="font-medium text-slate-500 hover:underline"
                            >
                              Cancel
                            </button>
                          </>
                        ) : (
                          <>
                            {isDraft && (
                              <button
                                type="button"
                                onClick={() => setConfirmingClaimId(claim.claim_id)}
                                className="flex items-center gap-1 font-medium text-slate-400 hover:text-red-600"
                                aria-label="Delete claim"
                              >
                                <Trash2 className="h-4 w-4" aria-hidden="true" />
                              </button>
                            )}
                            <Link
                              to={`/claims/${claim.claim_id}`}
                              className="font-medium text-indigo-700 hover:underline"
                            >
                              {isEditable ? 'Continue' : 'View'}
                            </Link>
                          </>
                        )}
                      </div>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}
    </div>
  )
}
