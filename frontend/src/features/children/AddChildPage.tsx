import { zodResolver } from '@hookform/resolvers/zod'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { isAxiosError } from 'axios'
import { AlertCircle, ArrowLeft, Loader2 } from 'lucide-react'
import { useForm, useWatch } from 'react-hook-form'
import { Link, useNavigate } from 'react-router-dom'
import { toast } from 'sonner'

import { createChild, previewEligibility } from '../../api/children'
import { addChildSchema, type AddChildFormValues } from './childSchema'
import { EligibilitySummary } from './EligibilitySummary'

function extractErrorMessage(error: unknown): string {
  if (isAxiosError(error)) {
    const backendMessage = error.response?.data?.message
    if (typeof backendMessage === 'string') {
      return backendMessage
    }
  }
  return 'Something went wrong. Please try again.'
}

function isValidPastOrTodayDate(value: string): boolean {
  if (!value || Number.isNaN(Date.parse(value))) {
    return false
  }
  return new Date(value) <= new Date()
}

export function AddChildPage() {
  const navigate = useNavigate()
  const queryClient = useQueryClient()

  const {
    register,
    handleSubmit,
    control,
    formState: { errors },
  } = useForm<AddChildFormValues>({
    resolver: zodResolver(addChildSchema),
    defaultValues: { childName: '', childDob: '' },
  })

  const childDob = useWatch({ control, name: 'childDob' })
  const dobIsValid = isValidPastOrTodayDate(childDob ?? '')

  const previewQuery = useQuery({
    queryKey: ['eligibility-preview', childDob],
    queryFn: () => previewEligibility(childDob),
    enabled: dobIsValid,
    retry: false,
  })

  const createMutation = useMutation({
    mutationFn: (values: AddChildFormValues) => createChild(values.childName, values.childDob),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['children'] })
      toast.success('Child added successfully.')
      navigate('/children')
    },
    onError: (error) => {
      toast.error(extractErrorMessage(error))
    },
  })

  return (
    <div className="mx-auto max-w-lg space-y-6">
      <Link to="/children" className="flex items-center gap-1.5 text-sm text-slate-500 hover:text-slate-700">
        <ArrowLeft className="h-4 w-4" aria-hidden="true" />
        Back to My Children
      </Link>

      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Add Child</h1>
        <p className="mt-1 text-slate-600">
          Enter your child's details to see their eligibility before saving.
        </p>
      </div>

      <form
        onSubmit={handleSubmit((values) => createMutation.mutate(values))}
        noValidate
        className="space-y-4 rounded-lg border border-slate-200 bg-white p-5 shadow-sm"
      >
        <div>
          <label htmlFor="childName" className="block text-sm font-medium text-slate-700">
            Child's name
          </label>
          <input
            id="childName"
            type="text"
            autoFocus
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

        {dobIsValid && (
          <div className="rounded-md border border-slate-200 bg-slate-50 p-3">
            <h2 className="mb-2 text-sm font-medium text-slate-500">Eligibility preview</h2>

            {previewQuery.isPending && (
              <div className="flex items-center gap-2 text-sm text-slate-500">
                <Loader2 className="h-3.5 w-3.5 animate-spin" aria-hidden="true" />
                Calculating…
              </div>
            )}

            {previewQuery.isError && (
              <p className="flex items-center gap-1.5 text-sm text-red-600">
                <AlertCircle className="h-3.5 w-3.5 shrink-0" aria-hidden="true" />
                {extractErrorMessage(previewQuery.error)}
              </p>
            )}

            {previewQuery.data && (
              <EligibilitySummary
                financialYear={previewQuery.data.financial_year}
                eligibilityStartDate={previewQuery.data.eligibility_start_date}
                eligibilityEndDate={previewQuery.data.eligibility_end_date}
                eligibleMonths={previewQuery.data.eligible_months}
                monthlyBenefitAmount={previewQuery.data.monthly_benefit_amount}
                allottedAmount={previewQuery.data.allotted_amount}
              />
            )}
          </div>
        )}

        <button
          type="submit"
          disabled={createMutation.isPending}
          className="flex w-full items-center justify-center gap-2 rounded-md bg-indigo-700 px-4 py-2 font-medium text-white transition hover:bg-indigo-800 disabled:cursor-not-allowed disabled:opacity-60"
        >
          {createMutation.isPending && <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />}
          {createMutation.isPending ? 'Saving…' : 'Save Child'}
        </button>
      </form>
    </div>
  )
}
