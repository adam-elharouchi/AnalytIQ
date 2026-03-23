import { lazy, Suspense } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AuthProvider, useAuth } from '@/contexts/AuthContext'
import { Navigation } from '@/components/Navigation'
import { PrivateRoute } from '@/components/PrivateRoute'

// Lazy-load pages so each page bundle is only fetched when needed
const Login                 = lazy(() => import('@/pages/Login'))
const StudentClasses        = lazy(() => import('@/pages/StudentClasses'))
const ProfessorDashboard    = lazy(() => import('@/pages/ProfessorDashboard'))
const ProfessorClass        = lazy(() => import('@/pages/ProfessorClass'))
const SuperadminDashboard   = lazy(() => import('@/pages/SuperadminDashboard'))
const TenantAdminDashboard  = lazy(() => import('@/pages/TenantAdminDashboard'))
const NotFound              = lazy(() => import('@/pages/NotFound'))
const StudentClass          = lazy(() => import('@/pages/StudentClass'))
const ChapterView           = lazy(() => import('@/pages/ChapterView'))
const ExercisePage          = lazy(() => import('@/pages/ExercisePage'))
const Profile               = lazy(() => import('@/pages/Profile'))
const ResetPassword         = lazy(() => import('@/pages/ResetPassword'))
const CodeAssistant         = lazy(() => import('@/pages/CodeAssistant'))
const UploadAssistant       = lazy(() => import('@/pages/UploadAssistant'))

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      staleTime: 30_000,       // 30 s — matches legacy dataCache TTL
      retry: 1,
    },
  },
})

/** Renders the correct admin dashboard based on the authenticated user's role. */
function AdminDashboard() {
  const { user } = useAuth()
  if (user?.role === 'tenant_admin') return <TenantAdminDashboard />
  return <SuperadminDashboard />
}

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

            {/* Student class detail */}
            <Route
              path="/classes/:classId"
              element={
                <PrivateRoute roles={['student', 'superadmin', 'tenant_admin']}>
                  <StudentClass />
                </PrivateRoute>
              }
            />

            {/* Chapter PDF view */}
            <Route
              path="/chapter/:chapterId"
              element={
                <PrivateRoute roles={['student', 'superadmin', 'tenant_admin', 'professor']}>
                  <ChapterView />
                </PrivateRoute>
              }
            />

            {/* Exercise / practice playground */}
            <Route
              path="/exercise/:exerciseId"
              element={
                <PrivateRoute roles={['student', 'superadmin', 'tenant_admin', 'professor']}>
                  <ExercisePage />
                </PrivateRoute>
              }
            />

            {/* Admin (superadmin + tenant_admin) */}
            <Route
              path="/admin"
              element={
                <PrivateRoute roles={['superadmin', 'tenant_admin']}>
                  <AdminDashboard />
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

            {/* Professor class detail */}
            <Route
              path="/professor-class/:classId"
              element={
                <PrivateRoute roles={['professor', 'superadmin', 'tenant_admin']}>
                  <ProfessorClass />
                </PrivateRoute>
              }
            />

            {/* Profile */}
            <Route
              path="/profile"
              element={
                <PrivateRoute roles={['student', 'professor', 'superadmin', 'tenant_admin']}>
                  <Profile />
                </PrivateRoute>
              }
            />

            {/* Code assistant */}
            <Route
              path="/code-assistant"
              element={
                <PrivateRoute roles={['student', 'professor', 'superadmin', 'tenant_admin']}>
                  <CodeAssistant />
                </PrivateRoute>
              }
            />

            {/* Upload assistant */}
            <Route
              path="/upload-assistant"
              element={
                <PrivateRoute roles={['professor', 'superadmin', 'tenant_admin']}>
                  <UploadAssistant />
                </PrivateRoute>
              }
            />

            {/* Reset password — public */}
            <Route path="/reset-password" element={<ResetPassword />} />

            {/* Root + /home → role-based redirect */}
            <Route path="/" element={<HomeRedirect />} />
            <Route path="/home" element={<HomeRedirect />} />

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
