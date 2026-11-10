/** Real route/auth/form lifecycles with mocked service responses, not browser E2E. */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, cleanup, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, useLocation, useNavigate } from 'react-router'
import { afterAll, afterEach, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'
import { AuthProvider } from '../features/auth/AuthProvider'
import { aiApi } from '../services/api/ai'
import { ApiError, apiClient } from '../services/api/client'
import { notificationApi } from '../services/api/collaboration'
import { authApi, queryKeys, tenantApi } from '../services/api/queries'
import type { Page, Profile, User, Workspace } from '../services/api/types'
import { workApi, workKeys } from '../services/api/work-management'
import type { Task, WorkCapabilities } from '../services/api/work-management'
import { AppRoutes } from './App'

const profileId = '00000000-0000-4000-8000-000000000801'
const workspaceId = '00000000-0000-4000-8000-000000000802'
const otherProfileId = '00000000-0000-4000-8000-000000000811'
const otherWorkspaceId = '00000000-0000-4000-8000-000000000812'
const created = '2026-10-26T00:00:00Z'
const user: User = { id: '00000000-0000-4000-8000-000000000803', email: 'stability@example.test', username: 'stability', first_name: 'Thành viên thử nghiệm', last_name: '', created_at: created, email_verified: false }
const otherUser: User = { ...user, id: '00000000-0000-4000-8000-000000000813', email: 'other-stability@example.test', username: 'other-stability', first_name: 'Thành viên tiếp theo' }
const profile: Profile = { id: profileId, name: 'Tổ chức thử nghiệm ổn định', status: 'ACTIVE', created_at: created, updated_at: created }
const workspace: Workspace = { id: workspaceId, profile_id: profileId, name: 'Không gian thử nghiệm ổn định', description: null, period: '2026-10-01', status: 'ACTIVE', created_at: created, updated_at: created }
const task: Task = { id: '00000000-0000-4000-8000-000000000804', workspace_id: workspaceId, parent_id: null, title: 'Công việc đã có', description: null, status: 'PENDING', priority: 'MEDIUM', deadline: null, active_assignment: null, can_start: false, can_submit: false, created_at: created, updated_at: created }
const capabilities: WorkCapabilities = { createWorkspace: true, manageWorkspace: true, manageTasks: true, manageLifecycle: true }
const base = `/profiles/${profileId}/workspaces/${workspaceId}/tasks`
const otherBase = `/profiles/${otherProfileId}/workspaces/${otherWorkspaceId}/tasks`
const tasksKey = workKeys.tasks(profileId, workspaceId, { ordering: '-created_at' }, 1)
const draft = { title: 'Bản nháp tổng hợp', description: 'Mô tả tổng hợp chưa gửi.', priority: 'HIGH', date: '03/12/2026', hour: '15', minute: '45', script: 'https://example.test/stability-script', compensation: '500.000' }
const page = <T,>(results: T[]): Page<T> => ({ count: results.length, results, next: null, previous: null })

function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>((done) => { resolve = done })
  return { promise, resolve }
}

// Test-only route driver; it never introduces product navigation or persistence.
function NavigationProbe() {
  const location = useLocation(), navigate = useNavigate()
  return <><output data-testid="stability-location">{location.pathname}</output><button type="button" onClick={() => navigate(otherBase)}>Chuyển phạm vi thử nghiệm</button></>
}

function renderApp() {
  const cache = new QueryClient({ defaultOptions: { queries: { retry: false, staleTime: 0, gcTime: Infinity, refetchOnWindowFocus: false } } })
  render(<QueryClientProvider client={cache}><MemoryRouter initialEntries={[base]}><AuthProvider><NavigationProbe /><AppRoutes /></AuthProvider></MemoryRouter></QueryClientProvider>)
  return cache
}

async function openDraft() {
  const interaction = userEvent.setup()
  await interaction.click(await screen.findByRole('button', { name: 'Tạo công việc' }))
  const dialog = screen.getByRole('dialog', { name: 'Tạo công việc' })
  await interaction.type(within(dialog).getByLabelText('Tên công việc'), draft.title)
  await interaction.type(within(dialog).getByLabelText('Mô tả'), draft.description)
  await interaction.selectOptions(within(dialog).getByLabelText('Mức ưu tiên'), draft.priority)
  fireEvent.change(within(dialog).getByLabelText('Ngày (dd/mm/yyyy)'), { target: { value: draft.date } })
  await interaction.selectOptions(within(dialog).getByLabelText('Giờ (00–23)'), draft.hour)
  await interaction.selectOptions(within(dialog).getByLabelText('Phút (00–59)'), draft.minute)
  fireEvent.change(within(dialog).getByLabelText('Link kịch bản'), { target: { value: draft.script } })
  fireEvent.change(within(dialog).getByLabelText('Tiền công dự kiến (VNĐ)'), { target: { value: draft.compensation } })
  return dialog
}

