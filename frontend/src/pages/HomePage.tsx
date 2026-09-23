import { useQuery } from '@tanstack/react-query'
import {
  CheckCircle2,
  ClipboardList,
  FileText,
  Loader2,
  PiggyBank,
  Plus,
  Users,
  Wallet,
} from 'lucide-react'
import { Link } from 'react-router-dom'

import { listClaims } from '../api/claims'
import { listChildren } from '../api/children'
import { getEligibilityReport, getMyFirstYearPayoutReport, getMyPayoutReport } from '../api/eligibility'
import { listHRClaims } from '../api/hr'
import { getClaimsSummary, getHeadcount, getPayoutReport } from '../api/reports'
import { BarChart, type BarChartDatum } from '../components/BarChart'
import { StatCard } from '../components/StatCard'
import { ClaimStatusBadge } from '../features/claims/ClaimStatusBadge'
import { useAuth } from '../features/auth/useAuth'
import { calculateAge, currentFinancialYearLabel, formatCurrency, formatDate } from '../lib/format'

const MONTH_LABELS = [
  'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec', 'Jan', 'Feb', 'Mar',
] as const
const MONTH_KEYS = [
  'apr', 'may', 'jun', 'jul', 'aug', 'sep', 'oct', 'nov', 'dec', 'jan', 'feb', 'mar',
] as const

const STATUS_DISPLAY_ORDER = ['Draft', 'Submitted', 'SentBack', 'Approved', 'Rejected'] as const
const ACTIVE_CLAIM_STATUSES = new Set(['Draft', 'Submitted', 'SentBack'])

