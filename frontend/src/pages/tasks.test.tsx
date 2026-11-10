import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes, useLocation, useNavigate } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AppRoutes } from '../app/App'
import { AuthProvider, useAuth } from '../features/auth/AuthProvider'
import { ApiError, apiClient } from '../services/api/client'
import { authApi, queryKeys, tenantApi } from '../services/api/queries'
import type { Page, Profile, User, Workspace } from '../services/api/types'
import { workApi, workKeys } from '../services/api/work-management'
import type { Task, WorkCapabilities } from '../services/api/work-management'
import { WorkspacesPage } from './tenants'
import { TaskDetailPage, TasksPage, filtersFromSearch } from './tasks'

// Page tests exercise permission hints, scoped data and navigation. Actual
// mutation forms and HTTP contracts have their own focused tests/browser flows.
vi.mock('../features/tasks/TaskForms', () => ({
  TaskCreate: ({ canCreate, onSaved }: { canCreate?: boolean; onSaved: () => void }) => canCreate
    ? <button type="button" onClick={onSaved}>Tạo công việc</button> : null,
  TaskEdit: ({ canEdit, onDenied }: { canEdit?: boolean; onDenied: () => void }) => canEdit
    ? <button type="button" onClick={onDenied}>Chỉnh sửa công việc</button> : null,
  TaskAssign: ({ canAssign, onOpen }: { canAssign?: boolean; onOpen: () => void }) => canAssign
    ? <button type="button" onClick={onOpen}>Phân công công việc</button> : null,
  TaskStart: ({ active, task, onStart, onSaved, onDenied }: { active?: boolean; task: Task; onStart: () => Promise<Task>; onSaved: () => void; onDenied: () => void }) => active && task.can_start
    ? <button type="button" onClick={() => { void onStart().then(onSaved).catch(onDenied) }}>Bắt đầu công việc</button> : null,
}))

// This direct-page harness deliberately isolates child feature boundaries and
// does not mount application authentication for Task pages. The Workspace route
// requires the real current-User context for its scoped creation form. Keep AI availability disabled here;
// task-generator.test.tsx exercises the real entry with AuthProvider and both
// availability states. Do not mock auth globally: the 403 identity test below
// must continue exercising the actual provider and protected application route.
vi.mock('../features/ai/GeneratorEntry', () => ({
  GeneratorEntry: ({ allowed }: { allowed: boolean }) => allowed
    ? <button type="button" disabled>Tạo công việc bằng AI</button> : null,
}))

const profileId = '00000000-0000-4000-8000-000000000201'
const workspaceId = '00000000-0000-4000-8000-000000000202'
const taskId = '00000000-0000-4000-8000-000000000203'
const otherProfileId = '00000000-0000-4000-8000-000000000211'
const otherWorkspaceId = '00000000-0000-4000-8000-000000000212'
const created = '2026-10-26T00:00:00Z'
const profile: Profile = { id: profileId, name: 'Nhóm có quyền đọc', status: 'ACTIVE', created_at: created, updated_at: created }
const workspace: Workspace = { id: workspaceId, profile_id: profileId, name: 'Không gian tháng mười', description: 'Mô tả được cấp quyền', period: '2026-10-01', status: 'ACTIVE', created_at: created, updated_at: created }
const task: Task = { id: taskId, workspace_id: workspaceId, parent_id: null, title: 'Thiết kế lịch nhóm', description: 'Nội dung trong phạm vi', status: 'PENDING', priority: 'HIGH', deadline: null, active_assignment: null, can_start: false, can_submit: false, created_at: created, updated_at: created }
const deniedCapabilities: WorkCapabilities = { createWorkspace: false, manageWorkspace: false, manageTasks: false, manageLifecycle: false }
const managerCapabilities: WorkCapabilities = { createWorkspace: true, manageWorkspace: true, manageTasks: true, manageLifecycle: true }
const base = `/profiles/${profileId}/workspaces/${workspaceId}/tasks`
const page = <T,>(results: T[], count = results.length): Page<T> => ({ results, count, next: null, previous: null })

function TestNavigation() {
  const navigate = useNavigate(), location = useLocation()
  return <><output data-testid="location">{location.pathname}{location.search}</output><button type="button" onClick={() => navigate(`/profiles/${otherProfileId}/workspaces/${otherWorkspaceId}/tasks`)}>Đổi phạm vi</button></>
}

function AuthenticatedWorkspacePage() {
  const { status } = useAuth()
  return status === 'authenticated' ? <WorkspacesPage /> : null
}

function renderPage(path = base) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, staleTime: 0, gcTime: 0, refetchOnWindowFocus: false } } })
  render(<QueryClientProvider client={client}><MemoryRouter initialEntries={[path]}><TestNavigation /><Routes>
    <Route path="/profiles/:profileId/workspaces/:workspaceId/tasks" element={<TasksPage />} />
    <Route path="/profiles/:profileId/workspaces/:workspaceId/tasks/:taskId" element={<TaskDetailPage />} />
    <Route path="/profiles/:profileId/workspaces" element={<AuthProvider><AuthenticatedWorkspacePage /></AuthProvider>} />
  </Routes></MemoryRouter></QueryClientProvider>)
  return client
}

