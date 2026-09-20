import { BrowserRouter } from 'react-router-dom'
import { Toaster } from 'sonner'

import { AuthProvider } from './features/auth/AuthProvider'
import { AppRoutes } from './routes/AppRoutes'

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
        <Toaster richColors position="top-right" />
      </AuthProvider>
    </BrowserRouter>
  )
}

export default App
