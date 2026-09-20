import { useQuery } from '@tanstack/react-query'
import { AlertTriangle, Loader2, Plus, Users } from 'lucide-react'
import { Link } from 'react-router-dom'

import { listChildren } from '../../api/children'
import { ChildCard } from './ChildCard'

const MAX_CHILDREN = 2

export function ChildrenPage() {
  const { data: children, isPending, isError } = useQuery({
    queryKey: ['children'],
    queryFn: listChildren,
  })

  const canAddChild = (children?.length ?? 0) < MAX_CHILDREN

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">My Children</h1>
          <p className="mt-1 text-slate-600">Up to two children are eligible for the benefit.</p>
        </div>
        {canAddChild && (
          <Link
            to="/children/new"
            className="flex items-center gap-1.5 rounded-md bg-indigo-700 px-4 py-2 text-sm font-medium text-white transition hover:bg-indigo-800"
          >
            <Plus className="h-4 w-4" aria-hidden="true" />
            Add Child
          </Link>
        )}
      </div>

      {isPending && (
        <div className="flex items-center gap-2 text-slate-600">
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
          Loading children…
        </div>
      )}

      {isError && (
        <div className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">
          <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
          Could not load your children. Please try again shortly.
        </div>
      )}

      {children && children.length === 0 && (
        <div className="flex flex-col items-center gap-3 rounded-lg border border-dashed border-slate-300 bg-white px-6 py-12 text-center">
          <Users className="h-8 w-8 text-slate-300" aria-hidden="true" />
          <p className="text-slate-600">You haven't added any children yet.</p>
          <Link
            to="/children/new"
            className="flex items-center gap-1.5 rounded-md bg-indigo-700 px-4 py-2 text-sm font-medium text-white transition hover:bg-indigo-800"
          >
            <Plus className="h-4 w-4" aria-hidden="true" />
            Add your first child
          </Link>
        </div>
      )}

      {children && children.length > 0 && (
        <div className="grid grid-cols-1 gap-4 sm:grid-cols-2">
          {children.map((child) => (
            <ChildCard key={child.child_id} child={child} />
          ))}
        </div>
      )}
    </div>
  )
}
