import { apiClient } from '../lib/apiClient'

export interface EligibilitySummary {
  eligibility_id: number
  child_id: string
  financial_year: string
  eligibility_start_date: string
  eligibility_end_date: string | null
  eligible_months: number
  monthly_benefit_amount: string
  allotted_amount: string
  utilized_amount: string
  approved_amount: string
  in_progress_amount: string
  remaining_amount: string
}

export interface EligibilityPreview {
  financial_year: string
  financial_year_start_date: string
  financial_year_end_date: string
  eligibility_start_date: string
  eligibility_end_date: string | null
  eligible_months: number
  monthly_benefit_amount: string
  allotted_amount: string
}

export interface Child {
  child_id: string
  employee_id: string
  child_sequence_no: number
  child_name: string
  child_dob: string
  is_active: boolean
  created_date: string
  eligibility: EligibilitySummary | null
}

export async function listChildren(): Promise<Child[]> {
  const { data } = await apiClient.get<Child[]>('/children')
  return data
}

export async function getChild(childId: string): Promise<Child> {
  const { data } = await apiClient.get<Child>(`/children/${childId}`)
  return data
}

export async function createChild(childName: string, childDob: string): Promise<Child> {
  const { data } = await apiClient.post<Child>('/children', {
    child_name: childName,
    child_dob: childDob,
  })
  return data
}

export async function previewEligibility(childDob: string): Promise<EligibilityPreview> {
  const { data } = await apiClient.post<EligibilityPreview>('/children/preview-eligibility', {
    child_dob: childDob,
  })
  return data
}
