import { useQuery } from '@tanstack/react-query'

import { getFinancialYears } from '../api/reports'

interface FinancialYearSelectProps {
  id: string
  label: string
  value: string
  onChange: (financialYear: string) => void
}

/** A financial-year dropdown populated from every FY that actually has
 * data — shared by every HR report's financial-year filter. */
export function FinancialYearSelect({ id, label, value, onChange }: FinancialYearSelectProps) {
  const { data } = useQuery({
    queryKey: ['financial-years'],
    queryFn: getFinancialYears,
    staleTime: 5 * 60 * 1000,
  })

  return (
    <div>
      <label htmlFor={id} className="block text-xs font-medium text-slate-500">
        {label}
      </label>
      <select
        id={id}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="mt-1 rounded-md border border-slate-300 px-2 py-1.5 text-sm"
      >
        <option value="">All</option>
        {(data ?? []).map((fy) => (
          <option key={fy} value={fy}>
            {fy}
          </option>
        ))}
      </select>
    </div>
  )
}
