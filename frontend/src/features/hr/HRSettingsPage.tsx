import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { isAxiosError } from 'axios'
import { AlertCircle, CalendarClock, Loader2, Settings } from 'lucide-react'
import { useState } from 'react'
import { toast } from 'sonner'

import {
  getPayoutSettings,
  getPayoutSettingsHistory,
  openNextFinancialYear,
  updatePayoutSettings,
  type PayoutSettingsHistoryEntry,
} from '../../api/payoutSettings'
import { formatDateTime } from '../../lib/format'

function extractErrorMessage(error: unknown): string {
  if (isAxiosError(error)) {
    const backendMessage = error.response?.data?.message
    if (typeof backendMessage === 'string') {
      return backendMessage
    }
  }
  return 'Something went wrong. Please try again.'
}

function describeChange(entry: PayoutSettingsHistoryEntry): string[] {
  const changes: string[] = []
  if (entry.previous_submission_cutoff_day !== entry.new_submission_cutoff_day) {
    changes.push(
      `Cutoff day: ${entry.previous_submission_cutoff_day} → ${entry.new_submission_cutoff_day}`,
    )
  }
  if (entry.previous_claims_blocked !== entry.new_claims_blocked) {
    changes.push(
      `Claims: ${entry.previous_claims_blocked ? 'Paused' : 'Resumed'} → ${
        entry.new_claims_blocked ? 'Paused' : 'Resumed'
      }`,
    )
  }
  if (entry.previous_open_financial_year !== entry.new_open_financial_year) {
    changes.push(
      `Open financial year: ${entry.previous_open_financial_year ?? '—'} → ${
        entry.new_open_financial_year ?? '—'
      }`,
    )
  }
  if (entry.previous_force_same_month_payout !== entry.new_force_same_month_payout) {
    changes.push(
      `Same-month payout override: ${entry.previous_force_same_month_payout ? 'On' : 'Off'} → ${
        entry.new_force_same_month_payout ? 'On' : 'Off'
      }`,
    )
  }
  return changes
}

