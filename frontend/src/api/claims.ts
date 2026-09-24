import { apiClient } from '../lib/apiClient'

export type AttachmentType = 'RECEIPT_INVOICE' | 'PAYMENT_PROOF'

export interface Attachment {
  attachment_id: number
  claim_id: number
  attachment_type: AttachmentType
  original_file_name: string
  content_type: string
  file_size: number
  uploaded_date: string
}

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

export interface PayoutScheduleEntry {
  month: string
  allocated_amount: string
}

export interface Claim {
  claim_id: number
  child_id: string
  child_name: string
  eligibility_id: number
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
  created_date: string
  requires_documents: boolean
  attachments: Attachment[]
  approval_history: ApprovalHistoryEntry[]
  payout_schedule: PayoutScheduleEntry[]
}

export interface ClaimInput {
  child_id: string
  invoice_date: string
  invoice_number: string
  invoice_amount: string
  institution_name: string
  from_date: string
  to_date: string
  comments?: string
}

export async function listClaims(): Promise<Claim[]> {
  const { data } = await apiClient.get<Claim[]>('/claims')
  return data
}

export async function getClaim(claimId: number): Promise<Claim> {
  const { data } = await apiClient.get<Claim>(`/claims/${claimId}`)
  return data
}

export async function createClaim(input: ClaimInput): Promise<Claim> {
  const { data } = await apiClient.post<Claim>('/claims', input)
  return data
}

export async function updateClaim(
  claimId: number,
  input: Omit<ClaimInput, 'child_id'>,
): Promise<Claim> {
  const { data } = await apiClient.put<Claim>(`/claims/${claimId}`, input)
  return data
}

export async function submitClaim(claimId: number): Promise<Claim> {
  const { data } = await apiClient.post<Claim>(`/claims/${claimId}/submit`)
  return data
}

export async function deleteClaim(claimId: number): Promise<void> {
  await apiClient.delete(`/claims/${claimId}`)
}

export async function uploadAttachment(
  claimId: number,
  attachmentType: AttachmentType,
  file: File,
): Promise<Attachment> {
  const formData = new FormData()
  formData.append('attachment_type', attachmentType)
  formData.append('file', file)
  const { data } = await apiClient.post<Attachment>(
    `/claims/${claimId}/attachments`,
    formData,
  )
  return data
}

export async function downloadAttachment(
  claimId: number,
  attachmentId: number,
  filename: string,
): Promise<void> {
  const response = await apiClient.get(
    `/claims/${claimId}/attachments/${attachmentId}/download`,
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
