import { z } from 'zod'

export const invoiceDetailsSchema = z
  .object({
    invoiceDate: z
      .string()
      .min(1, 'Invoice date is required.')
      .refine((value) => !Number.isNaN(Date.parse(value)), 'Enter a valid date.')
      .refine((value) => new Date(value) <= new Date(), 'Invoice date cannot be in the future.'),
    invoiceNumber: z
      .string()
      .trim()
      .min(1, 'Invoice number is required.')
      .max(50, 'Invoice number must be 50 characters or fewer.'),
    invoiceAmount: z
      .string()
      .min(1, 'Invoice amount is required.')
      .refine(
        (value) => !Number.isNaN(Number(value)) && Number(value) > 0,
        'Enter an amount greater than zero.',
      ),
    institutionName: z
      .string()
      .trim()
      .min(1, 'Institution name is required.')
      .max(200, 'Institution name must be 200 characters or fewer.'),
    fromDate: z
      .string()
      .min(1, 'From date is required.')
      .refine((value) => !Number.isNaN(Date.parse(value)), 'Enter a valid date.'),
    toDate: z
      .string()
      .min(1, 'To date is required.')
      .refine((value) => !Number.isNaN(Date.parse(value)), 'Enter a valid date.'),
    comments: z
      .string()
      .max(1000, 'Comments must be 1000 characters or fewer.')
      .optional(),
  })
  // The child's age-in-months bounds (from month 14 through month 72) are
  // enforced server-side, where the child's date of birth is known — see
  // claim_service._validate_service_period. This only checks basic
  // ordering, which doesn't need that context.
  .refine((values) => new Date(values.fromDate) <= new Date(values.toDate), {
    message: 'From date must be on or before to date.',
    path: ['toDate'],
  })

export type InvoiceDetailsFormValues = z.infer<typeof invoiceDetailsSchema>
