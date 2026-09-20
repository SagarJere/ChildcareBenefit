import { apiClient } from '../lib/apiClient'

export interface EmployeeProfile {
  memp_id: number
  employee_id: string
  full_name: string | null
  my_single_id: string | null
  join_date: string | null
  // UX convenience only — the backend independently enforces HR
  // authorization on every HR endpoint regardless of this flag.
  is_hr_approver: boolean
}

export interface LoginResponse {
  access_token: string
  token_type: string
  employee: EmployeeProfile
}

export interface ActiveEmployeeOption {
  employee_id: string
  full_name: string | null
}

export async function login(employeeId: string): Promise<LoginResponse> {
  const { data } = await apiClient.post<LoginResponse>('/auth/login', {
    employee_id: employeeId,
  })
  return data
}

// Deliberately public on the backend (no auth) — feeds this login page's
// autocomplete before the user has a token. See DECISIONS_LOG.md item 42.
export async function getActiveEmployees(): Promise<ActiveEmployeeOption[]> {
  const { data } = await apiClient.get<ActiveEmployeeOption[]>('/auth/active-employees')
  return data
}

export async function fetchCurrentEmployee(): Promise<EmployeeProfile> {
  const { data } = await apiClient.get<EmployeeProfile>('/me')
  return data
}
