import { CheckCircle2, Send, XCircle } from 'lucide-react'
import type { ReactNode } from 'react'

import { formatCurrency, formatDate } from '../lib/format'

interface ApprovalHistoryEntryLike {
  approval_history_id: number
  action: 'Approved' | 'Rejected' | 'SentBack'
  action_date: string
  approved_amount: string | null
  remarks: string | null
}

const ACTION_META = {
  Approved: { icon: CheckCircle2, label: 'Approved', classes: 'bg-emerald-100 text-emerald-700' },
  Rejected: { icon: XCircle, label: 'Rejected', classes: 'bg-red-100 text-red-700' },
  SentBack: { icon: Send, label: 'Sent Back', classes: 'bg-amber-100 text-amber-700' },
} as const

/** A vertical, icon-and-color-coded timeline for a claim's approval
 * history — shared by the HR claim detail page, the report detail
 * popup, and the employee's own claim detail page (via `renderActor`,
 * since the employee view deliberately shows "by HR" generically rather
 * than naming the specific approver). */
export function ApprovalHistoryTimeline<T extends ApprovalHistoryEntryLike>({
  entries,
  renderActor,
}: {
  entries: T[]
  renderActor: (entry: T) => ReactNode
}) {
  return (
    <ul className="space-y-4 text-sm">
      {entries.map((entry) => {
        const meta = ACTION_META[entry.action]
        const Icon = meta.icon
        return (
          <li key={entry.approval_history_id} className="flex gap-3">
            <div
              className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-full ${meta.classes}`}
            >
              <Icon className="h-4 w-4" aria-hidden="true" />
            </div>
            <div className="min-w-0 flex-1 space-y-1 pb-1">
              <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-0.5">
                <span className="font-medium text-slate-900">
                  {meta.label} {renderActor(entry)}
                </span>
                <span className="shrink-0 text-xs text-slate-400">
                  {formatDate(entry.action_date.slice(0, 10))}
                </span>
              </div>
              {entry.approved_amount && (
                <div className="text-slate-600">
                  Approved amount:{' '}
                  <span className="font-medium text-emerald-700">
                    {formatCurrency(entry.approved_amount)}
                  </span>
                </div>
              )}
              {entry.remarks && (
                <p className="rounded-md bg-slate-50 px-2.5 py-1.5 text-slate-600 italic">
                  &ldquo;{entry.remarks}&rdquo;
                </p>
              )}
            </div>
          </li>
        )
      })}
    </ul>
  )
}