function expectSameDraft(dialog: HTMLElement) {
  expect(screen.getByRole('dialog', { name: 'Tạo công việc' })).toBe(dialog)
  expect(within(dialog).getByLabelText('Tên công việc')).toHaveValue(draft.title)
  expect(within(dialog).getByLabelText('Mô tả')).toHaveValue(draft.description)
  expect(within(dialog).getByLabelText('Mức ưu tiên')).toHaveValue(draft.priority)
  expect(within(dialog).getByLabelText('Ngày (dd/mm/yyyy)')).toHaveValue(draft.date)
  expect(within(dialog).getByLabelText('Giờ (00–23)')).toHaveValue(draft.hour)
  expect(within(dialog).getByLabelText('Phút (00–59)')).toHaveValue(draft.minute)
  expect(within(dialog).getByLabelText('Link kịch bản')).toHaveValue(draft.script)
  expect(within(dialog).getByLabelText('Tiền công dự kiến (VNĐ)')).toHaveValue(draft.compensation)
  expect(screen.getByTestId('stability-location')).toHaveTextContent(base)
  expect(workApi.createTask).not.toHaveBeenCalled()
}

const showModalDescriptor = Object.getOwnPropertyDescriptor(HTMLDialogElement.prototype, 'showModal')
const closeDescriptor = Object.getOwnPropertyDescriptor(HTMLDialogElement.prototype, 'close')

beforeAll(() => {
  Object.defineProperty(HTMLDialogElement.prototype, 'showModal', { configurable: true, value(this: HTMLDialogElement) { this.open = true } })
  Object.defineProperty(HTMLDialogElement.prototype, 'close', { configurable: true, value(this: HTMLDialogElement) { this.open = false; this.dispatchEvent(new Event('close')) } })
})

afterAll(() => {
  if (showModalDescriptor) Object.defineProperty(HTMLDialogElement.prototype, 'showModal', showModalDescriptor)
  else Reflect.deleteProperty(HTMLDialogElement.prototype, 'showModal')
  if (closeDescriptor) Object.defineProperty(HTMLDialogElement.prototype, 'close', closeDescriptor)
  else Reflect.deleteProperty(HTMLDialogElement.prototype, 'close')
})

beforeEach(() => {
  vi.spyOn(document, 'visibilityState', 'get').mockReturnValue('visible')
  vi.spyOn(authApi, 'me').mockResolvedValue(user)
  vi.spyOn(authApi, 'logout').mockResolvedValue(undefined)
  vi.spyOn(tenantApi, 'profiles').mockResolvedValue(page([profile]))
  vi.spyOn(tenantApi, 'profile').mockImplementation(async (id) => ({ ...profile, id }))
  vi.spyOn(tenantApi, 'workspace').mockImplementation(async (pid, wid) => ({ ...workspace, id: wid, profile_id: pid }))
  vi.spyOn(workApi, 'capabilities').mockResolvedValue(capabilities)
  vi.spyOn(workApi, 'tasks').mockResolvedValue(page([task]))
  vi.spyOn(workApi, 'createTask').mockResolvedValue(task)
  vi.spyOn(notificationApi, 'unreadCount').mockResolvedValue(0)
  vi.spyOn(aiApi, 'availability').mockResolvedValue({ contract_version: 'ai.v1', enabled: false, mode: 'fixture_demo', generated_by_ai: false,
    scenarios: [], limits: { max_brief_chars: 6000, max_tasks: 20, max_depth: 3, max_request_bytes: 32768 } })
})

afterEach(() => {
  cleanup()
  vi.useRealTimers()
  apiClient.setForbiddenHandler(null)
})

