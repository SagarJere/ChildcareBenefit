import { HeartHandshake, LogOut } from 'lucide-react'
import { NavLink, Outlet } from 'react-router-dom'

import { useAuth } from '../features/auth/useAuth'

const navLinkClasses = ({ isActive }: { isActive: boolean }) =>
  `rounded-md px-2.5 py-1.5 text-sm font-medium transition ${
    isActive ? 'bg-indigo-50 text-indigo-700' : 'text-slate-600 hover:bg-slate-100 hover:text-slate-900'
  }`

export function AppLayout() {
  const { employee, signOut } = useAuth()

  return (
    <div className="flex min-h-svh flex-col">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-[90rem] items-center gap-2 px-4 py-4">
          <HeartHandshake className="h-6 w-6 text-indigo-700" aria-hidden="true" />
          <span className="text-lg font-semibold text-slate-900">Childcare Benefit</span>

          <nav className="ml-6 hidden items-center gap-1 sm:flex">
            <NavLink to="/" end className={navLinkClasses}>
              Home
            </NavLink>
            <NavLink to="/children" className={navLinkClasses}>
              My Children
            </NavLink>
            <NavLink to="/claims" className={navLinkClasses}>
              My Claims
            </NavLink>
            <NavLink to="/eligibility" className={navLinkClasses}>
              Eligibility &amp; Payout
            </NavLink>
            <NavLink to="/payout" className={navLinkClasses}>
              My Payout
            </NavLink>
            {employee?.is_hr_approver && (
              <>
                <NavLink to="/hr/claims" className={navLinkClasses}>
                  HR Queue
                </NavLink>
                <NavLink to="/hr/reports" className={navLinkClasses}>
                  Reports
                </NavLink>
                <NavLink to="/hr/settings" className={navLinkClasses}>
                  Settings
                </NavLink>
              </>
            )}
          </nav>

          <div className="ml-auto flex items-center gap-3">
            {employee && (
              <span className="hidden text-sm text-slate-600 sm:inline">
                {employee.full_name ?? employee.employee_id}
              </span>
            )}
            <button
              type="button"
              onClick={signOut}
              className="flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-sm font-medium text-slate-600 transition hover:bg-slate-100 hover:text-slate-900"
            >
              <LogOut className="h-4 w-4" aria-hidden="true" />
              Sign out
            </button>
          </div>
        </div>
        <nav className="flex flex-wrap items-center gap-1 border-t border-slate-100 px-4 py-2 sm:hidden">
          <NavLink to="/" end className={navLinkClasses}>
            Home
          </NavLink>
          <NavLink to="/children" className={navLinkClasses}>
            My Children
          </NavLink>
          <NavLink to="/claims" className={navLinkClasses}>
            My Claims
          </NavLink>
          <NavLink to="/eligibility" className={navLinkClasses}>
            Eligibility &amp; Payout
          </NavLink>
          <NavLink to="/payout" className={navLinkClasses}>
            My Payout
          </NavLink>
          {employee?.is_hr_approver && (
            <>
              <NavLink to="/hr/claims" className={navLinkClasses}>
                HR Queue
              </NavLink>
              <NavLink to="/hr/reports" className={navLinkClasses}>
                Reports
              </NavLink>
              <NavLink to="/hr/settings" className={navLinkClasses}>
                Settings
              </NavLink>
            </>
          )}
        </nav>
      </header>
      <main className="mx-auto w-full max-w-[90rem] flex-1 px-4 py-8">
        <Outlet />
      </main>
    </div>
  )
}
