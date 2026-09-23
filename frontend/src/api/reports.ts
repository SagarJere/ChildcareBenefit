import type { Claim } from './claims'
import { apiClient } from '../lib/apiClient'

export interface ClaimSummaryRow {
  claim_id: number
  employee_id: string
  employee_name: string
  child_id: string
  child_name: string
  invoice_date: string
  invoice_number: string
  invoice_amount: string
  claim_amount: string
  claim_status: Claim['claim_status']
  submitted_date: string | null
  approved_date: string | null
}

export interface ClaimsSummaryResponse {
  rows: ClaimSummaryRow[]
  totals: {
    total_claims: number
    count_by_status: Record<string, number>
    total_invoice_amount: string
    total_approved_amount: string
  }
}

export interface EligibilityUtilizationRow {
  eligibility_id: number
  employee_id: string
  employee_name: string
  child_id: string
  child_name: string
  financial_year: string
  eligible_months: number
  monthly_benefit_amount: string
  allotted_amount: string
  in_progress_amount: string
  approved_amount: string
  remaining_after_approved: string
}

export interface EligibilityUtilizationResponse {
  rows: EligibilityUtilizationRow[]
  totals: {
    total_allotted_amount: string
    total_in_progress_amount: string
    total_approved_amount: string
  }
}

export interface HeadcountResponse {
  total_employees_with_children: number
  total_children: number
  employees_with_one_child: number
  employees_with_two_children: number
  by_financial_year: { financial_year: string; child_count: number }[]
  by_age_bracket: { age_bracket: string; child_count: number }[]
}

export interface PayoutReportRow {
  employee_id: string
  employee_name: string
  child_id: string
  child_name: string
  child_dob: string
  financial_year: string
  apr: string
  may: string
  jun: string
  jul: string
  aug: string
  sep: string
  oct: string
  nov: string
  dec: string
  jan: string
  feb: string
  mar: string
  total_payout: string
}

export interface PayoutReportResponse {
  rows: PayoutReportRow[]
  totals: {
    total_payout: string
  }
}

export interface ClaimsSummaryFilters {
  date_from?: string
  date_to?: string
  status?: string
  employee_id?: string
}

export interface EligibilityUtilizationFilters {
  financial_year?: string
  employee_id?: string
}

export interface PayoutReportFilters {
  financial_year?: string
  employee_id?: string
  child_id?: string
}

export async function getClaimsSummary(
  filters: ClaimsSummaryFilters,
): Promise<ClaimsSummaryResponse> {
  const { data } = await apiClient.get<ClaimsSummaryResponse>('/hr/reports/claims-summary', {
    params: filters,
  })
  return data
}

export async function getEligibilityUtilization(
  filters: EligibilityUtilizationFilters,
): Promise<EligibilityUtilizationResponse> {
  const { data } = await apiClient.get<EligibilityUtilizationResponse>(
    '/hr/reports/eligibility-utilization',
    { params: filters },
  )
  return data
}

export async function getHeadcount(): Promise<HeadcountResponse> {
  const { data } = await apiClient.get<HeadcountResponse>('/hr/reports/headcount')
  return data
}

/** Every financial year that has data, most recent first — feeds the
 * reports' financial-year filter dropdown. */
export async function getFinancialYears(): Promise<string[]> {
  const { data } = await apiClient.get<string[]>('/hr/financial-years')
  return data
}

export async function getPayoutReport(filters: PayoutReportFilters): Promise<PayoutReportResponse> {
  const { data } = await apiClient.get<PayoutReportResponse>('/hr/reports/payout', {
    params: filters,
  })
  return data
}

/** The child's first-13-months auto-paid amounts only, with no claim
 * involved — the sibling of getPayoutReport's claim-driven payout. */
export async function getFirstYearPayoutReport(
  filters: PayoutReportFilters,
): Promise<PayoutReportResponse> {
  const { data } = await apiClient.get<PayoutReportResponse>('/hr/reports/payout/first-year', {
    params: filters,
  })
  return data
}

export async function downloadReportCsv(
  path: string,
  params: Record<string, string | undefined>,
  filename: string,
): Promise<void> {
  const response = await apiClient.get(path, {
    params: { ...params, format: 'csv' },
    responseType: 'blob',
  })
  const url = window.URL.createObjectURL(response.data as Blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.URL.revokeObjectURL(url)
}
