import { z } from 'zod'

export const addChildSchema = z.object({
  childName: z
    .string()
    .trim()
    .min(1, 'Child name is required.')
    .max(200, 'Child name must be 200 characters or fewer.'),
  childDob: z
    .string()
    .min(1, 'Date of birth is required.')
    .refine((value) => !Number.isNaN(Date.parse(value)), 'Enter a valid date.')
    .refine((value) => new Date(value) <= new Date(), 'Date of birth cannot be in the future.'),
})

export type AddChildFormValues = z.infer<typeof addChildSchema>
