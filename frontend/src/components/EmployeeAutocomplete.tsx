import { useQuery } from '@tanstack/react-query'
import { useState } from 'react'

import { getActiveEmployees } from '../api/auth'

interface EmployeeAutocompleteProps {
  id: string
  label: string
  value: string
  onChange: (employeeId: string) => void
}

/** A free-text Employee ID field with a name/ID autocomplete dropdown —
 * shared by every HR report's employee filter. Mirrors the login page's
 * own employee autocomplete (see DECISIONS_LOG.md item 42), reusing the
 * same public active-employees list. Typing a raw Employee ID directly
 * still works; the dropdown is just a faster way to find one by name. */
export function EmployeeAutocomplete({ id, label, value, onChange }: EmployeeAutocompleteProps) {
  const [isOpen, setIsOpen] = useState(false)

  const employeesQuery = useQuery({
    queryKey: ['active-employees'],
    queryFn: getActiveEmployees,
    staleTime: 5 * 60 * 1000,
  })

  const suggestions = (employeesQuery.data ?? [])
    .filter((option) => {
      const query = value.trim().toLowerCase()
      if (!query) return true
      return (
        option.employee_id.toLowerCase().includes(query) ||
        (option.full_name ?? '').toLowerCase().includes(query)
      )
    })
    .slice(0, 8)

  return (
    <div className="relative">
      <label htmlFor={id} className="block text-xs font-medium text-slate-500">
        {label}
      </label>
      <input
        id={id}
        type="text"
        autoComplete="off"
        role="combobox"
        aria-expanded={isOpen && suggestions.length > 0}
        aria-controls={`${id}-suggestions`}
        aria-autocomplete="list"
        value={value}
        onChange={(e) => {
          onChange(e.target.value)
          setIsOpen(true)
        }}
        onFocus={() => setIsOpen(true)}
        onBlur={() => setTimeout(() => setIsOpen(false), 150)}
        className="mt-1 rounded-md border border-slate-300 px-2 py-1.5 text-sm"
      />
      {isOpen && suggestions.length > 0 && (
        <ul
          id={`${id}-suggestions`}
          role="listbox"
          className="absolute z-10 mt-1 max-h-56 w-64 overflow-y-auto rounded-md border border-slate-200 bg-white py-1 shadow-lg"
        >
          {suggestions.map((option) => (
            <li key={option.employee_id} role="option" aria-selected="false">
              <button
                type="button"
                onMouseDown={(e) => {
                  e.preventDefault()
                  onChange(option.employee_id)
                  setIsOpen(false)
                }}
                className="flex w-full items-baseline justify-between gap-2 px-3 py-1.5 text-left text-sm hover:bg-indigo-50"
              >
                <span className="font-medium text-slate-900">
                  {option.full_name ?? option.employee_id}
                </span>
                <span className="text-xs text-slate-400">{option.employee_id}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