describe('authenticated Task draft continuity', () => {
  it.each(['focus', 'visibility', 'interval'] as const)('preserves the same form during pending and successful same-user %s verification', async (trigger) => {
    // Only interval scheduling is faked; Query/React/userEvent timeouts remain real.
    if (trigger === 'interval') vi.useFakeTimers({ toFake: ['setInterval', 'clearInterval'] })
    const cache = renderApp()
    const dialog = await openDraft()
    const identity = deferred<User>()
    vi.mocked(authApi.me).mockReturnValueOnce(identity.promise)
    cache.setQueryData(['stability-private-marker'], { owner: user.id })
    await act(async () => {
      if (trigger === 'focus') fireEvent(window, new Event('focus'))
      else if (trigger === 'visibility') fireEvent(document, new Event('visibilitychange'))
      else vi.advanceTimersByTime(60_000)
    })
    expect(authApi.me).toHaveBeenCalledTimes(2)
    expectSameDraft(dialog)
    await act(async () => { identity.resolve(user) })
    // Successful identity verification refreshes active authority/data queries
    // without relying on the old page-unmount side effect to observe revocation.
    await waitFor(() => {
      expect(tenantApi.profile).toHaveBeenCalledTimes(2)
      expect(tenantApi.workspace).toHaveBeenCalledTimes(2)
      expect(workApi.capabilities).toHaveBeenCalledTimes(2)
      expect(workApi.tasks).toHaveBeenCalledTimes(2)
    })
    await waitFor(() => expect(cache.isFetching()).toBe(0))
    expectSameDraft(dialog)
    expect(cache.getQueryData(['stability-private-marker'])).toEqual({ owner: user.id })
  })

  it('preserves the same draft during an ordinary Task-list data rerender', async () => {
    const cache = renderApp()
    const dialog = await openDraft()
    await act(async () => { cache.setQueryData(tasksKey, page([{ ...task, title: 'Danh sách vừa cập nhật' }])) })
    expectSameDraft(dialog)
    // Wait for Query's scheduled observer notification; the list is background
    // content while the modal is open, not an interactive navigation target.
    await waitFor(() => expect(screen.getByText('Danh sách vừa cập nhật', { selector: 'a' })).toBeInTheDocument())
    expectSameDraft(dialog)
  })

  it('preserves the same draft through pending and completed Task/Profile/Workspace refetches', async () => {
    const cache = renderApp()
    const dialog = await openDraft()
    const taskRefresh = deferred<Page<Task>>(), profileRefresh = deferred<Profile>(), workspaceRefresh = deferred<Workspace>()
    vi.mocked(workApi.tasks).mockReturnValueOnce(taskRefresh.promise)
    vi.mocked(tenantApi.profile).mockReturnValueOnce(profileRefresh.promise)
    vi.mocked(tenantApi.workspace).mockReturnValueOnce(workspaceRefresh.promise)
    let refreshed!: Promise<unknown>
    await act(async () => {
      refreshed = Promise.all([
        cache.refetchQueries({ queryKey: tasksKey, exact: true }),
        cache.refetchQueries({ queryKey: queryKeys.profile(profileId), exact: true }),
        cache.refetchQueries({ queryKey: queryKeys.workspace(profileId, workspaceId), exact: true }),
      ])
    })
    expect(workApi.tasks).toHaveBeenCalledTimes(2)
    expect(tenantApi.profile).toHaveBeenCalledTimes(2)
    expect(tenantApi.workspace).toHaveBeenCalledTimes(2)
    expectSameDraft(dialog)
    await act(async () => {
      taskRefresh.resolve(page([{ ...task, title: 'Danh sách mới sau refetch' }]))
      profileRefresh.resolve({ ...profile, name: 'Tổ chức đổi nhãn hợp lệ' })
      workspaceRefresh.resolve({ ...workspace, name: 'Không gian đổi nhãn hợp lệ' })
      await refreshed
    })
    await waitFor(() => expect(screen.getByRole('link', { name: 'Danh sách mới sau refetch' })).toBeInTheDocument())
    expectSameDraft(dialog)
  })

  it('clears the previous user draft and private cache when identity really changes in the same tenant', async () => {
    const cache = renderApp()
    const dialog = await openDraft()
    cache.setQueryData(['stability-private-marker'], { owner: user.id })
    vi.mocked(authApi.me).mockResolvedValue(otherUser)
    await act(async () => { fireEvent(window, new Event('focus')) })
    await waitFor(() => expect(screen.getByText(otherUser.first_name, { exact: true })).toBeInTheDocument())
    expect(dialog.isConnected).toBe(false)
    expect(screen.queryByRole('dialog', { name: 'Tạo công việc' })).not.toBeInTheDocument()
    expect(cache.getQueryData(['stability-private-marker'])).toBeUndefined()
    expect(screen.getByTestId('stability-location')).toHaveTextContent(base)
    await userEvent.setup().click(await screen.findByRole('button', { name: 'Tạo công việc' }))
    expect(screen.getByLabelText('Tên công việc')).toHaveValue('')
    expect(screen.getByLabelText('Mô tả')).toHaveValue('')
    expect(screen.getByLabelText('Link kịch bản')).toHaveValue('')
    expect(screen.getByLabelText('Tiền công dự kiến (VNĐ)')).toHaveValue('')
  })

  it('clears the previous tenant draft on an explicit route context switch', async () => {
    renderApp()
    const dialog = await openDraft()
    fireEvent.click(screen.getByRole('button', { name: 'Chuyển phạm vi thử nghiệm' }))
    await waitFor(() => expect(screen.getByTestId('stability-location')).toHaveTextContent(otherBase))
    expect(dialog.isConnected).toBe(false)
    expect(screen.queryByRole('dialog', { name: 'Tạo công việc' })).not.toBeInTheDocument()
    await userEvent.setup().click(await screen.findByRole('button', { name: 'Tạo công việc' }))
    const nextDialog = screen.getByRole('dialog', { name: 'Tạo công việc' })
    expect(within(nextDialog).getByLabelText('Tên công việc')).toHaveValue('')
    expect(within(nextDialog).getByLabelText('Mô tả')).toHaveValue('')
    expect(within(nextDialog).getByLabelText('Mức ưu tiên')).toHaveValue('MEDIUM')
    expect(within(nextDialog).getByLabelText('Ngày (dd/mm/yyyy)')).toHaveValue('')
    expect(within(nextDialog).getByLabelText('Giờ (00–23)')).toHaveValue('')
    expect(within(nextDialog).getByLabelText('Phút (00–59)')).toHaveValue('')
    expect(within(nextDialog).getByLabelText('Link kịch bản')).toHaveValue('')
    expect(within(nextDialog).getByLabelText('Tiền công dự kiến (VNĐ)')).toHaveValue('')
    expect(workApi.createTask).not.toHaveBeenCalled()
  })

  it('removes the open draft when routine identity success refreshes a genuinely denied Profile scope', async () => {
    renderApp()
    const dialog = await openDraft()
    vi.mocked(tenantApi.profile).mockRejectedValue(new ApiError(404, 'not-found', 'Nội dung không còn được phép.'))
    await act(async () => { fireEvent(window, new Event('focus')) })
    expect(await screen.findByRole('alert')).toHaveTextContent('Nội dung không còn được phép.')
    expect(tenantApi.profile).toHaveBeenCalledTimes(2)
    expect(authApi.me).toHaveBeenCalledTimes(2)
    expect(dialog.isConnected).toBe(false)
    expect(screen.queryByRole('dialog', { name: 'Tạo công việc' })).not.toBeInTheDocument()
    expect(screen.queryByDisplayValue(draft.title)).not.toBeInTheDocument()
    expect(screen.queryByRole('link', { name: task.title })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Đăng xuất' })).toBeInTheDocument()
    expect(workApi.createTask).not.toHaveBeenCalled()
  })

  it('does not turn a Task-list403 identity probe into an authority-refetch loop or a draft remount', async () => {
    let forbidden: (() => void | Promise<void>) | null = null
    vi.spyOn(apiClient, 'setForbiddenHandler').mockImplementation((handler) => { forbidden = handler })
    const cache = renderApp()
    const dialog = await openDraft()
    vi.mocked(workApi.tasks).mockImplementationOnce(async () => {
      await forbidden?.()
      throw new ApiError(403, 'forbidden', 'Bạn không có quyền đọc danh sách công việc.')
    })
    await act(async () => { await cache.refetchQueries({ queryKey: tasksKey, exact: true }) })
    expect(await screen.findByRole('alert')).toHaveTextContent('Bạn không có quyền đọc danh sách công việc.')
    // Allow scheduled observer notifications to settle, then check bounded calls.
    await act(async () => { await new Promise((resolve) => setTimeout(resolve, 35)) })
    expect(authApi.me).toHaveBeenCalledTimes(2)
    expect(workApi.tasks).toHaveBeenCalledTimes(2)
    expect(tenantApi.profile).toHaveBeenCalledTimes(1)
    expect(tenantApi.workspace).toHaveBeenCalledTimes(1)
    expect(workApi.capabilities).toHaveBeenCalledTimes(1)
    expect(cache.isFetching()).toBe(0)
    expectSameDraft(dialog)
  })
})
