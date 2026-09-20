import { z } from 'zod'

export const invoiceDetailsSchema = z.object({
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
  comments: z
    .string()
    .max(1000, 'Comments must be 1000 characters or fewer.')
    .optional(),
})

export type InvoiceDetailsFormValues = z.infer<typeof invoiceDetailsSchema>
