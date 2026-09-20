import { apiClient } from '../lib/apiClient'
import type { PayoutReportResponse } from './reports'

export interface EmployeeEligibilityReportRow {
  eligibility_id: number
  child_id: string
  child_name: string
  child_dob: string
  financial_year: string
  eligible_months: number
  monthly_benefit_amount: string
  allotted_amount: string
  utilized_amount: string
  in_progress_amount: string
  balance_amount: string
  last_modified_date: string
}

export interface EmployeeEligibilityReport {
  rows: EmployeeEligibilityReportRow[]
}

export interface MonthlyLedgerEntry {
  month: string
  entitlement_amount: string
  opening_balance: string
  total_available_amount: string
  claim_allocated_amount: string
  adjustment_amount: string
  closing_balance: string
  calculated_payout_amount: string
}

export async function getEligibilityReport(): Promise<EmployeeEligibilityReport> {
  const { data } = await apiClient.get<EmployeeEligibilityReport>('/eligibility/report')
  return data
}

export async function getPayoutSchedule(
  childId: string,
  financialYear: string,
): Promise<MonthlyLedgerEntry[]> {
  const { data } = await apiClient.get<MonthlyLedgerEntry[]>(
    `/eligibility/${childId}/payout-schedule`,
    { params: { financialYear } },
  )
  return data
}

/** The employee's own equivalent of HR's payout report — same
 * Employee + Child + FY, Apr-Mar pivoted shape, always scoped to the
 * signed-in employee's own children. Pass `financialYear` to scope to
 * one year (e.g. for the home page's current-year chart); omit it for
 * every year on record (e.g. the full "My Payout" page). */
export async function getMyPayoutReport(financialYear?: string): Promise<PayoutReportResponse> {
  const { data } = await apiClient.get<PayoutReportResponse>('/eligibility/payout-report', {
    params: financialYear ? { financial_year: financialYear } : undefined,
  })
  return data
}
