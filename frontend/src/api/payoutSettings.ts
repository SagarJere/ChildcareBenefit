import { apiClient } from '../lib/apiClient'

export interface PayoutSettings {
  submission_cutoff_day: number
  claims_blocked: boolean
  open_financial_year: string | null
  force_same_month_payout: boolean
  updated_by: string | null
  updated_date: string | null
}

export interface PayoutSettingsInput {
  submission_cutoff_day: number
  claims_blocked: boolean
  force_same_month_payout: boolean
}

export interface PayoutSettingsHistoryEntry {
  changed_by: string
  previous_submission_cutoff_day: number
  new_submission_cutoff_day: number
  previous_claims_blocked: boolean
  new_claims_blocked: boolean
  previous_open_financial_year: string | null
  new_open_financial_year: string | null
  previous_force_same_month_payout: boolean
  new_force_same_month_payout: boolean
  changed_date: string
}

/** Readable by any authenticated employee, not just HR — used to show a
 * "claims are paused" banner before an employee even tries to submit. */
export async function getPayoutSettings(): Promise<PayoutSettings> {
  const { data } = await apiClient.get<PayoutSettings>('/payout-settings')
  return data
}

export async function updatePayoutSettings(input: PayoutSettingsInput): Promise<PayoutSettings> {
  const { data } = await apiClient.put<PayoutSettings>('/hr/payout-settings', input)
  return data
}

export async function getPayoutSettingsHistory(): Promise<PayoutSettingsHistoryEntry[]> {
  const { data } = await apiClient.get<PayoutSettingsHistoryEntry[]>(
    '/hr/payout-settings/history',
  )
  return data
}

/** Advances the open financial year by exactly one, relative to
 * whatever is currently open — not to today's real calendar FY. There
 * is deliberately no automatic fallback: HR must call this explicitly
 * every year, including right at the calendar rollover, so a financial
 * year can be held closed on purpose during close-out. */
export async function openNextFinancialYear(): Promise<PayoutSettings> {
  const { data } = await apiClient.post<PayoutSettings>(
    '/hr/payout-settings/open-next-financial-year',
  )
  return data
}
