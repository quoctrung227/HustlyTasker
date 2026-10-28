import { Component, useEffect } from 'react'
import type { ReactNode } from 'react'
import { Navigate, Outlet, Route, Routes, useLocation, Link } from 'react-router'
import { Brand } from '../components/brand'
import { Card } from '../components/ui'
import { useAuth } from '../features/auth/AuthProvider'
import { AppLayout } from '../layouts/AppLayout'
import { LoginPage, SessionState } from '../pages/auth'
import { DashboardPage } from '../pages/overview'
import { ProfileDetailPage, ProfilesPage, WorkspaceDetailPage, WorkspacesPage } from '../pages/tenants'
import { TaskDetailPage, TasksPage } from '../pages/tasks'
import { NotificationsPage } from '../pages/notifications'
import { AccountPage, ForgotPasswordPage, RegisterPage, ResetPasswordPage } from '../pages/account-security'

function ProtectedRoute() {
  const auth = useAuth()
  const location = useLocation()
  if (auth.status === 'checking' || auth.status === 'unavailable') return <SessionState />
  if (auth.status === 'anonymous') return <Navigate to="/login" state={{ from: location.pathname + location.search }} replace />
  return <Outlet />
}

function StatusPage({ forbidden = false }: { forbidden?: boolean }) {
  useEffect(() => { document.title = `${forbidden ? 'Không có quyền truy cập' : 'Không tìm thấy trang'} · HustlyTasker` }, [forbidden])
  return <main className="status-page"><Brand /><Card><span className="status-page__code">{forbidden ? '403' : '404'}</span><h1>{forbidden ? 'Bạn chưa có quyền truy cập' : 'Không tìm thấy trang'}</h1><p>{forbidden ? 'Hãy liên hệ người quản trị nếu bạn cần truy cập nội dung này.' : 'Đường dẫn có thể đã thay đổi hoặc nội dung không khả dụng.'}</p><Link className="button button--primary" to="/dashboard">Về tổng quan</Link></Card></main>
}

export class AppErrorBoundary extends Component<{ children: ReactNode }, { failed: boolean }> {
  state = { failed: false }
  static getDerivedStateFromError() { return { failed: true } }
  componentDidCatch() { document.title = 'Không thể hiển thị trang · HustlyTasker' }
  render() {
    if (this.state.failed) return <main className="status-page"><a className="brand" href="/dashboard">HustlyTasker</a><Card><h1>Chưa thể hiển thị trang</h1><p>Vui lòng tải lại để thử lại.</p><a className="button button--primary" href="/dashboard">Tải lại trang</a></Card></main>
    return this.props.children
  }
}

export function AppRoutes() {
  return <Routes>
    <Route path="/login" element={<LoginPage />} />
    <Route path="/register" element={<RegisterPage />} />
    <Route path="/forgot-password" element={<ForgotPasswordPage />} />
    <Route path="/reset-password" element={<ResetPasswordPage />} />
    <Route element={<ProtectedRoute />}><Route element={<AppLayout />}>
      <Route index element={<Navigate to="/dashboard" replace />} />
      <Route path="/dashboard" element={<DashboardPage />} />
      <Route path="/account" element={<AccountPage />} />
      <Route path="/notifications" element={<NotificationsPage />} />
      <Route path="/profiles" element={<ProfilesPage />} />
      <Route path="/profiles/:profileId" element={<ProfileDetailPage />} />
      <Route path="/profiles/:profileId/workspaces" element={<WorkspacesPage />} />
      <Route path="/profiles/:profileId/workspaces/:workspaceId" element={<WorkspaceDetailPage />} />
      <Route path="/profiles/:profileId/workspaces/:workspaceId/tasks" element={<TasksPage />} />
      <Route path="/profiles/:profileId/workspaces/:workspaceId/tasks/:taskId" element={<TaskDetailPage />} />
    </Route></Route>
    <Route path="/403" element={<StatusPage forbidden />} />
    <Route path="/404" element={<StatusPage />} />
    <Route path="*" element={<StatusPage />} />
  </Routes>
}
