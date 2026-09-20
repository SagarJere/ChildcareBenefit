import { Navigate, Outlet } from 'react-router-dom'

import { useAuth } from '../features/auth/useAuth'

/**
 * UX-only gate: redirects non-HR employees away from HR screens instead
 * of showing them a page that will just fail to load. This is not the
 * authorization boundary — every HR endpoint independently enforces
 * access via get_current_hr_approver on the backend regardless of what
 * this component does.
 */
export function HRRoute() {
  const { employee } = useAuth()

  if (!employee?.is_hr_approver) {
    return <Navigate to="/" replace />
  }

  return <Outlet />
}