export function HomePage() {
  const { employee } = useAuth()
  const isHR = Boolean(employee?.is_hr_approver)
  const currentFY = currentFinancialYearLabel()

  const childrenQuery = useQuery({ queryKey: ['children'], queryFn: listChildren })
  const claimsQuery = useQuery({ queryKey: ['claims'], queryFn: listClaims })
  const myPayoutQuery = useQuery({
    queryKey: ['my-payout-report'],
    queryFn: () => getMyPayoutReport(),
  })
  const myFirstYearPayoutQuery = useQuery({
    queryKey: ['my-first-year-payout-report'],
    queryFn: () => getMyFirstYearPayoutReport(),
  })
  const myPayoutCurrentFYQuery = useQuery({
    queryKey: ['my-payout-report', currentFY],
    queryFn: () => getMyPayoutReport(currentFY),
  })
  const myFirstYearPayoutCurrentFYQuery = useQuery({
    queryKey: ['my-first-year-payout-report', currentFY],
    queryFn: () => getMyFirstYearPayoutReport(currentFY),
  })
  const eligibilityReportQuery = useQuery({
    queryKey: ['eligibility-report'],
    queryFn: getEligibilityReport,
  })

  const hrPendingQuery = useQuery({
    queryKey: ['hr-claims', { status: 'Submitted' }],
    queryFn: () => listHRClaims({ status: 'Submitted' }),
    enabled: isHR,
  })
  const headcountQuery = useQuery({
    queryKey: ['report-headcount'],
    queryFn: getHeadcount,
    enabled: isHR,
  })
  const claimsSummaryQuery = useQuery({
    queryKey: ['report-claims-summary', {}],
    queryFn: () => getClaimsSummary({}),
    enabled: isHR,
  })
  const hrPayoutQuery = useQuery({
    queryKey: ['report-payout', {}],
    queryFn: () => getPayoutReport({}),
    enabled: isHR,
  })

  const activeClaimsCount = (claimsQuery.data ?? []).filter((c) =>
    ACTIVE_CLAIM_STATUSES.has(c.claim_status),
  ).length
  // Balances aren't comparable across financial years (each year's
  // allotment is independent — see DECISIONS_LOG.md item 45), so this is
  // broken down per FY rather than summed into one misleading total.
  const balanceByFY = Object.entries(
    (eligibilityReportQuery.data?.rows ?? []).reduce<Record<string, number>>((acc, row) => {
      acc[row.financial_year] = (acc[row.financial_year] ?? 0) + Number(row.balance_amount)
      return acc
    }, {}),
  ).sort(([a], [b]) => a.localeCompare(b))
  const recentClaims = (claimsQuery.data ?? []).slice(0, 5)

  // Combines both payout sources (first-year auto-pay + approved claims)
  // into one total-payout view — the detailed per-source breakdown lives
  // on the dedicated My Payout page.
  const monthlyPayoutData: BarChartDatum[] = MONTH_KEYS.map((key, i) => ({
    label: MONTH_LABELS[i],
    value:
      (myPayoutCurrentFYQuery.data?.rows ?? []).reduce((sum, row) => sum + Number(row[key]), 0) +
      (myFirstYearPayoutCurrentFYQuery.data?.rows ?? []).reduce(
        (sum, row) => sum + Number(row[key]),
        0,
      ),
  }))

  const claimsByStatusData: BarChartDatum[] = STATUS_DISPLAY_ORDER.filter(
    (status) => (claimsSummaryQuery.data?.totals.count_by_status[status] ?? 0) > 0,
  ).map((status) => ({
    label: status,
    value: claimsSummaryQuery.data?.totals.count_by_status[status] ?? 0,
  }))

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">
          Welcome{employee?.full_name ? `, ${employee.full_name}` : ''}
        </h1>
        <p className="mt-1 text-slate-600">Here's a summary of your childcare benefit account.</p>
      </div>

      <div className="flex flex-wrap gap-2">
        <Link
          to="/claims/new"
          className="flex items-center gap-1.5 rounded-md bg-indigo-700 px-4 py-2 text-sm font-medium text-white transition hover:bg-indigo-800"
        >
          <Plus className="h-4 w-4" aria-hidden="true" />
          Raise Claim
        </Link>
        <Link
          to="/claims"
          className="flex items-center gap-1.5 rounded-md bg-slate-100 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-200"
        >
          My Claims
        </Link>
        <Link
          to="/payout"
          className="flex items-center gap-1.5 rounded-md bg-slate-100 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-200"
        >
          My Payout
        </Link>
        <Link
          to="/eligibility"
          className="flex items-center gap-1.5 rounded-md bg-slate-100 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-200"
        >
          Eligibility &amp; Payout
        </Link>
      </div>

      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <StatCard
          icon={Users}
          label="Children"
          value={childrenQuery.data?.length ?? '—'}
          to="/children"
          tooltip={
            childrenQuery.data && childrenQuery.data.length > 0 ? (
              <ul className="space-y-2">
                {childrenQuery.data.map((child) => (
                  <li key={child.child_id} className="text-sm">
                    <div className="font-medium text-slate-800">{child.child_name}</div>
                    <div className="text-slate-500">
                      {formatDate(child.child_dob)} · {calculateAge(child.child_dob)}
                    </div>
                  </li>
                ))}
              </ul>
            ) : undefined
          }
        />
        <StatCard
          icon={FileText}
          label="Active Claims"
          value={claimsQuery.data ? activeClaimsCount : '—'}
          to="/claims"
          accent="amber"
        />
        <StatCard
          icon={Wallet}
          label="Total Payout"
          value={
            myPayoutQuery.data && myFirstYearPayoutQuery.data
              ? formatCurrency(
                  Number(myPayoutQuery.data.totals.total_payout) +
                    Number(myFirstYearPayoutQuery.data.totals.total_payout),
                )
              : '—'
          }
          to="/payout"
          accent="emerald"
        />
        <Link
          to="/eligibility"
          className="block rounded-lg border border-slate-200 bg-white p-4 shadow-sm transition hover:border-indigo-300 hover:shadow-md"
        >
          <div className="flex items-center gap-2 text-slate-500">
            <PiggyBank className="h-4 w-4 text-indigo-600" aria-hidden="true" />
            <span className="text-sm">Remaining Balance</span>
          </div>
          {!eligibilityReportQuery.data && (
            <div className="mt-1 text-2xl font-semibold text-slate-900">—</div>
          )}
          {eligibilityReportQuery.data && balanceByFY.length === 0 && (
            <div className="mt-1 text-2xl font-semibold text-slate-900">
              {formatCurrency(0)}
            </div>
          )}
          {balanceByFY.length > 0 && (
            <dl className="mt-1 space-y-0.5">
              {balanceByFY.map(([fy, amount]) => (
                <div key={fy} className="flex items-baseline justify-between gap-2">
                  <dt className="text-xs text-slate-500">FY {fy}</dt>
                  <dd className="text-base font-semibold text-slate-900">
                    {formatCurrency(amount)}
                  </dd>
                </div>
              ))}
            </dl>
          )}
        </Link>
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="mb-3 font-medium text-slate-900">Recent Claims</h2>
          {claimsQuery.isPending && (
            <div className="flex items-center gap-2 text-slate-600">
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
              Loading…
            </div>
          )}
          {claimsQuery.data && recentClaims.length === 0 && (
            <p className="text-sm text-slate-500">
              You haven't raised any claims yet.{' '}
              <Link to="/claims/new" className="text-indigo-700 underline">
                Raise your first claim
              </Link>
              .
            </p>
          )}
          {recentClaims.length > 0 && (
            <ul className="space-y-2">
              {recentClaims.map((claim) => (
                <li key={claim.claim_id}>
                  <Link
                    to={`/claims/${claim.claim_id}`}
                    className="flex items-center justify-between gap-2 rounded-md border border-slate-100 p-2.5 text-sm transition hover:border-indigo-200 hover:bg-indigo-50/40"
                  >
                    <span>
                      <span className="font-medium text-slate-800">{claim.child_name}</span>{' '}
                      <span className="text-slate-500">— {claim.invoice_number}</span>
                    </span>
                    <span className="flex items-center gap-2">
                      <span className="text-slate-600">
                        {formatCurrency(claim.invoice_amount)}
                      </span>
                      <ClaimStatusBadge status={claim.claim_status} />
                    </span>
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <h2 className="mb-3 font-medium text-slate-900">
            Monthly Payout <span className="font-normal text-slate-400">— FY {currentFY}</span>
          </h2>
          {(myPayoutCurrentFYQuery.isPending || myFirstYearPayoutCurrentFYQuery.isPending) && (
            <div className="flex items-center gap-2 text-slate-600">
              <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
              Loading…
            </div>
          )}
          {myPayoutCurrentFYQuery.data &&
            myFirstYearPayoutCurrentFYQuery.data &&
            myPayoutCurrentFYQuery.data.rows.length === 0 &&
            myFirstYearPayoutCurrentFYQuery.data.rows.length === 0 && (
              <p className="text-sm text-slate-500">
                No payouts yet for FY {currentFY} — nothing here until a claim is approved, or a
                child's first-13-months auto-pay applies.
              </p>
            )}
          {myPayoutCurrentFYQuery.data &&
            myFirstYearPayoutCurrentFYQuery.data &&
            (myPayoutCurrentFYQuery.data.rows.length > 0 ||
              myFirstYearPayoutCurrentFYQuery.data.rows.length > 0) && (
              <BarChart data={monthlyPayoutData} formatValue={formatCurrency} />
            )}
        </div>
      </div>

      {isHR && (
        <div className="space-y-4 border-t border-slate-200 pt-8">
          <h2 className="text-lg font-semibold text-slate-900">HR Overview</h2>

          <div className="flex flex-wrap gap-2">
            <Link
              to="/hr/claims"
              className="flex items-center gap-1.5 rounded-md bg-indigo-700 px-4 py-2 text-sm font-medium text-white transition hover:bg-indigo-800"
            >
              <ClipboardList className="h-4 w-4" aria-hidden="true" />
              HR Queue
            </Link>
            <Link
              to="/hr/reports"
              className="flex items-center gap-1.5 rounded-md bg-slate-100 px-4 py-2 text-sm font-medium text-slate-700 transition hover:bg-slate-200"
            >
              Reports
            </Link>
          </div>

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
            <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
              <h3 className="mb-3 font-medium text-slate-900">Claims by Status</h3>
              <BarChart data={claimsByStatusData} />
            </div>
          )}
        </div>
      )}
    </div>
  )
}
