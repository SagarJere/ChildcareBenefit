import { useQuery } from '@tanstack/react-query'
import type { LucideIcon } from 'lucide-react'
import {
  CheckCircle2,
  ClipboardList,
  History,
  Settings,
  Table2,
  UserPlus,
  Users,
  UsersRound,
} from 'lucide-react'
import { Link } from 'react-router-dom'

import { getClaimsSummary, getHeadcount, getPayoutReport } from '../../api/reports'
import { listHRClaims } from '../../api/hr'
import { BarChart, type BarChartDatum } from '../../components/BarChart'
import { StatCard } from '../../components/StatCard'
import { formatCurrency } from '../../lib/format'

const STATUS_DISPLAY_ORDER = ['Draft', 'Submitted', 'SentBack', 'Approved', 'Rejected'] as const

interface QuickLink {
  to: string
  icon: LucideIcon
  title: string
  description: string
}

const QUICK_LINK_GROUPS: { heading: string; links: QuickLink[] }[] = [
  {
    heading: 'Children',
    links: [
      {
        to: '/hr/children/new',
        icon: UserPlus,
        title: 'Add Child',
        description: 'Add one child on behalf of an employee.',
      },
      {
        to: '/hr/children/bulk',
        icon: UsersRound,
        title: 'Bulk Add Children',
        description: 'Upload a CSV to add several children at once.',
      },
      {
        to: '/hr/children/bulk/history',
        icon: History,
        title: 'Bulk Upload History',
        description: 'Look up a past bulk upload and what happened to each row.',
      },
    ],
  },
  {
    heading: 'Insights',
    links: [
      {
        to: '/hr/reports',
        icon: Table2,
        title: 'Reports',
        description: 'Claims, eligibility, payout, headcount, and child details.',
      },
    ],
  },
  {
    heading: 'Configuration',
    links: [
      {
        to: '/hr/settings',
        icon: Settings,
        title: 'Settings',
        description: 'Cutoff day, claims-blocked switch, and financial year.',
      },
    ],
  },
]

export function HRDashboardPage() {
  const hrPendingQuery = useQuery({
    queryKey: ['hr-claims', { status: 'Submitted' }],
    queryFn: () => listHRClaims({ status: 'Submitted' }),
  })
  const headcountQuery = useQuery({
    queryKey: ['report-headcount'],
    queryFn: getHeadcount,
  })
  const claimsSummaryQuery = useQuery({
    queryKey: ['report-claims-summary', {}],
    queryFn: () => getClaimsSummary({}),
  })
  const hrPayoutQuery = useQuery({
    queryKey: ['report-payout', {}],
    queryFn: () => getPayoutReport({}),
  })

  const claimsByStatusData: BarChartDatum[] = STATUS_DISPLAY_ORDER.filter(
    (status) => (claimsSummaryQuery.data?.totals.count_by_status[status] ?? 0) > 0,
  ).map((status) => ({
    label: status,
    value: claimsSummaryQuery.data?.totals.count_by_status[status] ?? 0,
  }))

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">HR Dashboard</h1>
        <p className="mt-1 text-slate-600">Everything HR needs, in one place.</p>
      </div>

      <Link
        to="/hr/claims"
        className="flex w-fit items-center gap-1.5 rounded-md bg-indigo-700 px-4 py-2 text-sm font-medium text-white transition hover:bg-indigo-800"
      >
        <ClipboardList className="h-4 w-4" aria-hidden="true" />
        Claim Approval Queue
      </Link>

      <div>
        <h2 className="mb-3 text-lg font-semibold text-slate-900">Overview</h2>
        <div className="grid grid-cols-2 gap-3 sm:grid-cols-3">
          <StatCard
            icon={ClipboardList}
            label="Pending Review"
            value={hrPendingQuery.data?.length ?? '—'}
            to="/hr/claims"
            accent="amber"
          />
          <StatCard
            icon={Users}
            label="Employees with Children"
            value={headcountQuery.data?.total_employees_with_children ?? '—'}
          />
          <StatCard
            icon={CheckCircle2}
            label="Total Approved Payout"
            value={
              hrPayoutQuery.data ? formatCurrency(hrPayoutQuery.data.totals.total_payout) : '—'
            }
            to="/hr/reports"
            accent="emerald"
          />
        </div>

        {claimsByStatusData.length > 0 && (
          <div className="mt-4 max-w-md rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
            <h3 className="mb-3 font-medium text-slate-900">Claims by Status</h3>
            <BarChart data={claimsByStatusData} />
          </div>
        )}
      </div>

      <div className="space-y-6">
        {QUICK_LINK_GROUPS.map((group) => (
          <div key={group.heading}>
            <h2 className="mb-3 text-lg font-semibold text-slate-900">{group.heading}</h2>
            <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
              {group.links.map((link) => (
                <Link
                  key={link.to}
                  to={link.to}
                  className="flex items-start gap-3 rounded-lg border border-slate-200 bg-white p-4 shadow-sm transition hover:border-indigo-300 hover:shadow-md"
                >
                  <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-indigo-100 text-indigo-700">
                    <link.icon className="h-4 w-4" aria-hidden="true" />
                  </div>
                  <div>
                    <div className="font-medium text-slate-900">{link.title}</div>
                    <p className="mt-0.5 text-sm text-slate-500">{link.description}</p>
                  </div>
                </Link>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