beforeEach(() => {
  vi.spyOn(tenantApi, 'profile').mockImplementation(async (id) => ({ ...profile, id }))
  vi.spyOn(tenantApi, 'workspace').mockImplementation(async (pid, wid) => ({ ...workspace, id: wid, profile_id: pid }))
  vi.spyOn(tenantApi, 'workspaces').mockResolvedValue(page([workspace]))
  vi.spyOn(workApi, 'capabilities').mockResolvedValue(deniedCapabilities)
  vi.spyOn(workApi, 'tasks').mockResolvedValue(page([task]))
  vi.spyOn(workApi, 'task').mockResolvedValue(task)
  vi.spyOn(workApi, 'subtasks').mockResolvedValue(page([]))
  vi.spyOn(workApi, 'members').mockResolvedValue(page([]))
  vi.spyOn(workApi, 'startTask').mockResolvedValue({ ...task, status: 'WORKING', can_start: false })
})

describe('Task URL filters and pagination', () => {
  it('allowlists current filter values and ignores retired hierarchy URL controls without hiding existing Tasks', () => {
    expect(filtersFromSearch(new URLSearchParams(`status=WORKING&priority=HIGH&ordering=deadline&parent_id=${taskId}&root_only=true&private=ignored`)))
      .toEqual({ status: 'WORKING', priority: 'HIGH', ordering: 'deadline' })
    expect(filtersFromSearch(new URLSearchParams('status=ADMIN&priority=999&ordering=title&parent_id=../../secret&deadline_before=not-a-date')))
      .toEqual({ ordering: '-created_at' })
  })

  it('uses a scoped query key and bounds malformed page values', async () => {
    const client = renderPage(`${base}?page=9007199254740992&status=WORKING&priority=HIGH`)
    expect(await screen.findByRole('link', { name: task.title })).toBeVisible()
    const filters = { status: 'WORKING', priority: 'HIGH', ordering: '-created_at' }
    expect(workApi.tasks).toHaveBeenCalledWith(profileId, workspaceId, filters, 1, expect.any(AbortSignal))
    expect(client.getQueryData(workKeys.tasks(profileId, workspaceId, filters as Parameters<typeof workKeys.tasks>[2], 1))).toEqual(page([task]))
  })

  it('resets pagination when applying filters and retains only supported query fields', async () => {
    vi.mocked(workApi.tasks).mockResolvedValue(page([task], 61))
    renderPage(`${base}?page=3&unknown=discard`)
    await screen.findByRole('link', { name: task.title })
    const user = userEvent.setup()
    await user.selectOptions(screen.getByLabelText('Trạng thái'), 'WORKING')
    await user.selectOptions(screen.getByLabelText('Mức ưu tiên'), 'URGENT')
    expect(screen.queryByLabelText('Cấu trúc')).not.toBeInTheDocument()
    await user.click(screen.getByRole('button', { name: 'Áp dụng bộ lọc' }))
    await waitFor(() => expect(workApi.tasks).toHaveBeenLastCalledWith(profileId, workspaceId, { status: 'WORKING', priority: 'URGENT', ordering: '-created_at' }, 1, expect.any(AbortSignal)))
    expect(screen.getByTestId('location')).not.toHaveTextContent('page=3')
    expect(screen.getByTestId('location')).not.toHaveTextContent('unknown=')
  })

  it('preserves server filters during pagination', async () => {
    vi.mocked(workApi.tasks).mockResolvedValue(page([task], 21))
    renderPage(`${base}?priority=HIGH&root_only=true`)
    await screen.findByRole('link', { name: task.title })
    await userEvent.setup().click(screen.getByRole('button', { name: 'Trang sau' }))
    await waitFor(() => expect(workApi.tasks).toHaveBeenLastCalledWith(profileId, workspaceId, { priority: 'HIGH', ordering: '-created_at' }, 2, expect.any(AbortSignal)))
  })

  it('labels local title search as page-only and never sends it to the server', async () => {
    renderPage()
    await screen.findByRole('link', { name: task.title })
    const calls = vi.mocked(workApi.tasks).mock.calls.length
    await userEvent.setup().type(screen.getByRole('searchbox', { name: 'Tìm trong trang' }), 'không khớp')
    expect(screen.getByRole('heading', { name: 'Chưa tìm thấy công việc' })).toBeVisible()
    expect(screen.getByText('Không có tên phù hợp trong trang hiện tại. Thử xóa từ khóa hoặc chuyển trang.')).toBeVisible()
    expect(workApi.tasks).toHaveBeenCalledTimes(calls)
  })

  it('blocks a reversed deadline range in the URL without requesting Tasks', async () => {
    renderPage(`${base}?deadline_after=2026-12-01T00:00:00Z&deadline_before=2026-01-01T00:00:00Z`)
    expect(await screen.findByRole('alert')).toHaveTextContent('Khoảng thời hạn trong đường dẫn chưa hợp lệ')
    expect(workApi.tasks).not.toHaveBeenCalled()
  })

  it('keeps reversed form dates local until the user fixes them', async () => {
    renderPage()
    await screen.findByRole('link', { name: task.title })
    const calls = vi.mocked(workApi.tasks).mock.calls.length
    fireEvent.change(screen.getByLabelText('Thời hạn từ ngày (UTC)'), { target: { value: '01/12/2026' } })
    fireEvent.change(screen.getByLabelText('Thời hạn đến ngày (UTC)'), { target: { value: '01/01/2026' } })
    await userEvent.setup().click(screen.getByRole('button', { name: 'Áp dụng bộ lọc' }))
    expect(screen.getByRole('alert')).toHaveTextContent('Khoảng thời hạn chưa hợp lệ')
    expect(workApi.tasks).toHaveBeenCalledTimes(calls)
  })
})

