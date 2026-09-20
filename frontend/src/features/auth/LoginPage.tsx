import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQuery } from '@tanstack/react-query'
import { isAxiosError } from 'axios'
import { AlertCircle, HeartHandshake, Loader2 } from 'lucide-react'
import { useState } from 'react'
import { useForm, useWatch } from 'react-hook-form'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'
import { toast } from 'sonner'

import { getActiveEmployees, login } from '../../api/auth'
import { loginSchema, type LoginFormValues } from './loginSchema'
import { useAuth } from './useAuth'

function extractErrorMessage(error: unknown): string {
  if (isAxiosError(error)) {
    const backendMessage = error.response?.data?.message
    if (typeof backendMessage === 'string') {
      return backendMessage
    }
    if (error.code === 'ECONNABORTED' || !error.response) {
      return 'Could not reach the server. Please check your connection and try again.'
    }
  }
  return 'Something went wrong. Please try again.'
}

export function LoginPage() {
  const { status, signIn } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [isSuggestionsOpen, setIsSuggestionsOpen] = useState(false)

  const employeesQuery = useQuery({
    queryKey: ['active-employees'],
    queryFn: getActiveEmployees,
    staleTime: 5 * 60 * 1000,
  })

  const {
    register,
    handleSubmit,
    setValue,
    control,
    formState: { errors },
  } = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: { employeeId: '' },
  })

  const { onChange: onEmployeeIdChange, ...employeeIdField } = register('employeeId')
  const employeeIdValue = useWatch({ control, name: 'employeeId' })

  const suggestions = (employeesQuery.data ?? [])
    .filter((option) => {
      const query = employeeIdValue.trim().toLowerCase()
      if (!query) return true
      return (
        option.employee_id.toLowerCase().includes(query) ||
        (option.full_name ?? '').toLowerCase().includes(query)
      )
    })
    .slice(0, 8)

  const loginMutation = useMutation({
    mutationFn: (values: LoginFormValues) => login(values.employeeId),
    onSuccess: (data) => {
      signIn(data.access_token, data.employee)
      const redirectTo = (location.state as { from?: string } | null)?.from ?? '/'
      navigate(redirectTo, { replace: true })
    },
    onError: (error) => {
      toast.error(extractErrorMessage(error))
    },
  })

  if (status === 'authenticated') {
    return <Navigate to="/" replace />
  }

  return (
    <div className="flex min-h-svh items-center justify-center bg-slate-50 px-4">
      <div className="w-full max-w-sm rounded-lg border border-slate-200 bg-white p-6 shadow-sm">
        <div className="mb-6 flex flex-col items-center gap-2 text-center">
          <HeartHandshake className="h-8 w-8 text-indigo-700" aria-hidden="true" />
          <h1 className="text-xl font-semibold text-slate-900">Childcare Benefit</h1>
          <p className="text-sm text-slate-500">Sign in with your Employee ID</p>
        </div>

        <form
          onSubmit={handleSubmit((values) => loginMutation.mutate(values))}
          noValidate
          className="space-y-4"
        >
          <div className="relative">
            <label htmlFor="employeeId" className="block text-sm font-medium text-slate-700">
              Employee ID
            </label>
            <input
              id="employeeId"
              type="text"
              autoComplete="off"
              autoFocus
              role="combobox"
              aria-expanded={isSuggestionsOpen && suggestions.length > 0}
              aria-controls="employeeId-suggestions"
              aria-autocomplete="list"
              aria-invalid={errors.employeeId ? 'true' : 'false'}
              aria-describedby={errors.employeeId ? 'employeeId-error' : undefined}
              className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2 text-slate-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              {...employeeIdField}
              onChange={(event) => {
                onEmployeeIdChange(event)
                setIsSuggestionsOpen(true)
              }}
              onFocus={() => setIsSuggestionsOpen(true)}
              onBlur={(event) => {
                employeeIdField.onBlur(event)
                setTimeout(() => setIsSuggestionsOpen(false), 150)
              }}
            />
            {isSuggestionsOpen && suggestions.length > 0 && (
              <ul
                id="employeeId-suggestions"
                role="listbox"
                className="absolute z-10 mt-1 max-h-56 w-full overflow-y-auto rounded-md border border-slate-200 bg-white py-1 shadow-lg"
              >
                {suggestions.map((option) => (
                  <li key={option.employee_id} role="option" aria-selected="false">
                    <button
                      type="button"
                      onMouseDown={(event) => {
                        event.preventDefault()
                        setValue('employeeId', option.employee_id, { shouldValidate: true })
                        setIsSuggestionsOpen(false)
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
            {errors.employeeId && (
              <p id="employeeId-error" className="mt-1 flex items-center gap-1 text-sm text-red-600">
                <AlertCircle className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
                {errors.employeeId.message}
              </p>
            )}
          </div>

          <button
            type="submit"
            disabled={loginMutation.isPending}
            className="flex w-full items-center justify-center gap-2 rounded-md bg-indigo-700 px-4 py-2 font-medium text-white transition hover:bg-indigo-800 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {loginMutation.isPending && <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />}
            {loginMutation.isPending ? 'Signing in…' : 'Sign in'}
          </button>
        </form>

        <p className="mt-4 text-center text-xs text-slate-400">
          Employee-ID-only sign-in is an internal Version 1 mode and will be replaced by your
          organization's single sign-on.
        </p>
      </div>
    </div>
  )
}
