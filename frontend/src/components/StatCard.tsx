import type { LucideIcon } from 'lucide-react'
import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'

const ACCENT_CLASSES = {
  indigo: 'text-indigo-600',
  emerald: 'text-emerald-600',
  amber: 'text-amber-600',
  slate: 'text-slate-600',
} as const

interface StatCardProps {
  icon: LucideIcon
  label: string
  value: string | number
  to?: string
  accent?: keyof typeof ACCENT_CLASSES
  /** Optional detail panel revealed on hover — e.g. a breakdown behind a
   * single summary number. Purely a hover affordance; the card still
   * navigates to `to` on click as usual. */
  tooltip?: ReactNode
}

/** A small dashboard stat tile — optionally a link to the page it
 * summarizes, and optionally a hover-revealed detail panel. */
export function StatCard({
  icon: Icon,
  label,
  value,
  to,
  accent = 'indigo',
  tooltip,
}: StatCardProps) {
  const box = (
    <div className="h-full rounded-lg border border-slate-200 bg-white p-4 shadow-sm transition hover:border-indigo-300 hover:shadow-md">
      <div className="flex items-center gap-2 text-slate-500">
        <Icon className={`h-4 w-4 ${ACCENT_CLASSES[accent]}`} aria-hidden="true" />
        <span className="text-sm">{label}</span>
      </div>
      <div className="mt-1 text-2xl font-semibold text-slate-900">{value}</div>
    </div>
  )

  const content = to ? (
    <Link to={to} className="block h-full">
      {box}
    </Link>
  ) : (
    box
  )

  if (!tooltip) {
    return content
  }

  return (
    <div className="group relative h-full">
      {content}
      <div className="invisible absolute left-0 top-full z-10 mt-2 w-64 rounded-lg border border-slate-200 bg-white p-3 opacity-0 shadow-lg transition group-hover:visible group-hover:opacity-100">
        {tooltip}
      </div>
    </div>
  )
}
