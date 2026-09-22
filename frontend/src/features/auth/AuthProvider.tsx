import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useCallback, useEffect, useState, type ReactNode } from 'react'

import { fetchCurrentEmployee, type EmployeeProfile } from '../../api/auth'
import { setUnauthorizedHandler } from '../../lib/authEvents'
import { clearStoredToken, getStoredToken, setStoredToken } from '../../lib/authStorage'
import { AuthContext, type AuthStatus } from './context'

export function AuthProvider({ children }: { children: ReactNode }) {
  const queryClient = useQueryClient()
  const [token, setToken] = useState<string | null>(() => getStoredToken())

  const signOut = useCallback(() => {
    clearStoredToken()
    setToken(null)
    // Every cached query (children, claims, payout, HR reports, ...) is
    // keyed independently of who's signed in, so without this a different
    // user logging in in the same tab would briefly (or, for an in-flight
    // request that resolves late, not-so-briefly) see the previous user's
    // cached data. cancelQueries first so an in-flight request from the
    // outgoing session can't write stale data back in after clear().
    queryClient.cancelQueries()
    queryClient.clear()
  }, [queryClient])

  const signIn = (nextToken: string, employee: EmployeeProfile) => {
    setStoredToken(nextToken)
    setToken(nextToken)
    queryClient.setQueryData(['me'], employee)
  }

  useEffect(() => {
    setUnauthorizedHandler(signOut)
    return () => setUnauthorizedHandler(null)
  }, [signOut])

  const meQuery = useQuery({
    queryKey: ['me'],
    queryFn: async () => {
      try {
        return await fetchCurrentEmployee()
      } catch (error) {
        // The stored token is invalid/expired, or the employee is no
        // longer active — clear it here (inside the query itself, not a
        // render-phase effect) so the app falls back to "unauthenticated"
        // and the user is sent to the login screen.
        clearStoredToken()
        setToken(null)
        throw error
      }
    },
    enabled: token !== null,
    retry: false,
    staleTime: Infinity,
  })

  let status: AuthStatus = 'loading'
  if (token === null) {
    status = 'unauthenticated'
  } else if (meQuery.isSuccess) {
    status = 'authenticated'
  } else if (meQuery.isError) {
    status = 'unauthenticated'
  }

  return (
    <AuthContext.Provider value={{ status, employee: meQuery.data ?? null, signIn, signOut }}>
      {children}
    </AuthContext.Provider>
  )
}
