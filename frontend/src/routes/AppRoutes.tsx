import { Route, Routes } from 'react-router-dom'

import { HRRoute } from '../components/HRRoute'
import { ProtectedRoute } from '../components/ProtectedRoute'
import { LoginPage } from '../features/auth/LoginPage'
import { AddChildPage } from '../features/children/AddChildPage'
import { ChildrenPage } from '../features/children/ChildrenPage'
import { ClaimDetailPage } from '../features/claims/ClaimDetailPage'
import { ClaimsPage } from '../features/claims/ClaimsPage'
import { RaiseClaimPage } from '../features/claims/RaiseClaimPage'
import { EligibilityReportPage } from '../features/eligibility/EligibilityReportPage'
import { PayoutScheduleDetailPage } from '../features/eligibility/PayoutScheduleDetailPage'
import { HRClaimDetailPage } from '../features/hr/HRClaimDetailPage'
import { HRClaimsPage } from '../features/hr/HRClaimsPage'
import { HRSettingsPage } from '../features/hr/HRSettingsPage'
import { ReportsPage } from '../features/hr/ReportsPage'
import { MyPayoutPage } from '../features/payout/MyPayoutPage'
import { AppLayout } from '../layouts/AppLayout'
import { HomePage } from '../pages/HomePage'

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route element={<ProtectedRoute />}>
        <Route element={<AppLayout />}>
          <Route index element={<HomePage />} />
          <Route path="/children" element={<ChildrenPage />} />
          <Route path="/children/new" element={<AddChildPage />} />
          <Route path="/eligibility" element={<EligibilityReportPage />} />
          <Route path="/eligibility/:childId/schedule" element={<PayoutScheduleDetailPage />} />
          <Route path="/payout" element={<MyPayoutPage />} />
          <Route path="/claims" element={<ClaimsPage />} />
          <Route path="/claims/new" element={<RaiseClaimPage />} />
          <Route path="/claims/:claimId" element={<ClaimDetailPage />} />
          <Route element={<HRRoute />}>
            <Route path="/hr/claims" element={<HRClaimsPage />} />
            <Route path="/hr/claims/:claimId" element={<HRClaimDetailPage />} />
            <Route path="/hr/reports" element={<ReportsPage />} />
            <Route path="/hr/settings" element={<HRSettingsPage />} />
          </Route>
        </Route>
      </Route>
    </Routes>
  )
}
