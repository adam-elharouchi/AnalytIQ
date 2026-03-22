import { lazy, Suspense } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AuthProvider, useAuth } from '@/contexts/AuthContext'
import { Navigation } from '@/components/Navigation'
import { PrivateRoute } from '@/components/PrivateRoute'

// Lazy-load pages so each page bundle is only fetched when needed
const Login            = lazy(() => import('@/pages/Login'))
const StudentClasses   = lazy(() => import('@/pages/StudentClasses'))
const ProfessorDashboard = lazy(() => import('@/pages/ProfessorDashboard'))
const NotFound         = lazy(() => import('@/pages/NotFound'))

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,       // 30 s — matches legacy dataCache TTL
      retry: 1,
    },
  },
})

function HomeRedirect() {
  const { user, isAuthenticated } = useAuth()
  if (!isAuthenticated) return <Navigate to="/login" replace />
  switch (user?.role) {
    case 'professor':     return <Navigate to="/dashboard" replace />
    case 'superadmin':
    case 'tenant_admin':  return <Navigate to="/admin" replace />
    default:              return <Navigate to="/classes" replace />
  }
}

function AppRoutes() {
  return (
    <>
      <Navigation />
      <main className="main-content">
        <Suspense fallback={<div className="loading-state"><div className="spinner" /></div>}>
          <Routes>
            {/* Public */}
            <Route path="/login" element={<Login />} />

            {/* Student */}
            <Route
              path="/classes"
              element={
                <PrivateRoute roles={['student']}>
                  <StudentClasses />
                </PrivateRoute>
              }
            />

            {/* Professor */}
            <Route
              path="/dashboard"
              element={
                <PrivateRoute roles={['professor']}>
                  <ProfessorDashboard />
                </PrivateRoute>
              }
            />

            {/* Root → role-based redirect */}
            <Route path="/" element={<HomeRedirect />} />

            {/* 404 */}
            <Route path="*" element={<NotFound />} />
          </Routes>
        </Suspense>
      </main>
    </>
  )
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <BrowserRouter>
          <AppRoutes />
        </BrowserRouter>
      </AuthProvider>
    </QueryClientProvider>
  )
}
