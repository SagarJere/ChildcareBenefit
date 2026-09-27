import type { BulkChildRowResult } from '../../api/hr'

function toCsv(results: BulkChildRowResult[]): string {
  const header = 'row_number,employee_id,child_name,child_dob,status,message,child_id'
  const escape = (value: string) => `"${value.replace(/"/g, '""')}"`
  const lines = results.map((row) =>
    [
      row.row_number,
      escape(row.employee_id),
      escape(row.child_name),
      escape(row.child_dob),
      row.status,
      escape(row.message ?? ''),
      escape(row.child_id ?? ''),
    ].join(','),
  )
  return [header, ...lines].join('\n')
}

export function downloadBulkResultsCsv(results: BulkChildRowResult[], filename: string) {
  const blob = new Blob([toCsv(results)], { type: 'text/csv' })
  const url = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  document.body.appendChild(link)
  link.click()
  link.remove()
  window.URL.revokeObjectURL(url)
}
