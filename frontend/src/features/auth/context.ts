import { createContext } from 'react'

import type { EmployeeProfile } from '../../api/auth'

export type AuthStatus = 'loading' | 'authenticated' | 'unauthenticated'

export interface AuthContextValue {
  status: AuthStatus
  employee: EmployeeProfile | null
  signIn: (token: string, employee: EmployeeProfile) => void
  signOut: () => void
}

export const AuthContext = createContext<AuthContextValue | undefined>(undefined)