export function HRSettingsPage() {
  const queryClient = useQueryClient()
  // undefined = "not yet touched by the user" -> follow the loaded
  // settings; once the user edits a field, its draft value takes over
  // and stays put across a background refetch. Derived during render
  // rather than seeded via an effect, so there's no cascading re-render
  // and no risk of clobbering an in-progress edit if `data` changes.
  const [cutoffDayDraft, setCutoffDayDraft] = useState<string | undefined>(undefined)
  const [claimsBlockedDraft, setClaimsBlockedDraft] = useState<boolean | undefined>(undefined)
  const [forceSameMonthDraft, setForceSameMonthDraft] = useState<boolean | undefined>(undefined)
  const [isConfirmingOpenFY, setIsConfirmingOpenFY] = useState(false)

  const { data, isPending, isError } = useQuery({
    queryKey: ['payout-settings'],
    queryFn: getPayoutSettings,
  })

  const historyQuery = useQuery({
    queryKey: ['payout-settings-history'],
    queryFn: getPayoutSettingsHistory,
  })

  const cutoffDay = cutoffDayDraft ?? (data ? String(data.submission_cutoff_day) : '')
  const claimsBlocked = claimsBlockedDraft ?? data?.claims_blocked ?? false
  const forceSameMonthPayout = forceSameMonthDraft ?? data?.force_same_month_payout ?? false

  const updateMutation = useMutation({
    mutationFn: () =>
      updatePayoutSettings({
        submission_cutoff_day: Number(cutoffDay),
        claims_blocked: claimsBlocked,
        force_same_month_payout: forceSameMonthPayout,
      }),
    onSuccess: async (updated) => {
      queryClient.setQueryData(['payout-settings'], updated)
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['payout-settings'] }),
        queryClient.invalidateQueries({ queryKey: ['payout-settings-history'] }),
      ])
      setCutoffDayDraft(undefined)
      setClaimsBlockedDraft(undefined)
      setForceSameMonthDraft(undefined)
      toast.success('Settings saved.')
    },
    onError: (error) => toast.error(extractErrorMessage(error)),
  })

  const openNextFYMutation = useMutation({
    mutationFn: openNextFinancialYear,
    onSuccess: async (updated) => {
      queryClient.setQueryData(['payout-settings'], updated)
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ['payout-settings'] }),
        queryClient.invalidateQueries({ queryKey: ['payout-settings-history'] }),
      ])
      setIsConfirmingOpenFY(false)
      toast.success(`Financial year ${updated.open_financial_year} is now open.`)
    },
    onError: (error) => toast.error(extractErrorMessage(error)),
  })

  const cutoffDayNumber = Number(cutoffDay)
  const cutoffDayIsValid =
    cutoffDay.trim() !== '' && Number.isInteger(cutoffDayNumber) && cutoffDayNumber >= 1 && cutoffDayNumber <= 28

  const isDirty =
    data !== undefined &&
    (cutoffDay !== String(data.submission_cutoff_day) ||
      claimsBlocked !== data.claims_blocked ||
      forceSameMonthPayout !== data.force_same_month_payout)

  return (
    <div className="max-w-2xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Payout Settings</h1>
        <p className="mt-1 text-slate-600">
          Controls that apply to every employee's claims, effective immediately.
        </p>
      </div>

      {isPending && (
        <div className="flex items-center gap-2 text-slate-600">
          <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
          Loading…
        </div>
      )}

      {isError && (
        <div className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-4 text-red-700">
          <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
          Could not load payout settings.
        </div>
      )}

      {data && (
        <form
          onSubmit={(e) => {
            e.preventDefault()
            updateMutation.mutate()
          }}
          className="space-y-6 rounded-lg border border-slate-200 bg-white p-5 shadow-sm"
        >
          <div>
            <label htmlFor="cutoffDay" className="block text-sm font-medium text-slate-700">
              Submission cutoff day
            </label>
            <p className="mt-1 text-sm text-slate-500">
              A claim submitted on or before this day of the month is eligible for that same
              month's payout. Submitted later, payout moves to the next month — even if approved
              quickly.
            </p>
            <input
              id="cutoffDay"
              type="number"
              min={1}
              max={28}
              step={1}
              value={cutoffDay}
              onChange={(e) => setCutoffDayDraft(e.target.value)}
              onWheel={(e) => e.currentTarget.blur()}
              className="mt-2 block w-24 rounded-md border border-slate-300 px-3 py-2 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            />
            {!cutoffDayIsValid && (
              <p className="mt-1 flex items-center gap-1 text-sm text-red-600">
                <AlertCircle className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
                Enter a whole number from 1 to 28.
              </p>
            )}
          </div>

          <div className="flex items-start gap-3 rounded-md border border-slate-200 p-3">
            <input
              id="claimsBlocked"
              type="checkbox"
              checked={claimsBlocked}
              onChange={(e) => setClaimsBlockedDraft(e.target.checked)}
              className="mt-0.5 h-4 w-4 rounded border-slate-300 text-indigo-700 focus:ring-indigo-500"
            />
            <label htmlFor="claimsBlocked" className="text-sm">
              <span className="font-medium text-slate-900">Pause all claims</span>
              <p className="mt-0.5 text-slate-500">
                While on, employees can't create or submit any claims. Editing an existing Draft
                and your own approve/reject/send-back actions keep working as normal.
              </p>
            </label>
          </div>

          {claimsBlocked && (
            <div className="flex items-start gap-2 rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
              Claims are currently paused for every employee.
            </div>
          )}

          <div className="flex items-start gap-3 rounded-md border border-slate-200 p-3">
            <input
              id="forceSameMonthPayout"
              type="checkbox"
              checked={forceSameMonthPayout}
              onChange={(e) => setForceSameMonthDraft(e.target.checked)}
              className="mt-0.5 h-4 w-4 rounded border-slate-300 text-indigo-700 focus:ring-indigo-500"
            />
            <label htmlFor="forceSameMonthPayout" className="text-sm">
              <span className="font-medium text-slate-900">Force same-month payout</span>
              <p className="mt-0.5 text-slate-500">
                For financial-year close-out. While on, every approved claim pays out in the
                month it's approved, ignoring the cutoff-day rule above — including claims
                already approved before you turned this on.
              </p>
            </label>
          </div>

          {forceSameMonthPayout && (
            <div className="flex items-start gap-2 rounded-md border border-amber-200 bg-amber-50 p-3 text-sm text-amber-800">
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden="true" />
              Every claim is currently paying out in its approval month — turn this off once
              close-out is finished.
            </div>
          )}

          <div className="flex items-center justify-between gap-3">
            <p className="text-xs text-slate-400">
              {data.updated_date
                ? `Last updated ${formatDateTime(data.updated_date)} by ${data.updated_by}`
                : 'Never changed from the default.'}
            </p>
            <button
              type="submit"
              disabled={!cutoffDayIsValid || !isDirty || updateMutation.isPending}
              className="flex items-center gap-1.5 rounded-md bg-indigo-700 px-4 py-2 text-sm font-medium text-white transition hover:bg-indigo-800 disabled:cursor-not-allowed disabled:opacity-60"
            >
              {updateMutation.isPending && (
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
              )}
              Save changes
            </button>
          </div>
        </form>
      )}

      {data && (
        <div className="space-y-4 rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
          <div className="flex items-start gap-3">
            <div className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-indigo-100 text-indigo-700">
              <CalendarClock className="h-4 w-4" aria-hidden="true" />
            </div>
            <div>
              <h2 className="font-medium text-slate-900">Financial year</h2>
              <p className="mt-0.5 text-sm text-slate-500">
                Employees can only raise or submit claims for a financial year at or before this
                one. There's no automatic rollover — open each new year yourself, including right
                at the start of April, so you can hold it closed on purpose while finishing
                close-out.
              </p>
            </div>
          </div>

          <div className="flex items-center justify-between rounded-md border border-slate-200 bg-slate-50 px-3 py-2.5">
            <span className="text-sm text-slate-600">
              Currently open through{' '}
              <span className="font-medium text-slate-900">{data.open_financial_year}</span>
            </span>
            {isConfirmingOpenFY ? (
              <div className="flex items-center gap-3 text-sm">
                <span className="text-slate-500">Open the next financial year?</span>
                <button
                  type="button"
                  disabled={openNextFYMutation.isPending}
                  onClick={() => openNextFYMutation.mutate()}
                  className="flex items-center gap-1 font-medium text-indigo-700 hover:underline disabled:cursor-not-allowed disabled:opacity-60"
                >
                  {openNextFYMutation.isPending && (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
                  )}
                  Confirm
                </button>
                <button
                  type="button"
                  onClick={() => setIsConfirmingOpenFY(false)}
                  className="font-medium text-slate-500 hover:underline"
                >
                  Cancel
                </button>
              </div>
            ) : (
              <button
                type="button"
                onClick={() => setIsConfirmingOpenFY(true)}
                className="rounded-md border border-slate-300 px-3 py-1.5 text-sm font-medium text-slate-700 transition hover:bg-white"
              >
                Open next financial year
              </button>
            )}
          </div>
        </div>
      )}

      <div className="rounded-lg border border-slate-200 bg-white p-5 shadow-sm">
        <h2 className="mb-3 font-medium text-slate-900">Change history</h2>

        {historyQuery.isPending && (
          <div className="flex items-center gap-2 text-slate-600">
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
            Loading…
          </div>
        )}

        {historyQuery.isError && (
          <p className="text-sm text-red-700">Could not load change history.</p>
        )}

        {historyQuery.data && historyQuery.data.length === 0 && (
          <p className="text-sm text-slate-500">No changes recorded yet.</p>
        )}

        {historyQuery.data && historyQuery.data.length > 0 && (
          <ul className="space-y-4 text-sm">
            {historyQuery.data.map((entry, index) => (
              <li key={`${entry.changed_date}-${index}`} className="flex gap-3">
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-indigo-100 text-indigo-700">
                  <Settings className="h-4 w-4" aria-hidden="true" />
                </div>
                <div className="min-w-0 flex-1 space-y-1 pb-1">
                  <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-0.5">
                    <span className="font-medium text-slate-900">
                      Changed by {entry.changed_by}
                    </span>
                    <span className="shrink-0 text-xs text-slate-400">
                      {formatDateTime(entry.changed_date)}
                    </span>
                  </div>
                  {describeChange(entry).map((line) => (
                    <div key={line} className="text-slate-600">
                      {line}
                    </div>
                  ))}
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  )
}
