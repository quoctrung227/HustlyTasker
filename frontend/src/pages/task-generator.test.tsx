/** Mock component tests; root runs real UI and PostgreSQL E2E separately. */
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, useLocation, useNavigate } from 'react-router'
import { afterAll, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'
import { AppRoutes } from '../app/App'
import { AuthProvider } from '../features/auth/AuthProvider'
import { aiApi, aiKeys } from '../services/api/ai'
import type { AiAvailability, AiProposal, AiTaskPlan } from '../services/api/ai'
import { ApiError, apiClient } from '../services/api/client'
import { notificationApi } from '../services/api/collaboration'
import { authApi, tenantApi } from '../services/api/queries'
import type { Profile, User, Workspace } from '../services/api/types'
import { workApi, workKeys } from '../services/api/work-management'

const userId = '00000000-0000-4000-8000-000000000501'
const profileId = '00000000-0000-4000-8000-000000000502'
const workspaceId = '00000000-0000-4000-8000-000000000503'
const proposalId = '00000000-0000-4000-8000-000000000504'
const otherProfileId = '00000000-0000-4000-8000-000000000505'
const taskId = '00000000-0000-4000-8000-000000000506'
const base = `/profiles/${profileId}/workspaces/${workspaceId}/tasks`
const route = `${base}/generate`
const timestamp = new Date().toISOString()
const user: User = { id: userId, email: 'synthetic@example.test', username: 'synthetic', first_name: '', last_name: '', created_at: timestamp, email_verified: false }
const profile: Profile = { id: profileId, name: 'Nhóm mô phỏng', status: 'ACTIVE', created_at: timestamp, updated_at: timestamp }
const workspace: Workspace = { id: workspaceId, profile_id: profileId, name: 'Tháng mô phỏng', description: '', period: '2026-11-01', status: 'ACTIVE', created_at: timestamp, updated_at: timestamp }
const plan: AiTaskPlan = { contract_version: 'ai.task-plan.v1', tasks: [
  { local_ref: 'item_1', parent_ref: null, title: 'Công việc mẫu', description: 'Mô tả mẫu', priority: 'MEDIUM', proposed_deadline: null, notes: 'Ghi chú không lưu vào Task' },
  { local_ref: 'item_2', parent_ref: 'item_1', title: 'Công việc con mẫu', description: '', priority: 'LOW', proposed_deadline: null, notes: '' },
], assumptions: ['Dữ liệu giả lập'], warnings: ['Không có AI thật xử lý mô tả.'] }
const available: AiProposal = { contract_version: 'ai.v1', proposal_id: proposalId, revision: 1, scenario_id: 'task-tree-v1', status: 'AVAILABLE', mode: 'fixture_demo', generated_by_ai: false, persisted: true,
  created_at: timestamp, expires_at: new Date(Date.now() + 1800000).toISOString(), payload_expires_at: new Date(Date.now() + 604800000).toISOString(), confirmed_at: null, recovery_expires_at: null,
  payload: plan, created_tasks: null, usage: { input_tokens: 0, billable_output_tokens: 0, cost_usd: '0.000000', status: 'fixture_zero' } }
const confirmed: AiProposal = { ...available, status: 'CONFIRMED', payload: null, confirmed_at: timestamp, recovery_expires_at: new Date(Date.now() + 2592000000).toISOString(), created_tasks: { item_1: taskId, item_2: otherProfileId } }
const availability: AiAvailability = { contract_version: 'ai.v1', enabled: true, mode: 'fixture_demo', generated_by_ai: false,
  scenarios: [{ id: 'task-tree-v1', label: 'Mẫu cây công việc', brief: 'Mẫu giả lập cây công việc.' }, { id: 'subtitle-check-v1', label: 'Mẫu phụ đề', brief: 'Mẫu phụ đề.' }],
  limits: { max_brief_chars: 6000, max_tasks: 20, max_depth: 3, max_request_bytes: 32768 } }
const clone = <T,>(value: T): T => JSON.parse(JSON.stringify(value)) as T
function deferred<T>() { let resolve!: (value: T) => void; const promise = new Promise<T>((done) => { resolve = done }); return { promise, resolve } }
const network = () => new ApiError(0, 'network', 'Kết nối gián đoạn.')
const show = Object.getOwnPropertyDescriptor(HTMLDialogElement.prototype, 'showModal')
const close = Object.getOwnPropertyDescriptor(HTMLDialogElement.prototype, 'close')
beforeAll(() => {
  Object.defineProperty(HTMLDialogElement.prototype, 'showModal', { configurable: true, value(this: HTMLDialogElement) { this.open = true } })
  Object.defineProperty(HTMLDialogElement.prototype, 'close', { configurable: true, value(this: HTMLDialogElement) { this.open = false; this.dispatchEvent(new Event('close')) } })
})
afterAll(() => {
  if (show) Object.defineProperty(HTMLDialogElement.prototype, 'showModal', show); else Reflect.deleteProperty(HTMLDialogElement.prototype, 'showModal')
  if (close) Object.defineProperty(HTMLDialogElement.prototype, 'close', close); else Reflect.deleteProperty(HTMLDialogElement.prototype, 'close')
})
function Position() {
  const location = useLocation(), navigate = useNavigate()
  return <><output data-testid="location">{location.pathname}{location.search}</output><button type="button" onClick={() => navigate(`/profiles/${otherProfileId}/workspaces/${workspaceId}/tasks/generate`)}>Đổi phạm vi thử nghiệm</button><button type="button" onClick={() => navigate(`${route}?proposal=${otherProfileId}`)}>Đổi đề xuất thử nghiệm</button></>
}
function renderRoute(path = route) {
  const cache = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: Infinity, refetchOnWindowFocus: false } } })
  const view = render(<QueryClientProvider client={cache}><MemoryRouter initialEntries={[path]}><Position /><AuthProvider><AppRoutes /></AuthProvider></MemoryRouter></QueryClientProvider>)
  return { cache, ...view }
}
async function open() { const view = renderRoute(); await screen.findByRole('button', { name: 'Đề xuất công việc' }); return { ...view, actions: userEvent.setup() } }
async function generate() {
  const view = await open()
  await view.actions.click(screen.getByRole('button', { name: 'Đề xuất công việc' }))
  await screen.findByLabelText('Tên công việc 1')
  await waitFor(() => expect(screen.getByTestId('location')).toHaveTextContent(`?proposal=${proposalId}`))
  await waitFor(() => expect(aiApi.proposal).toHaveBeenCalled())
  await waitFor(() => expect(view.cache.isFetching({ queryKey: aiKeys.proposal(userId, profileId, workspaceId, proposalId) })).toBe(0))
  return view
}
async function openConfirmation(actions: ReturnType<typeof userEvent.setup>) {
  await actions.click(screen.getByRole('button', { name: 'Kiểm tra và xác nhận' }))
  return within(await screen.findByRole('dialog', { name: 'Xác nhận tạo công việc' }))
}
beforeEach(() => {
  vi.spyOn(authApi, 'me').mockResolvedValue(user)
  vi.spyOn(authApi, 'logout').mockResolvedValue(undefined)
  vi.spyOn(notificationApi, 'unreadCount').mockResolvedValue(0)
  vi.spyOn(tenantApi, 'profile').mockImplementation(async (id) => ({ ...profile, id }))
  vi.spyOn(tenantApi, 'workspace').mockImplementation(async (id, selected) => ({ ...workspace, id: selected, profile_id: id }))
  vi.spyOn(workApi, 'capabilities').mockResolvedValue({ createWorkspace: true, manageWorkspace: true, manageTasks: true, manageLifecycle: true })
  vi.spyOn(workApi, 'tasks').mockResolvedValue({ results: [], count: 0, next: null, previous: null })
  vi.spyOn(workApi, 'createTask').mockRejectedValue(new Error('Ordinary Task API must not be used by AI confirmation.'))
  vi.spyOn(aiApi, 'availability').mockResolvedValue(clone(availability))
  vi.spyOn(aiApi, 'generate').mockResolvedValue(clone(available))
  vi.spyOn(aiApi, 'proposal').mockResolvedValue(clone(available))
  vi.spyOn(aiApi, 'confirm').mockResolvedValue(clone(confirmed))
})

