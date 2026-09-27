import type { Attachment, PayoutScheduleEntry } from './claims'
import { apiClient } from '../lib/apiClient'
import type { Child, EligibilitySummary } from './children'

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
  submitted_date_from?: string
  submitted_date_to?: string
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

/** HR adding a child on behalf of another employee (user direction
 * 2026-09-26) — everything else about the child (2-child cap,
 * eligibility, first-year payout) works exactly as it does for a
 * self-service add; only who's recorded as having created it differs. */
export async function addChildForEmployee(
  employeeId: string,
  childName: string,
  childDob: string,
): Promise<Child> {
  const { data } = await apiClient.post<Child>('/hr/children', {
    employee_id: employeeId,
    child_name: childName,
    child_dob: childDob,
  })
  return data
}

export interface BulkChildRowResult {
  row_number: number
  employee_id: string
  child_name: string
  child_dob: string
  status: 'created' | 'failed'
  message: string | null
  child_id: string | null
}

export interface BulkAddChildrenResponse {
  total_rows: number
  succeeded: number
  failed: number
  results: BulkChildRowResult[]
}

/** Runs the whole file for real against a database SAVEPOINT the
 * backend always rolls back — the response reflects exactly what
 * committing the same file would do, without anything persisting.
 * Re-upload the same File object to `commitBulkAddChildren` once HR
 * has reviewed this preview. */
export async function previewBulkAddChildren(file: File): Promise<BulkAddChildrenResponse> {
  const formData = new FormData()
  formData.append('file', file)
  const { data } = await apiClient.post<BulkAddChildrenResponse>(
    '/hr/children/bulk/preview',
    formData,
  )
  return data
}

export async function commitBulkAddChildren(file: File): Promise<BulkAddChildrenResponse> {
  const formData = new FormData()
  formData.append('file', file)
  const { data } = await apiClient.post<BulkAddChildrenResponse>(
    '/hr/children/bulk/commit',
    formData,
  )
  return data
}

export interface BulkUploadBatchSummary {
  bulk_upload_id: number
  uploaded_by: string
  uploaded_file_name: string | null
  total_rows: number
  succeeded_count: number
  failed_count: number
  uploaded_date: string
}

export interface BulkUploadBatchDetail extends BulkUploadBatchSummary {
  results: BulkChildRowResult[]
}

/** Permanent audit trail of every bulk-add-children *commit* (never
 * preview, since preview never persists anything) — the defense against
 * a later dispute like "I uploaded 2, only 1 was added" (user direction
 * 2026-09-26). */
export async function getBulkUploadHistory(): Promise<BulkUploadBatchSummary[]> {
  const { data } = await apiClient.get<BulkUploadBatchSummary[]>('/hr/children/bulk/history')
  return data
}

export async function getBulkUploadBatch(bulkUploadId: number): Promise<BulkUploadBatchDetail> {
  const { data } = await apiClient.get<BulkUploadBatchDetail>(
    `/hr/children/bulk/history/${bulkUploadId}`,
  )
  return data
}
