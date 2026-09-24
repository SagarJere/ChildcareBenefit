import type { Attachment, PayoutScheduleEntry } from './claims'
import { apiClient } from '../lib/apiClient'
import type { EligibilitySummary } from './children'

export interface ApprovalHistoryEntry {
  approval_history_id: number
  action_by: string
  action_by_name: string
  action: 'Approved' | 'Rejected' | 'SentBack'
  previous_status: string
  new_status: string
  approved_amount: string | null
  remarks: string | null
  action_date: string
}

export interface HRClaimSummary {
  claim_id: number
  employee_id: string
  employee_name: string
  child_id: string
  child_name: string
  invoice_date: string
  invoice_number: string
  invoice_amount: string
  claim_amount: string
  institution_name: string | null
  from_date: string | null
  to_date: string | null
  claim_status: 'Draft' | 'Submitted' | 'HRReview' | 'Approved' | 'Rejected' | 'SentBack'
  comments: string | null
  submitted_date: string | null
  requires_documents: boolean
}

export interface HRClaimDetail extends HRClaimSummary {
  eligibility: EligibilitySummary | null
  attachments: Attachment[]
  approval_history: ApprovalHistoryEntry[]
  payout_schedule: PayoutScheduleEntry[]
}

export interface HRClaimListFilters {
  status?: string
  employee_id?: string
  child_id?: string
  date_from?: string
  date_to?: string
}

export async function listHRClaims(filters: HRClaimListFilters = {}): Promise<HRClaimSummary[]> {
  const { data } = await apiClient.get<HRClaimSummary[]>('/hr/claims', { params: filters })
  return data
}

export async function getHRClaimDetail(claimId: number): Promise<HRClaimDetail> {
  const { data } = await apiClient.get<HRClaimDetail>(`/hr/claims/${claimId}`)
  return data
}

export async function approveClaim(
  claimId: number,
  approvedAmount: string,
  remarks?: string,
): Promise<HRClaimDetail> {
  const { data } = await apiClient.post<HRClaimDetail>(`/hr/claims/${claimId}/approve`, {
    approved_amount: approvedAmount,
    remarks: remarks || undefined,
  })
  return data
}

export async function rejectClaim(claimId: number, remarks: string): Promise<HRClaimDetail> {
  const { data } = await apiClient.post<HRClaimDetail>(`/hr/claims/${claimId}/reject`, {
    remarks,
  })
  return data
}

export async function sendBackClaim(claimId: number, remarks: string): Promise<HRClaimDetail> {
  const { data } = await apiClient.post<HRClaimDetail>(`/hr/claims/${claimId}/send-back`, {
    remarks,
  })
  return data
}

export async function downloadHRAttachment(
  claimId: number,
  attachmentId: number,
  filename: string,
): Promise<void> {
  const response = await apiClient.get(
    `/hr/claims/${claimId}/attachments/${attachmentId}/download`,
    { responseType: 'blob' },
  )
  const url = window.URL.createObjectURL(response.data as Blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.URL.revokeObjectURL(url)
}