describe('Task access and tenant cache boundaries', () => {
  it('starts only from the backend current-user hint, including an eligible non-manager Editor', async () => {
    vi.mocked(workApi.task).mockResolvedValue({ ...task, status: 'ASSIGNED', can_start: true })
    const client = renderPage(`${base}/${taskId}`)
    const invalidate = vi.spyOn(client, 'invalidateQueries')
    const otherKey = workKeys.tasks(otherProfileId, otherWorkspaceId)
    client.setQueryDefaults(otherKey, { gcTime: Infinity })
    client.setQueryData(otherKey, page([]))
    await userEvent.setup().click(await screen.findByRole('button', { name: 'Bắt đầu công việc' }))
    expect(workApi.startTask).toHaveBeenCalledWith(profileId, workspaceId, taskId, undefined)
    expect(invalidate).toHaveBeenCalledWith({ queryKey: workKeys.scope(profileId, workspaceId) })
    expect(client.getQueryState(otherKey)?.isInvalidated).toBe(false)
    expect(await screen.findByText('Đã bắt đầu công việc.')).toBeVisible()
    expect(workApi.members).not.toHaveBeenCalled()
    expect(screen.queryByRole('button', { name: 'Chỉnh sửa công việc' })).not.toBeInTheDocument()
  })
  it('does not start merely because manager role hints are positive', async () => {
    vi.mocked(workApi.capabilities).mockResolvedValue(managerCapabilities)
    renderPage(`${base}/${taskId}`)
    await screen.findByRole('button', { name: 'Chỉnh sửa công việc' })
    expect(screen.queryByRole('button', { name: 'Bắt đầu công việc' })).not.toBeInTheDocument()
    expect(workApi.startTask).not.toHaveBeenCalled()
  })
  it('keeps Start unavailable for archived scope even with a stale positive task hint', async () => {
    vi.mocked(workApi.task).mockResolvedValue({ ...task, status: 'ASSIGNED', can_start: true })
    vi.mocked(tenantApi.workspace).mockResolvedValue({ ...workspace, status: 'ARCHIVED' })
    renderPage(`${base}/${taskId}`)
    await screen.findByRole('heading', { name: task.title })
    expect(screen.queryByRole('button', { name: 'Bắt đầu công việc' })).not.toBeInTheDocument()
  })
  it('waits for the authorized Workspace before fetching business data or hints', async () => {
    let resolve: ((value: Workspace) => void) | undefined
    vi.mocked(tenantApi.workspace).mockReturnValue(new Promise<Workspace>((done) => { resolve = done }))
    renderPage()
    await waitFor(() => expect(tenantApi.workspace).toHaveBeenCalledOnce())
    expect(workApi.tasks).not.toHaveBeenCalled()
    expect(workApi.capabilities).not.toHaveBeenCalled()
    await act(async () => { resolve?.(workspace) })
    expect(await screen.findByRole('link', { name: task.title })).toBeVisible()
  })

  it('shows scoped Tasks to read-only members without mutation controls or member requests', async () => {
    renderPage(`${base}/${taskId}`)
    expect(await screen.findByRole('heading', { name: task.title })).toBeVisible()
    expect(screen.queryByRole('button', { name: 'Chỉnh sửa công việc' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Phân công công việc' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Tạo công việc con' })).not.toBeInTheDocument()
    expect(workApi.members).not.toHaveBeenCalled()
  })

  it('presents manager actions only after active-scope capability discovery', async () => {
    vi.mocked(workApi.capabilities).mockResolvedValue(managerCapabilities)
    renderPage(`${base}/${taskId}`)
    expect(await screen.findByRole('button', { name: 'Chỉnh sửa công việc' })).toBeVisible()
    expect(screen.getByRole('button', { name: 'Phân công công việc' })).toBeVisible()
    expect(screen.queryByRole('button', { name: 'Tạo công việc con' })).not.toBeInTheDocument()
    expect(workApi.members).not.toHaveBeenCalled()
    await userEvent.setup().click(screen.getByRole('button', { name: 'Phân công công việc' }))
    await waitFor(() => expect(workApi.members).toHaveBeenCalledWith(profileId, workspaceId, 1, expect.any(AbortSignal)))
  })

  it.each(['Profile', 'Workspace'])('keeps an archived %s context read-only despite stale positive hints', async (kind) => {
    vi.mocked(workApi.capabilities).mockResolvedValue(managerCapabilities)
    if (kind === 'Profile') vi.mocked(tenantApi.profile).mockResolvedValue({ ...profile, status: 'ARCHIVED' })
    else vi.mocked(tenantApi.workspace).mockResolvedValue({ ...workspace, status: 'ARCHIVED' })
    renderPage(`${base}/${taskId}`)
    expect(await screen.findByRole('heading', { name: task.title })).toBeVisible()
    expect(screen.queryByRole('button', { name: 'Chỉnh sửa công việc' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Tạo công việc con' })).not.toBeInTheDocument()
    expect(workApi.members).not.toHaveBeenCalled()
  })

  it('removes old-scope content while the next tenant scope is loading', async () => {
    let resolve: ((value: Page<Task>) => void) | undefined
    vi.mocked(workApi.tasks).mockImplementation(async (_pid, wid) => wid === workspaceId ? page([task]) : new Promise<Page<Task>>((done) => { resolve = done }))
    const client = renderPage()
    await screen.findByRole('link', { name: task.title })
    await userEvent.setup().click(screen.getByRole('button', { name: 'Đổi phạm vi' }))
    await waitFor(() => expect(workApi.tasks).toHaveBeenCalledWith(otherProfileId, otherWorkspaceId, { ordering: '-created_at' }, 1, expect.any(AbortSignal)))
    expect(screen.queryByText(task.title)).not.toBeInTheDocument()
    await act(async () => { resolve?.(page([{ ...task, id: '00000000-0000-4000-8000-000000000213', workspace_id: otherWorkspaceId, title: 'Công việc phạm vi mới' }])) })
    expect(await screen.findByRole('link', { name: 'Công việc phạm vi mới' })).toBeVisible()
    expect(client.getQueryData(workKeys.tasks(otherProfileId, otherWorkspaceId, { ordering: '-created_at' }, 1))).toBeDefined()
    expect(screen.queryByText(task.title)).not.toBeInTheDocument()
  })

  it('hides mutations if capability revalidation fails while older positive data is cached', async () => {
    vi.mocked(workApi.capabilities).mockResolvedValueOnce(managerCapabilities).mockRejectedValue(new ApiError(403, 'forbidden', 'Không có quyền.'))
    const client = renderPage()
    expect(await screen.findByRole('button', { name: 'Tạo công việc' })).toBeVisible()
    await act(async () => { await client.invalidateQueries({ queryKey: workKeys.capabilities(profileId, workspaceId) }) })
    await waitFor(() => expect(client.getQueryState(workKeys.capabilities(profileId, workspaceId))?.status).toBe('error'))
    expect(screen.queryByRole('button', { name: 'Tạo công việc' })).not.toBeInTheDocument()
    expect(screen.getByText('Chưa xác minh được quyền thao tác. Các nút chỉnh sửa tạm thời được ẩn.')).toBeVisible()
  })

  it('does not keep Workspace creation visible after an authenticated Profile read becomes forbidden', async () => {
    const user: User = { id: '00000000-0000-4000-8000-000000000209', email: 'fixture@example.test', username: 'fixture', first_name: '', last_name: '', created_at: created, email_verified: false }
    vi.spyOn(authApi, 'me').mockResolvedValue(user)
    vi.mocked(workApi.capabilities).mockResolvedValue(managerCapabilities)
    const client = renderPage(`/profiles/${profileId}/workspaces`)
    expect(await screen.findByRole('button', { name: 'Tạo không gian' })).toBeVisible()
    vi.mocked(tenantApi.profile).mockRejectedValue(new ApiError(403, 'forbidden', 'Không có quyền truy cập tổ chức.'))
    await act(async () => { await client.invalidateQueries({ queryKey: queryKeys.profile(profileId) }) })
    expect(await screen.findByRole('alert')).toHaveTextContent('Không có quyền truy cập tổ chức.')
    expect(screen.queryByRole('button', { name: 'Tạo không gian' })).not.toBeInTheDocument()
  })

  it('invalidates exactly the current work scope after a successful mutation callback', async () => {
    vi.mocked(workApi.capabilities).mockResolvedValue(managerCapabilities)
    const client = renderPage()
    const invalidate = vi.spyOn(client, 'invalidateQueries')
    const otherKey = workKeys.tasks(otherProfileId, otherWorkspaceId, { ordering: '-created_at' }, 1)
    client.setQueryDefaults(otherKey, { gcTime: Infinity })
    client.setQueryData(otherKey, page([]))
    await userEvent.setup().click(await screen.findByRole('button', { name: 'Tạo công việc' }))
    expect(invalidate).toHaveBeenCalledWith({ queryKey: workKeys.scope(profileId, workspaceId) })
    expect(client.getQueryState(otherKey)?.isInvalidated).toBe(false)
    expect(await screen.findByText('Đã tạo công việc. Bạn có thể mở chi tiết để phân công.')).toBeVisible()
  })

  it('clears stale hints on mutation denial and refetches once without a capability loop', async () => {
    vi.mocked(workApi.capabilities).mockResolvedValueOnce(managerCapabilities).mockResolvedValue(deniedCapabilities)
    const client = renderPage(`${base}/${taskId}`)
    await userEvent.setup().click(await screen.findByRole('button', { name: 'Chỉnh sửa công việc' }))
    await waitFor(() => expect(workApi.capabilities).toHaveBeenCalledTimes(2))
    await act(async () => { await new Promise((resolve) => setTimeout(resolve, 35)) })
    expect(workApi.capabilities).toHaveBeenCalledTimes(2)
    expect(client.getQueryData(workKeys.capabilities(profileId, workspaceId))).toEqual(deniedCapabilities)
    expect(screen.queryByRole('button', { name: 'Chỉnh sửa công việc' })).not.toBeInTheDocument()
  })

  it('renders safe denied Task feedback without mounted private detail content', async () => {
    vi.mocked(workApi.task).mockRejectedValue(new ApiError(404, 'not-found', 'Nội dung không khả dụng.'))
    renderPage(`${base}/${taskId}`)
    expect(await screen.findByRole('alert')).toHaveTextContent('Nội dung không khả dụng.')
    expect(screen.queryByText(task.title)).not.toBeInTheDocument()
    expect(screen.queryByText(task.description || '')).not.toBeInTheDocument()
    expect(workApi.subtasks).not.toHaveBeenCalled()
  })
})

describe('existing hierarchy data without ordinary hierarchy controls', () => {
  it('keeps an existing child detail readable without fetching ancestors or rendering child controls', async () => {
    vi.mocked(workApi.capabilities).mockResolvedValue(managerCapabilities)
    const parents = [0, 1, 2].map((n) => `00000000-0000-4000-8000-00000000030${n}`)
    vi.mocked(workApi.task).mockImplementation(async (_pid, _wid, id) => {
      if (id === taskId) return { ...task, parent_id: parents[0] ?? null }
      const index = parents.indexOf(id)
      return { ...task, id, title: `Cấp tổ tiên ${index}`, parent_id: parents[index + 1] ?? null }
    })
    renderPage(`${base}/${taskId}`)
    expect(await screen.findByRole('heading', { name: task.title })).toBeVisible()
    expect(screen.queryByRole('navigation', { name: 'Phân cấp công việc' })).not.toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Công việc con' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Tạo công việc con' })).not.toBeInTheDocument()
    expect(workApi.task).toHaveBeenCalledOnce()
    expect(workApi.subtasks).not.toHaveBeenCalled()
  })

  it('does not interpret or rewrite a historical parent relation in the ordinary detail UI', async () => {
    vi.mocked(workApi.capabilities).mockResolvedValue(managerCapabilities)
    vi.mocked(workApi.task).mockResolvedValue({ ...task, parent_id: taskId })
    renderPage(`${base}/${taskId}`)
    expect(await screen.findByRole('heading', { name: task.title })).toBeVisible()
    expect(screen.queryByText('Chưa thể xác minh đầy đủ phân cấp.')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Tạo công việc con' })).not.toBeInTheDocument()
    expect(screen.queryByText('Invalid hierarchy')).not.toBeInTheDocument()
    expect(workApi.task).toHaveBeenCalledOnce()
  })
})

describe('ordinary Task list preserves historical records', () => {
  it('lists roots and children without hierarchy controls or root-only filtering', async () => {
    const child = { ...task, id: otherProfileId, parent_id: taskId, title: 'Công việc cũ vẫn hiển thị' }
    vi.mocked(workApi.tasks).mockResolvedValue(page([task, child]))
    renderPage(`${base}?root_only=true&parent_id=${taskId}`)
    expect(await screen.findByRole('link', { name: child.title })).toBeVisible()
    expect(screen.getByRole('link', { name: task.title })).toBeVisible()
    expect(screen.queryByText('CÔNG VIỆC CON')).not.toBeInTheDocument()
    expect(screen.queryByText('CÔNG VIỆC GỐC')).not.toBeInTheDocument()
    expect(workApi.tasks).toHaveBeenCalledWith(profileId, workspaceId, { ordering: '-created_at' }, 1, expect.any(AbortSignal))
  })
})

describe('Task brief with server-redacted compensation', () => {
  // These role scenarios model server-authorized projections; React does not
  // infer compensation access from role labels or assignment/User IDs.
  it.each(['Profile Owner', 'Profile Admin', 'Workspace Admin'])('shows authorized %s compensation with the existing metadata controls', async () => {
    vi.mocked(workApi.capabilities).mockResolvedValue(managerCapabilities)
    vi.mocked(workApi.task).mockResolvedValue({ ...task, estimated_compensation_vnd: '500000' })
    renderPage(`${base}/${taskId}`)
    expect(await screen.findByText('500.000 VNĐ')).toBeVisible()
    expect(screen.getByRole('button', { name: 'Chỉnh sửa công việc' })).toBeVisible()
  })

  it('shows safe document actions and exact whole-Task compensation to an authorized read-only assignee', async () => {
    vi.mocked(workApi.task).mockResolvedValue({ ...task, raw_video_url: 'https://example.test/raw', reference_video_url: 'https://example.test/reference', template_project_url: 'https://example.test/template', script_url: 'https://docs.google.com/document/d/synthetic/edit', estimated_compensation_vnd: '9007199254740993' })
    renderPage(`${base}/${taskId}`)
    expect(await screen.findByRole('heading', { name: 'Tài liệu và nguyên liệu' })).toBeVisible()
    for (const name of ['Mở video gốc', 'Mở video tham khảo', 'Mở dự án mẫu', 'Mở kịch bản']) {
      expect(screen.getByRole('link', { name })).toHaveAttribute('target', '_blank')
      expect(screen.getByRole('link', { name })).toHaveAttribute('rel', 'noopener noreferrer')
    }
    expect(screen.getByText('9.007.199.254.740.993 VNĐ')).toBeVisible()
    expect(screen.getByText(/Chỉ hiển thị khi máy chủ xác nhận quyền xem hiện tại/)).toBeVisible()
    expect(screen.queryByRole('button', { name: 'Chỉnh sửa công việc' })).not.toBeInTheDocument()
    expect(screen.queryByLabelText('Tiền công dự kiến (VNĐ)')).not.toBeInTheDocument()
  })
  it.each(['unassigned MEMBER', 'ordinary VIEWER'])('does not render compensation for a server-redacted %s while retaining URL/deadline access', async () => {
    vi.mocked(workApi.task).mockResolvedValue({ ...task, script_url: 'https://example.test/script', deadline: '2027-12-31T11:30:00Z', estimated_compensation_vnd: null })
    renderPage(`${base}/${taskId}`)
    expect(await screen.findByRole('heading', { name: task.title })).toBeVisible()
    expect(screen.getByRole('link', { name: 'Mở kịch bản' })).toHaveAttribute('href', 'https://example.test/script')
    expect(screen.getByText(/31\/12\/2027/)).toBeVisible()
    expect(screen.queryByRole('heading', { name: 'Tiền công dự kiến' })).not.toBeInTheDocument()
    expect(screen.queryByLabelText('Tiền công dự kiến (VNĐ)')).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Chỉnh sửa công việc' })).not.toBeInTheDocument()
    expect(document.body).not.toHaveTextContent('500.000')
    expect(document.body).not.toHaveTextContent('500000')
    expect(document.body).not.toHaveTextContent('VNĐ')
  })
  it('replaces formerly visible compensation in both DOM and QueryClient after a same-User redacted refresh', async () => {
    vi.mocked(workApi.task).mockResolvedValueOnce({ ...task, estimated_compensation_vnd: '9007199254740993' })
      .mockResolvedValue({ ...task, estimated_compensation_vnd: null })
    const client = renderPage(`${base}/${taskId}`)
    expect(await screen.findByText('9.007.199.254.740.993 VNĐ')).toBeVisible()
    const key = workKeys.task(profileId, workspaceId, taskId)
    await act(async () => { await client.invalidateQueries({ queryKey: key }) })
    await waitFor(() => expect(screen.queryByRole('heading', { name: 'Tiền công dự kiến' })).not.toBeInTheDocument())
    expect(client.getQueryData<Task>(key)?.estimated_compensation_vnd).toBeNull()
    expect(JSON.stringify(client.getQueryData(key))).not.toContain('9007199254740993')
    expect(document.body).not.toHaveTextContent('9.007.199.254.740.993')
    expect(screen.getByRole('heading', { name: task.title })).toBeVisible()
  })
  it.each([403, 404])('hides a formerly visible compensation after Task access is revoked with HTTP %s', async (status) => {
    vi.mocked(workApi.task).mockResolvedValueOnce({ ...task, estimated_compensation_vnd: '9007199254740993' })
      .mockRejectedValue(new ApiError(status, status === 403 ? 'forbidden' : 'not-found', 'Nội dung không khả dụng.'))
    const client = renderPage(`${base}/${taskId}`)
    expect(await screen.findByText('9.007.199.254.740.993 VNĐ')).toBeVisible()
    await act(async () => { await client.invalidateQueries({ queryKey: workKeys.task(profileId, workspaceId, taskId) }) })
    expect(await screen.findByRole('heading', { name: 'Nội dung không khả dụng' })).toBeVisible()
    expect(screen.queryByRole('heading', { name: 'Tiền công dự kiến' })).not.toBeInTheDocument()
    expect(document.body).not.toHaveTextContent('9.007.199.254.740.993')
    expect(workApi.task).toHaveBeenCalledTimes(2)
  })
  it('does not render a redacted compensation value on ordinary Task list rows', async () => {
    vi.mocked(workApi.tasks).mockResolvedValue(page([{ ...task, estimated_compensation_vnd: null }]))
    renderPage()
    expect(await screen.findByRole('link', { name: task.title })).toBeVisible()
    expect(document.body).not.toHaveTextContent('Tiền công dự kiến')
    expect(document.body).not.toHaveTextContent('500000')
    expect(document.body).not.toHaveTextContent('500.000')
  })
  it('does not render four empty documents or an absent compensation group', async () => {
    renderPage(`${base}/${taskId}`)
    await screen.findByRole('heading', { name: task.title })
    expect(screen.queryByRole('heading', { name: 'Tài liệu và nguyên liệu' })).not.toBeInTheDocument()
    expect(screen.queryByRole('heading', { name: 'Tiền công dự kiến' })).not.toBeInTheDocument()
  })
  it('displays zero VNĐ and safely omits an unsafe link even when a mock bypasses the API parser', async () => {
    vi.mocked(workApi.task).mockResolvedValue({ ...task, raw_video_url: 'javascript:alert(1)', estimated_compensation_vnd: '0' })
    renderPage(`${base}/${taskId}`)
    expect(await screen.findByText('0 VNĐ')).toBeVisible()
    expect(screen.queryByRole('link', { name: 'Mở video gốc' })).not.toBeInTheDocument()
  })
})

describe('Task permission403 identity stability', () => {
  it('keeps a valid SessionAuthentication identity without remount/refetch loops', async () => {
    const user: User = { id: '00000000-0000-4000-8000-000000000209', email: 'fixture@example.test', username: 'fixture', first_name: '', last_name: '', created_at: created, email_verified: false }
    vi.spyOn(authApi, 'me').mockResolvedValue(user)
    let forbidden: (() => void | Promise<void>) | null = null
    vi.spyOn(apiClient, 'setForbiddenHandler').mockImplementation((handler) => { forbidden = handler })
    vi.mocked(workApi.tasks).mockImplementation(async () => {
      await forbidden?.()
      throw new ApiError(403, 'forbidden', 'Bạn không có quyền thực hiện thao tác này.')
    })
    const client = new QueryClient({ defaultOptions: { queries: { retry: false, staleTime: 0, gcTime: 0, refetchOnWindowFocus: false } } })
    render(<QueryClientProvider client={client}><MemoryRouter initialEntries={[base]}><AuthProvider><AppRoutes /></AuthProvider></MemoryRouter></QueryClientProvider>)
    expect(await screen.findByRole('alert')).toHaveTextContent('Bạn không có quyền')
    await act(async () => { await new Promise((resolve) => setTimeout(resolve, 35)) })
    expect(authApi.me).toHaveBeenCalledTimes(2)
    expect(workApi.tasks).toHaveBeenCalledOnce()
    expect(workApi.capabilities).toHaveBeenCalledOnce()
    expect(screen.getByRole('button', { name: 'Đăng xuất' })).toBeVisible()
    expect(screen.queryByRole('button', { name: 'Đăng nhập' })).not.toBeInTheDocument()
  })
})

describe('Task detail reading layout and grouped deadline filters', () => {
  it('retains a very long description in a named keyboard-focusable region outside the fixed card heading', async () => {
    const description = `${'Nội dung giao việc rất dài.\n'.repeat(1600)}https://example.test/${'a'.repeat(2500)}\nKẾT THÚC NỘI DUNG`
    vi.mocked(workApi.task).mockResolvedValue({ ...task, description })
    renderPage(`${base}/${taskId}`)
    const region = await screen.findByRole('region', { name: 'Mô tả công việc' })
    expect(region.textContent).toBe(description)
    expect(region).toHaveAttribute('tabindex', '0')
    region.focus()
    expect(region).toHaveFocus()
    expect(region).not.toContainElement(screen.getByRole('heading', { name: 'Thông tin công việc' }))
    expect(region).not.toContainElement(screen.getByRole('heading', { name: 'Thời hạn và phân công' }))
    expect(workApi.task).toHaveBeenCalledOnce()
  })

  it('keeps the empty-description message inside the same readable region', async () => {
    vi.mocked(workApi.task).mockResolvedValue({ ...task, description: null })
    renderPage(`${base}/${taskId}`)
    expect(await screen.findByRole('region', { name: 'Mô tả công việc' })).toHaveTextContent('Công việc chưa có mô tả.')
  })

  it('groups both UTC deadline controls in from-to order without regrouping status or priority', async () => {
    renderPage()
    await screen.findByRole('link', { name: task.title })
    const group = screen.getByRole('group', { name: 'Khoảng thời hạn (UTC)' })
    const from = within(group).getByLabelText('Thời hạn từ ngày (UTC)')
    const to = within(group).getByLabelText('Thời hạn đến ngày (UTC)')
    expect(from.compareDocumentPosition(to) & Node.DOCUMENT_POSITION_FOLLOWING).not.toBe(0)
    expect(group).not.toContainElement(screen.getByLabelText('Trạng thái'))
    expect(group).not.toContainElement(screen.getByLabelText('Mức ưu tiên'))
  })

  it('preserves UTC filter boundaries and clears the whole date group through the existing actions', async () => {
    renderPage()
    await screen.findByRole('link', { name: task.title })
    const user = userEvent.setup()
    fireEvent.change(screen.getByLabelText('Thời hạn từ ngày (UTC)'), { target: { value: '01/12/2027' } })
    fireEvent.change(screen.getByLabelText('Thời hạn đến ngày (UTC)'), { target: { value: '31/12/2027' } })
    await user.click(screen.getByRole('button', { name: 'Áp dụng bộ lọc' }))
    await waitFor(() => expect(workApi.tasks).toHaveBeenLastCalledWith(profileId, workspaceId, {
      ordering: '-created_at', deadline_after: '2027-12-01T00:00:00Z', deadline_before: '2027-12-31T23:59:59.999999Z',
    }, 1, expect.any(AbortSignal)))
    await user.click(screen.getByRole('button', { name: 'Xóa bộ lọc' }))
    await waitFor(() => expect(workApi.tasks).toHaveBeenLastCalledWith(profileId, workspaceId, { ordering: '-created_at' }, 1, expect.any(AbortSignal)))
    expect(screen.getByLabelText('Thời hạn từ ngày (UTC)')).toHaveValue('')
    expect(screen.getByLabelText('Thời hạn đến ngày (UTC)')).toHaveValue('')
  })
})

describe('server-scoped assignee display names', () => {
  const assignment = { id: '00000000-0000-4000-8000-000000000281', profile_membership_id: '00000000-0000-4000-8000-000000000282', assigned_at: created }
  it.each([
    { display_name: 'Nguyễn An', expected: 'Nguyễn An' },
    { display_name: 'editor_synthetic', expected: 'editor_synthetic' },
    { display_name: null, expected: 'Thành viên không còn khả dụng' },
    { display_name: undefined, expected: 'Thành viên được phân công' },
    { display_name: assignment.profile_membership_id, expected: 'Thành viên được phân công' },
  ])('renders $expected instead of a raw membership UUID', async ({ display_name, expected }) => {
    vi.mocked(workApi.task).mockResolvedValue({ ...task, active_assignment: { ...assignment, display_name } })
    renderPage(`${base}/${taskId}`)
    expect(await screen.findByText(expected)).toBeVisible()
    expect(document.body.textContent).not.toContain(assignment.profile_membership_id)
    expect(document.body.textContent).not.toContain(assignment.id)
    expect(workApi.members).not.toHaveBeenCalled()
  })

  it('distinguishes an unassigned Task from an unavailable assignee', async () => {
    renderPage(`${base}/${taskId}`)
    expect(await screen.findByText('Chưa phân công')).toBeVisible()
    expect(screen.queryByText('Thành viên không còn khả dụng')).not.toBeInTheDocument()
    expect(workApi.members).not.toHaveBeenCalled()
  })

  it('uses the same safe name for Task list rows without loading the management roster', async () => {
    vi.mocked(workApi.tasks).mockResolvedValue(page([{ ...task, active_assignment: { ...assignment, display_name: 'Editor được giao' } }]))
    renderPage()
    expect(await screen.findByText('Editor được giao')).toBeVisible()
    expect(document.body.textContent).not.toContain(assignment.profile_membership_id)
    expect(workApi.members).not.toHaveBeenCalled()
  })

  it('replaces the old assignee name when a current Task response changes assignment', async () => {
    vi.mocked(workApi.task).mockResolvedValueOnce({ ...task, active_assignment: { ...assignment, display_name: 'Người nhận trước' } })
      .mockResolvedValue({ ...task, active_assignment: { ...assignment, id: '00000000-0000-4000-8000-000000000283', display_name: 'Người nhận mới' } })
    const client = renderPage(`${base}/${taskId}`)
    expect(await screen.findByText('Người nhận trước')).toBeVisible()
    await act(async () => { await client.invalidateQueries({ queryKey: workKeys.task(profileId, workspaceId, taskId) }) })
    expect(await screen.findByText('Người nhận mới')).toBeVisible()
    expect(screen.queryByText('Người nhận trước')).not.toBeInTheDocument()
    expect(workApi.members).not.toHaveBeenCalled()
  })

  it('does not retain the last known name after the server marks an existing assignment unavailable', async () => {
    vi.mocked(workApi.task).mockResolvedValueOnce({ ...task, active_assignment: { ...assignment, display_name: 'Tên được phép trước đây' } })
      .mockResolvedValue({ ...task, active_assignment: { ...assignment, display_name: null } })
    const client = renderPage(`${base}/${taskId}`)
    expect(await screen.findByText('Tên được phép trước đây')).toBeVisible()
    await act(async () => { await client.invalidateQueries({ queryKey: workKeys.task(profileId, workspaceId, taskId) }) })
    expect(await screen.findByText('Thành viên không còn khả dụng')).toBeVisible()
    expect(screen.queryByText('Tên được phép trước đây')).not.toBeInTheDocument()
    expect(client.getQueryData<Task>(workKeys.task(profileId, workspaceId, taskId))?.active_assignment?.display_name).toBeNull()
    expect(workApi.members).not.toHaveBeenCalled()
  })
})
