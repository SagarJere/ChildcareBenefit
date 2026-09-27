import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { isAxiosError } from 'axios'
import { AlertCircle, ArrowLeft, Loader2 } from 'lucide-react'
import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { Link } from 'react-router-dom'
import { toast } from 'sonner'

import { addChildForEmployee } from '../../api/hr'
import { EmployeeAutocomplete } from '../../components/EmployeeAutocomplete'
import { addChildSchema, type AddChildFormValues } from '../children/childSchema'

function extractErrorMessage(error: unknown): string {
  if (isAxiosError(error)) {
    const backendMessage = error.response?.data?.message
    if (typeof backendMessage === 'string') {
      return backendMessage
    }
  }
  return 'Something went wrong. Please try again.'
}

export function HRAddChildPage() {
  const queryClient = useQueryClient()
  const [employeeId, setEmployeeId] = useState('')

  const {
    register,
    handleSubmit,
    reset,
    formState: { errors },
  } = useForm<AddChildFormValues>({
    resolver: zodResolver(addChildSchema),
    defaultValues: { childName: '', childDob: '' },
  })

  const createMutation = useMutation({
    mutationFn: (values: AddChildFormValues) =>
      addChildForEmployee(employeeId, values.childName, values.childDob),
    onSuccess: async (child) => {
      // Invalidates in case HR is adding a child for the employee
      // currently viewing their own My Children page in another tab.
      await queryClient.invalidateQueries({ queryKey: ['children'] })
      toast.success(`Added ${child.child_name} for ${child.employee_id}.`)
      reset({ childName: '', childDob: '' })
      setEmployeeId('')
    },
    onError: (error) => toast.error(extractErrorMessage(error)),
  })

  return (
    <div className="mx-auto max-w-lg space-y-6">
      <Link
        to="/hr/dashboard"
        className="flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-700"
      >
        <ArrowLeft className="h-4 w-4" aria-hidden="true" />
        Back to HR Dashboard
      </Link>

      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Add Child</h1>
        <p className="mt-1 text-slate-600">
          Add a child on behalf of an employee. The same rules apply as when an employee adds
          their own — including the two-child limit and eligibility calculation.
        </p>
        <Link
          to="/hr/children/bulk"
          className="mt-1 inline-block text-sm text-indigo-700 hover:underline"
        >
          Adding several children at once? Use bulk upload instead.
        </Link>
      </div>

      <form
        onSubmit={handleSubmit((values) => createMutation.mutate(values))}
        noValidate
        className="space-y-4 rounded-lg border border-slate-200 bg-white p-5 shadow-sm"
      >
        <EmployeeAutocomplete
          id="hrAddChildEmployee"
          label="Employee"
          value={employeeId}
          onChange={setEmployeeId}
        />

        <div>
          <label htmlFor="childName" className="block text-sm font-medium text-slate-700">
            Child's name
          </label>
          <input
            id="childName"
            type="text"
            aria-invalid={errors.childName ? 'true' : 'false'}
            className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2 text-slate-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            {...register('childName')}
          />
          {errors.childName && (
            <p className="mt-1 flex items-center gap-1 text-sm text-red-600">
              <AlertCircle className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
              {errors.childName.message}
            </p>
          )}
        </div>

        <div>
          <label htmlFor="childDob" className="block text-sm font-medium text-slate-700">
            Date of birth
          </label>
          <input
            id="childDob"
            type="date"
            max={new Date().toISOString().slice(0, 10)}
            aria-invalid={errors.childDob ? 'true' : 'false'}
            className="mt-1 block w-full rounded-md border border-slate-300 px-3 py-2 text-slate-900 shadow-sm focus:border-indigo-500 focus:outline-none focus:ring-1 focus:ring-indigo-500"
            {...register('childDob')}
          />
          {errors.childDob && (
            <p className="mt-1 flex items-center gap-1 text-sm text-red-600">
              <AlertCircle className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
              {errors.childDob.message}
            </p>
          )}
        </div>

        <button
          type="submit"
          disabled={!employeeId.trim() || createMutation.isPending}
          className="flex w-full items-center justify-center gap-2 rounded-md bg-indigo-700 px-4 py-2 font-medium text-white transition hover:bg-indigo-800 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {createMutation.isPending && (
            <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
          )}
          {createMutation.isPending ? 'Saving…' : 'Save Child'}
        </button>
      </form>
    </div>
  )
}
