import { ChevronRight } from 'lucide-react'
import type { ReactNode } from 'react'

interface CollapsibleSectionProps {
  title: string
  children: ReactNode
  defaultOpen?: boolean
}

/** A card-styled section that can be expanded/collapsed, built on the
 * native <details>/<summary> elements — no extra state or JS needed. */
export function CollapsibleSection({
  title,
  children,
  defaultOpen = true,
}: CollapsibleSectionProps) {
  return (
    <details
      className="group rounded-lg border border-slate-200 bg-white shadow-sm"
      open={defaultOpen}
    >
      <summary className="flex cursor-pointer list-none items-center gap-2 p-5 font-medium text-slate-900 [&::-webkit-details-marker]:hidden">
        <ChevronRight
          className="h-4 w-4 shrink-0 text-slate-400 transition-transform group-open:rotate-90"
          aria-hidden="true"
        />
        {title}
      </summary>
      <div className="px-5 pb-5">{children}</div>
    </details>
  )
}
