import type { PayoutReportRow } from '../api/reports'
import { formatCurrency, formatDate } from '../lib/format'

const MONTH_COLUMNS: { key: keyof PayoutReportRow; label: string }[] = [
  { key: 'apr', label: 'Apr' },
  { key: 'may', label: 'May' },
  { key: 'jun', label: 'Jun' },
  { key: 'jul', label: 'Jul' },
  { key: 'aug', label: 'Aug' },
  { key: 'sep', label: 'Sep' },
  { key: 'oct', label: 'Oct' },
  { key: 'nov', label: 'Nov' },
  { key: 'dec', label: 'Dec' },
  { key: 'jan', label: 'Jan' },
  { key: 'feb', label: 'Feb' },
  { key: 'mar', label: 'Mar' },
]

/** The Employee + Child + Financial-Year, April-through-March payout
 * breakdown — shared by HR's payout report and the employee's own
 * equivalent view, since both read the exact same shape from the API. */
export function PayoutReportTable({ rows }: { rows: PayoutReportRow[] }) {
  return (
    <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
      <table className="min-w-full divide-y divide-slate-100 text-sm">
        <thead className="bg-slate-50 text-left text-xs font-medium uppercase tracking-wide text-slate-500">
          <tr>
            <th className="px-3 py-3">Employee ID</th>
            <th className="px-3 py-3">Employee</th>
            <th className="px-3 py-3">Child</th>
            <th className="px-3 py-3">Child DOB</th>
            <th className="px-3 py-3">FY</th>
            {MONTH_COLUMNS.map((column) => (
              <th key={column.key} className="px-2 py-3 text-right">
                {column.label}
              </th>
            ))}
            <th className="px-3 py-3 text-right">Total</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {rows.map((row) => (
            <tr key={`${row.employee_id}-${row.child_id}-${row.financial_year}`}>
              <td className="px-3 py-3 whitespace-nowrap text-slate-600">{row.employee_id}</td>
              <td className="px-3 py-3 whitespace-nowrap text-slate-800">{row.employee_name}</td>
              <td className="px-3 py-3 whitespace-nowrap text-slate-600">{row.child_name}</td>
              <td className="px-3 py-3 whitespace-nowrap text-slate-600">
                {formatDate(row.child_dob)}
              </td>
              <td className="px-3 py-3 text-slate-600">{row.financial_year}</td>
              {MONTH_COLUMNS.map((column) => {
                const value = Number(row[column.key])
                return (
                  <td key={column.key} className="px-2 py-3 text-right text-slate-600">
                    {value === 0 ? '—' : formatCurrency(row[column.key] as string)}
                  </td>
                )
              })}
              <td className="px-3 py-3 text-right font-medium text-slate-900">
                {formatCurrency(row.total_payout)}
              </td>
            </tr>
          ))}
          {rows.length === 0 && (
            <tr>
              <td colSpan={18} className="px-4 py-6 text-center text-slate-400">
                No payouts match these filters.
              </td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  )
}