describe('fixture Smart Task Generator UI', () => {
  it('shows manager AI entry alongside ordinary manual creation', async () => {
    renderRoute(base)
    expect(await screen.findByRole('button', { name: 'Tạo công việc' })).toBeVisible()
    expect(await screen.findByRole('link', { name: 'Tạo công việc bằng AI' })).toHaveAttribute('href', route)
  })
  it('keeps entry and direct route read-only for a Viewer', async () => {
    vi.mocked(workApi.capabilities).mockResolvedValue({ createWorkspace: false, manageWorkspace: false, manageTasks: false, manageLifecycle: false })
    renderRoute()
    expect(await screen.findByText(/Chức năng đề xuất chỉ dành/)).toBeVisible()
    expect(aiApi.availability).not.toHaveBeenCalled()
    expect(aiApi.generate).not.toHaveBeenCalled()
    expect(screen.queryByRole('button', { name: 'Đề xuất công việc' })).not.toBeInTheDocument()
  })
  it('shows an honest disabled state without a generation request', async () => {
    vi.mocked(aiApi.availability).mockResolvedValue({ ...availability, enabled: false })
    renderRoute()
    expect(await screen.findByText('Bản mô phỏng chưa khả dụng')).toBeVisible()
    expect(screen.queryByRole('button', { name: 'Đề xuất công việc' })).not.toBeInTheDocument()
    expect(aiApi.generate).not.toHaveBeenCalled()
  })
  it('keeps the generator behind the existing authentication guard', async () => {
    vi.mocked(authApi.me).mockRejectedValue(new ApiError(403, 'forbidden', 'Đăng nhập lại.'))
    renderRoute()
    expect(await screen.findByRole('button', { name: 'Đăng nhập' })).toBeVisible()
    expect(aiApi.generate).not.toHaveBeenCalled()
  })
  it.each(['a'.repeat(6001), 'Nội dung\0không hợp lệ', '\uD800'])('rejects invalid optional synthetic brief before HTTP', async (brief) => {
    const { actions } = await open()
    fireEvent.change(screen.getByLabelText('Mô tả yêu cầu giả lập'), { target: { value: brief } })
    await actions.click(screen.getByRole('button', { name: 'Đề xuất công việc' }))
    expect(aiApi.generate).not.toHaveBeenCalled()
    expect(screen.getByLabelText('Mô tả yêu cầu giả lập')).toHaveAttribute('aria-invalid', 'true')
    expect(screen.getByRole('alert').parentElement).toHaveFocus()
  })
  it('generates only after a click and previews real contract fields without Task creation', async () => {
    const { actions } = await open()
    await actions.type(screen.getByLabelText('Mô tả yêu cầu giả lập'), 'Yêu cầu mô phỏng')
    expect(aiApi.generate).not.toHaveBeenCalled()
    expect(screen.getByText(/Kết quả là mẫu cố định/)).toBeVisible()
    await actions.click(screen.getByRole('button', { name: 'Đề xuất công việc' }))
    expect(await screen.findByLabelText('Tên công việc 1')).toHaveValue('Công việc mẫu')
    expect(screen.getByLabelText('Tên công việc 2')).toHaveValue('Công việc con mẫu')
    expect(aiApi.generate).toHaveBeenCalledExactlyOnceWith(profileId, workspaceId, { scenario_id: 'task-tree-v1', brief: 'Yêu cầu mô phỏng' }, expect.any(String), expect.any(AbortSignal))
    await waitFor(() => expect(screen.getByTestId('location')).toHaveTextContent(`?proposal=${proposalId}`))
    expect(aiApi.confirm).not.toHaveBeenCalled()
    expect(workApi.createTask).not.toHaveBeenCalled()
  })
  it('blocks rapid duplicate generate and preserves the original body/key for explicit recovery', async () => {
    const waiting = deferred<AiProposal>()
    vi.mocked(aiApi.generate).mockReturnValueOnce(waiting.promise)
    const { actions } = await open()
    const button = screen.getByRole('button', { name: 'Đề xuất công việc' })
    await actions.click(button)
    fireEvent.submit(screen.getByRole('form', { name: 'Yêu cầu đề xuất công việc' }))
    expect(button).toBeDisabled()
    expect(aiApi.generate).toHaveBeenCalledOnce()
    await act(async () => waiting.resolve(clone(available)))
    expect(await screen.findByLabelText('Tên công việc 1')).toBeVisible()
  })
  it('does not automatically retry an ambiguous generate; explicit recovery reuses the exact key/body', async () => {
    vi.mocked(aiApi.generate).mockRejectedValueOnce(network()).mockResolvedValueOnce(clone(available))
    const { actions } = await open()
    await actions.click(screen.getByRole('button', { name: 'Đề xuất công việc' }))
    const retry = await screen.findByRole('button', { name: 'Khôi phục đề xuất' })
    expect(aiApi.generate).toHaveBeenCalledOnce()
    await actions.click(retry)
    expect(await screen.findByLabelText('Tên công việc 1')).toBeVisible()
    expect(vi.mocked(aiApi.generate).mock.calls[1]?.slice(0, 4)).toEqual(vi.mocked(aiApi.generate).mock.calls[0]?.slice(0, 4))
  })
  it('edits the payload locally, displays the exact frozen confirmation and invalidates only this Workspace', async () => {
    const { actions, cache } = await generate()
    const sibling = workKeys.scope(otherProfileId, workspaceId)
    cache.setQueryData([...sibling, 'tasks'], { private: 'other tenant fixture' })
    cache.setQueryData([...workKeys.scope(profileId, workspaceId), 'tasks'], { old: true })
    await actions.clear(screen.getByLabelText('Tên công việc 1')); await actions.type(screen.getByLabelText('Tên công việc 1'), 'Tên đã sửa')
    await actions.selectOptions(screen.getByLabelText('Mức ưu tiên 1'), 'HIGH')
    expect(screen.getByRole('combobox', { name: 'Mức ưu tiên 1' })).toHaveValue('HIGH')
    const dialog = await openConfirmation(actions)
    expect(dialog.getByText('Tên đã sửa', { exact: true })).toBeVisible()
    expect(aiApi.confirm).not.toHaveBeenCalled()
    await actions.click(dialog.getByRole('button', { name: 'Xác nhận tạo công việc' }))
    expect(await screen.findByRole('heading', { name: 'Đã tạo công việc' })).toBeVisible()
    const call = vi.mocked(aiApi.confirm).mock.calls[0]
    expect(call?.slice(0, 3)).toEqual([profileId, workspaceId, proposalId])
    expect(call?.[3].payload.tasks[0]).toMatchObject({ title: 'Tên đã sửa', priority: 'HIGH', notes: plan.tasks[0]?.notes })
    expect(call?.[3].confirmed).toBe(true)
    expect(workApi.createTask).not.toHaveBeenCalled()
    expect(cache.getQueryState([...sibling, 'tasks'])?.isInvalidated).toBe(false)
    expect(cache.getQueryState([...workKeys.scope(profileId, workspaceId), 'tasks'])?.isInvalidated).toBe(true)
    expect(screen.queryByLabelText('Tên công việc 1')).not.toBeInTheDocument()
  })
  it('validates edited fields before offering confirmation', async () => {
    const { actions } = await generate()
    fireEvent.change(screen.getByLabelText('Tên công việc 1'), { target: { value: ' ' } })
    await actions.click(screen.getByRole('button', { name: 'Kiểm tra và xác nhận' }))
    expect(screen.getByLabelText('Tên công việc 1')).toHaveAttribute('aria-invalid', 'true')
    expect(screen.queryByRole('dialog', { name: 'Xác nhận tạo công việc' })).not.toBeInTheDocument()
    expect(aiApi.confirm).not.toHaveBeenCalled()
  })
  it('blocks duplicate confirm while a single atomic request is pending', async () => {
    const waiting = deferred<AiProposal>()
    vi.mocked(aiApi.confirm).mockReturnValueOnce(waiting.promise)
    const { actions } = await generate()
    const dialog = await openConfirmation(actions)
    const submit = dialog.getByRole('button', { name: 'Xác nhận tạo công việc' })
    await actions.click(submit); fireEvent.click(submit)
    expect(aiApi.confirm).toHaveBeenCalledOnce()
    expect(submit).toBeDisabled()
    await act(async () => waiting.resolve(clone(confirmed)))
    expect(await screen.findByRole('heading', { name: 'Đã tạo công việc' })).toBeVisible()
  })
  it('cancels a slower restoration GET before confirmation so consumed payload cannot return to cache', async () => {
    const waiting = deferred<AiProposal>()
    vi.mocked(aiApi.proposal).mockReturnValueOnce(waiting.promise)
    const { actions, cache } = await open()
    await actions.click(screen.getByRole('button', { name: 'Đề xuất công việc' }))
    await screen.findByLabelText('Tên công việc 1')
    await waitFor(() => expect(aiApi.proposal).toHaveBeenCalledOnce())
    const restoreSignal = vi.mocked(aiApi.proposal).mock.calls[0]?.[3]
    const dialog = await openConfirmation(actions)
    await actions.click(dialog.getByRole('button', { name: 'Xác nhận tạo công việc' }))
    expect(await screen.findByRole('heading', { name: 'Đã tạo công việc' })).toBeVisible()
    expect(restoreSignal?.aborted).toBe(true)
    await act(async () => waiting.resolve(clone(available)))
    expect(cache.getQueryData<AiProposal>(aiKeys.proposal(userId, profileId, workspaceId, proposalId))?.payload).toBeNull()
    expect(screen.queryByLabelText('Tên công việc 1')).not.toBeInTheDocument()
  })
  it('reconciles a lost confirmation with GET and never blindly resubmits', async () => {
    let committed = false
    vi.mocked(aiApi.proposal).mockImplementation(async () => clone(committed ? confirmed : available))
    vi.mocked(aiApi.confirm).mockImplementationOnce(async () => { committed = true; throw network() })
    const { actions } = await generate()
    const dialog = await openConfirmation(actions)
    await actions.click(dialog.getByRole('button', { name: 'Xác nhận tạo công việc' }))
    expect(await screen.findByRole('heading', { name: 'Đã tạo công việc' })).toBeVisible()
    expect(aiApi.confirm).toHaveBeenCalledOnce()
    expect(aiApi.proposal).toHaveBeenCalledWith(profileId, workspaceId, proposalId, expect.any(AbortSignal))
  })
  it('only offers explicit same-key confirmation replay after GET reports AVAILABLE', async () => {
    vi.mocked(aiApi.confirm).mockRejectedValueOnce(network()).mockResolvedValueOnce(clone(confirmed))
    const { actions } = await generate()
    const dialog = await openConfirmation(actions)
    await actions.click(dialog.getByRole('button', { name: 'Xác nhận tạo công việc' }))
    const retry = await screen.findByRole('button', { name: 'Gửi lại xác nhận cũ' })
    expect(screen.getByLabelText('Tên công việc 1')).toBeDisabled()
    await actions.click(retry)
    await actions.click(within(await screen.findByRole('dialog', { name: 'Xác nhận tạo công việc' })).getByRole('button', { name: 'Xác nhận tạo công việc' }))
    expect(await screen.findByRole('heading', { name: 'Đã tạo công việc' })).toBeVisible()
    expect(vi.mocked(aiApi.confirm).mock.calls[1]?.slice(0, 5)).toEqual(vi.mocked(aiApi.confirm).mock.calls[0]?.slice(0, 5))
  })
  it('discards a stale frozen confirmation when recovery reports a newer revision and requires a new human review', async () => {
    const { actions } = await generate()
    const updated = clone(available)
    updated.revision = 2
    if (updated.payload?.tasks[0]) updated.payload.tasks[0].title = 'Nội dung phiên bản mới'
    vi.mocked(aiApi.proposal).mockResolvedValueOnce(updated)
    vi.mocked(aiApi.confirm).mockRejectedValueOnce(new ApiError(409, 'conflict', 'Stale', {}, null, 'STALE_PROPOSAL')).mockResolvedValueOnce({ ...confirmed, revision: 2 })
    const oldDialog = await openConfirmation(actions)
    await actions.click(oldDialog.getByRole('button', { name: 'Xác nhận tạo công việc' }))
    await waitFor(() => expect(screen.getByLabelText('Tên công việc 1')).toHaveValue('Nội dung phiên bản mới'))
    expect(screen.queryByRole('button', { name: 'Gửi lại xác nhận cũ' })).not.toBeInTheDocument()
    expect(aiApi.confirm).toHaveBeenCalledOnce()
    const newDialog = await openConfirmation(actions)
    expect(newDialog.getByText('Nội dung phiên bản mới')).toBeVisible()
    expect(aiApi.confirm).toHaveBeenCalledOnce()
    await actions.click(newDialog.getByRole('button', { name: 'Xác nhận tạo công việc' }))
    expect(await screen.findByRole('heading', { name: 'Đã tạo công việc' })).toBeVisible()
    const calls = vi.mocked(aiApi.confirm).mock.calls
    expect(calls[1]?.[3].proposal_revision).toBe(2)
    expect(calls[1]?.[4]).not.toBe(calls[0]?.[4])
  })
  it('rejects recovery for a different proposal ID without allowing a frozen confirmation replay', async () => {
    const { actions } = await generate()
    vi.mocked(aiApi.proposal).mockResolvedValueOnce({ ...available, proposal_id: otherProfileId })
    vi.mocked(aiApi.confirm).mockRejectedValueOnce(network())
    const dialog = await openConfirmation(actions)
    await actions.click(dialog.getByRole('button', { name: 'Xác nhận tạo công việc' }))
    expect(await screen.findByText(/Kết quả khôi phục không đúng đề xuất/)).toBeVisible()
    expect(screen.queryByRole('button', { name: 'Gửi lại xác nhận cũ' })).not.toBeInTheDocument()
    expect(aiApi.confirm).toHaveBeenCalledOnce()
  })
  it('aborts a frozen confirmation if the proposal URL changes while its request is being prepared', async () => {
    const { actions, cache } = await generate()
    const cancellation = deferred<void>()
    vi.spyOn(cache, 'cancelQueries').mockReturnValueOnce(cancellation.promise)
    const nextProposal = deferred<AiProposal>()
    vi.mocked(aiApi.proposal).mockReturnValueOnce(nextProposal.promise)
    const dialog = await openConfirmation(actions)
    await actions.click(dialog.getByRole('button', { name: 'Xác nhận tạo công việc' }))
    fireEvent.click(screen.getByRole('button', { name: 'Đổi đề xuất thử nghiệm' }))
    await waitFor(() => expect(screen.getByTestId('location')).toHaveTextContent(`?proposal=${otherProfileId}`))
    await act(async () => cancellation.resolve())
    expect(aiApi.confirm).not.toHaveBeenCalled()
    expect(screen.queryByRole('dialog', { name: 'Xác nhận tạo công việc' })).not.toBeInTheDocument()
    expect(screen.queryByLabelText('Tên công việc 1')).not.toBeInTheDocument()
    await act(async () => nextProposal.resolve({ ...available, proposal_id: otherProfileId }))
    expect(await screen.findByLabelText('Tên công việc 1')).toBeVisible()
    const freshDialog = await openConfirmation(actions)
    await actions.click(freshDialog.getByRole('button', { name: 'Xác nhận tạo công việc' }))
    expect(aiApi.confirm).toHaveBeenCalledWith(profileId, workspaceId, otherProfileId, expect.any(Object), expect.any(String), expect.any(AbortSignal))
  })
  it('does not offer a replay if reconciliation itself fails', async () => {
    const { actions } = await generate()
    vi.mocked(aiApi.confirm).mockRejectedValueOnce(network())
    vi.mocked(aiApi.proposal).mockRejectedValueOnce(network())
    const dialog = await openConfirmation(actions)
    await actions.click(dialog.getByRole('button', { name: 'Xác nhận tạo công việc' }))
    expect(await screen.findByRole('button', { name: 'Kiểm tra trạng thái' })).toBeVisible()
    await waitFor(() => expect(screen.getByRole('button', { name: 'Kiểm tra trạng thái' })).toBeEnabled())
    expect(screen.queryByRole('button', { name: 'Gửi lại xác nhận cũ' })).not.toBeInTheDocument()
    expect(aiApi.confirm).toHaveBeenCalledOnce()
  })
  it('restores an already-confirmed proposal by scoped URL with no generation', async () => {
    vi.mocked(aiApi.proposal).mockResolvedValue(clone(confirmed))
    renderRoute(`${route}?proposal=${proposalId}`)
    expect(await screen.findByRole('heading', { name: 'Đã tạo công việc' })).toBeVisible()
    expect(screen.getByRole('link', { name: 'Mở công việc item_1' })).toHaveAttribute('href', `${base}/${taskId}`)
    expect(aiApi.generate).not.toHaveBeenCalled()
    expect(aiApi.confirm).not.toHaveBeenCalled()
  })
  it('shows expiry and cannot confirm an expired proposal', async () => {
    vi.mocked(aiApi.proposal).mockResolvedValue({ ...available, status: 'EXPIRED', payload: null, expires_at: new Date(Date.now() - 1).toISOString() })
    renderRoute(`${route}?proposal=${proposalId}`)
    expect(await screen.findByRole('heading', { name: 'Đề xuất đã hết hạn' })).toBeVisible()
    expect(screen.queryByRole('button', { name: 'Kiểm tra và xác nhận' })).not.toBeInTheDocument()
    expect(aiApi.confirm).not.toHaveBeenCalled()
  })
  it('renders sanitized throttling and disabled errors without request loops', async () => {
    vi.mocked(aiApi.generate).mockRejectedValueOnce(new ApiError(429, 'throttled', 'Wait', {}, 30))
    const { actions } = await open()
    await actions.click(screen.getByRole('button', { name: 'Đề xuất công việc' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Đã đạt giới hạn đề xuất')
    expect(aiApi.generate).toHaveBeenCalledOnce()
    vi.mocked(aiApi.generate).mockRejectedValueOnce(new ApiError(503, 'server', 'Disabled', {}, null, 'AI_DISABLED'))
    await actions.click(screen.getByRole('button', { name: 'Đề xuất công việc' }))
    expect(await screen.findByText('Bản mô phỏng chưa khả dụng')).toBeVisible()
    expect(screen.queryByLabelText('Mô tả yêu cầu giả lập')).not.toBeInTheDocument()
  })
  it('guards cancel/navigation against losing an unconfirmed local draft', async () => {
    const { actions } = await generate()
    await actions.click(screen.getByRole('link', { name: 'Hủy đề xuất' }))
    const dialog = within(await screen.findByRole('dialog', { name: 'Rời bản nháp đề xuất' }))
    await actions.click(dialog.getByRole('button', { name: 'Ở lại chỉnh sửa' }))
    expect(screen.getByLabelText('Tên công việc 1')).toHaveValue('Công việc mẫu')
    const event = new Event('beforeunload', { cancelable: true })
    window.dispatchEvent(event)
    expect(event.defaultPrevented).toBe(true)
    await actions.click(screen.getByRole('link', { name: 'Hủy đề xuất' }))
    await actions.click(within(await screen.findByRole('dialog', { name: 'Rời bản nháp đề xuất' })).getByRole('button', { name: 'Rời trang' }))
    await waitFor(() => expect(screen.getByTestId('location')).toHaveTextContent(base))
    expect(aiApi.confirm).not.toHaveBeenCalled()
  })
  it('aborts pending generation on Profile switch and does not populate the next scope', async () => {
    const waiting = deferred<AiProposal>()
    vi.mocked(aiApi.generate).mockReturnValueOnce(waiting.promise)
    const { actions, cache } = await open()
    await actions.click(screen.getByRole('button', { name: 'Đề xuất công việc' }))
    const signal = vi.mocked(aiApi.generate).mock.calls[0]?.[4]
    await actions.click(screen.getByRole('button', { name: 'Đổi phạm vi thử nghiệm' }))
    expect(signal?.aborted).toBe(true)
    await act(async () => waiting.resolve(clone(available)))
    expect(cache.getQueryData(aiKeys.proposal(userId, otherProfileId, workspaceId, proposalId))).toBeUndefined()
    expect(screen.queryByLabelText('Tên công việc 1')).not.toBeInTheDocument()
  })
  it('aborts a pending request on logout without repopulating private cache', async () => {
    const waiting = deferred<AiProposal>()
    vi.mocked(aiApi.generate).mockReturnValueOnce(waiting.promise)
    const { actions, cache } = await open()
    await actions.click(screen.getByRole('button', { name: 'Đề xuất công việc' }))
    const signal = vi.mocked(aiApi.generate).mock.calls[0]?.[4]
    await actions.click(screen.getByRole('button', { name: 'Đăng xuất' }))
    expect(await screen.findByRole('button', { name: 'Đăng nhập' })).toBeVisible()
    expect(signal?.aborted).toBe(true)
    await act(async () => waiting.resolve(clone(available)))
    expect(cache.getQueryData(aiKeys.proposal(userId, profileId, workspaceId, proposalId))).toBeUndefined()
  })
  it('clears a draft on quiet User change without leaving the same route', async () => {
    let forbidden: (() => void | Promise<void>) | null = null
    vi.spyOn(apiClient, 'setForbiddenHandler').mockImplementation((handler) => { forbidden = handler })
    const { cache } = await generate()
    vi.mocked(authApi.me).mockResolvedValue({ ...user, id: otherProfileId })
    await act(async () => { await forbidden?.() })
    expect(cache.getQueryData(aiKeys.proposal(userId, profileId, workspaceId, proposalId))).toBeUndefined()
    // A request in the new identity gets its own scope; old local draft is not reused.
    expect(aiApi.proposal).toHaveBeenCalledWith(profileId, workspaceId, proposalId, expect.any(AbortSignal))
  })
})
