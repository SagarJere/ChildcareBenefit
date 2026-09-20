import { z } from 'zod'

export const loginSchema = z.object({
  employeeId: z
    .string()
    .trim()
    .min(1, 'Employee ID is required.')
    .max(20, 'Employee ID must be 20 characters or fewer.'),
})

export type LoginFormValues = z.infer<typeof loginSchema>
