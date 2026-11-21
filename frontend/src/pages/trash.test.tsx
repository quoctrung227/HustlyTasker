import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router'
import { afterAll, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'
import { TrashPage } from './trash'
import { TrashDeleteAction } from '../features/trash/TrashActions'
import { ApiError } from '../services/api/client'
import { trashApi } from '../services/api/trash'
import type { TrashItem } from '../services/api/trash'
import type { Page } from '../services/api/types'
import { trashIds, trashItem } from '../test/trash-fixtures'

let currentUser = { id: trashIds.user }
vi.mock('../features/auth/AuthProvider', () => ({ useAuth: () => ({ user: currentUser }) }))
vi.mock('../services/api/trash', async (original) => ({ ...await original<typeof import('../services/api/trash')>(), trashApi: { list: vi.fn(), delete: vi.fn(), restore: vi.fn(), purge: vi.fn() } }))
const showDescriptor = Object.getOwnPropertyDescriptor(HTMLDialogElement.prototype, 'showModal')
const closeDescriptor = Object.getOwnPropertyDescriptor(HTMLDialogElement.prototype, 'close')
beforeAll(() => {
  Object.defineProperty(HTMLDialogElement.prototype, 'showModal', { configurable: true, value() { this.setAttribute('open', '') } })
  Object.defineProperty(HTMLDialogElement.prototype, 'close', { configurable: true, value() { this.removeAttribute('open') } })
})
afterAll(() => {
  if (showDescriptor) Object.defineProperty(HTMLDialogElement.prototype, 'showModal', showDescriptor)
  else Reflect.deleteProperty(HTMLDialogElement.prototype, 'showModal')
  if (closeDescriptor) Object.defineProperty(HTMLDialogElement.prototype, 'close', closeDescriptor)
  else Reflect.deleteProperty(HTMLDialogElement.prototype, 'close')
})
const page = (results: TrashItem[] = [], count = results.length): Page<TrashItem> => ({ count, results, next: null, previous: null })
function deferred<T>() {
  let resolve!: (value: T) => void
  const promise = new Promise<T>((done) => { resolve = done })
  return { promise, resolve }
}
function LocationProbe() { return <output data-testid="trash-location">{useLocation().pathname + useLocation().search}</output> }
function providers(content: React.ReactNode, path: string) {
  const cache = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: Infinity, refetchOnWindowFocus: false }, mutations: { retry: false } } })
  render(<QueryClientProvider client={cache}><MemoryRouter initialEntries={[path]}><LocationProbe />{content}</MemoryRouter></QueryClientProvider>)
  return cache
}
function renderTrash(path = '/trash') { return providers(<TrashPage />, path) }
function renderDelete(canDelete = true) {
  return providers(<Routes><Route path="/task" element={<TrashDeleteAction objectType="TASK" objectId={trashIds.task} title="Công việc hiện tại" canDelete={canDelete} />} /><Route path="/trash" element={<h1>Đã đến Thùng rác</h1>} /></Routes>, '/task')
}
function itemRow(title: string) { return within(screen.getByRole('heading', { name: title }).closest('li') as HTMLLIElement) }
beforeEach(() => {
  vi.clearAllMocks()
  currentUser = { id: trashIds.user }
  vi.mocked(trashApi.list).mockResolvedValue(page())
  vi.mocked(trashApi.delete).mockResolvedValue(trashItem())
  vi.mocked(trashApi.restore).mockResolvedValue()
  vi.mocked(trashApi.purge).mockResolvedValue()
})

describe('Trash page and server capabilities', () => {
  it('works without resolving a normal Profile and shows a useful empty state', async () => {
    renderTrash()
    expect(await screen.findByRole('heading', { name: 'Thùng rác trống' })).toBeVisible()
    expect(trashApi.list).toHaveBeenCalledWith({}, 1, expect.any(AbortSignal))
    expect(screen.getByRole('button', { name: 'Tất cả' })).toHaveAttribute('aria-pressed', 'true')
  })
  it('renders name, type, safe deleter, server deadline, remaining days and impact', async () => {
    vi.mocked(trashApi.list).mockResolvedValue(page([trashItem()]))
    renderTrash()
    const heading = await screen.findByRole('heading', { name: 'Công việc trong Thùng rác' })
    expect(heading).toBeVisible()
    expect(screen.getByText('Quản lý kiểm thử')).toBeVisible()
    expect(screen.getByText('Còn 5 ngày')).toBeVisible()
    expect(screen.getByText(/1 công việc · 1 phân công/)).toBeVisible()
    expect(document.querySelector('time[datetime="2026-10-31T10:00:00Z"]')).toBeVisible()
    expect(itemRow(trashItem().title).getByRole('button', { name: 'Xóa vĩnh viễn' })).toBeDisabled()
  })
  it('does not render a UUID or email-derived fallback as the deleter name', async () => {
    vi.mocked(trashApi.list).mockResolvedValue(page([trashItem({ deleted_by: { display_name: trashIds.user } })]))
    renderTrash()
    expect(await screen.findByText('Người dùng không còn khả dụng')).toBeVisible()
    expect(screen.queryByText(trashIds.user)).not.toBeInTheDocument()
  })
  it('supports type filters and resets pagination', async () => {
    renderTrash('/trash?page=2')
    await screen.findByText('Thùng rác trống')
    await userEvent.click(screen.getByRole('button', { name: 'Task' }))
    await waitFor(() => expect(trashApi.list).toHaveBeenLastCalledWith({ object_type: 'TASK' }, 1, expect.any(AbortSignal)))
    expect(screen.getByTestId('trash-location')).toHaveTextContent('/trash?object_type=TASK')
  })
  it('debounces server search and provides a no-results recovery action', async () => {
    renderTrash()
    await screen.findByText('Thùng rác trống')
    fireEvent.change(screen.getByLabelText('Tìm trong Thùng rác'), { target: { value: 'không tìm thấy' } })
    expect(trashApi.list).toHaveBeenCalledTimes(1)
    await waitFor(() => expect(trashApi.list).toHaveBeenLastCalledWith({ search: 'không tìm thấy' }, 1, expect.any(AbortSignal)))
    expect(await screen.findByRole('heading', { name: 'Không tìm thấy mục phù hợp' })).toBeVisible()
    await userEvent.click(screen.getByRole('button', { name: 'Bỏ bộ lọc' }))
    await waitFor(() => expect(screen.getByTestId('trash-location')).toHaveTextContent('/trash'))
    expect(screen.getByLabelText('Tìm trong Thùng rác')).toHaveValue('')
  })
  it('paginates by server count instead of following remote next links', async () => {
    vi.mocked(trashApi.list).mockResolvedValue(page([trashItem()], 21))
    renderTrash()
    await screen.findByText(trashItem().title)
    await userEvent.click(screen.getByRole('button', { name: 'Trang sau' }))
    await waitFor(() => expect(trashApi.list).toHaveBeenLastCalledWith({}, 2, expect.any(AbortSignal)))
    expect(screen.getByTestId('trash-location')).toHaveTextContent('page=2')
  })
  it('explains inherited-parent and expired-restore restrictions', async () => {
    vi.mocked(trashApi.list).mockResolvedValue(page([trashItem({ parent_deleted: true, can_restore: false, restore_blocker: 'PARENT_DELETED' }), trashItem({ id: trashIds.user, title: 'Mục hết hạn', days_remaining: 0, can_restore: false, restore_blocker: 'EXPIRED' })]))
    renderTrash()
    expect(await screen.findByText('Khôi phục: Khôi phục đối tượng cha trước khi khôi phục mục này.')).toBeVisible()
    expect(screen.getByText('Khôi phục: Đã hết thời hạn khôi phục 30 ngày.')).toBeVisible()
    expect(itemRow(trashItem().title).getByRole('button', { name: 'Khôi phục' })).toBeDisabled()
    expect(itemRow('Mục hết hạn').getByRole('button', { name: 'Khôi phục' })).toBeDisabled()
    expect(screen.getByText('Đã đến hạn')).toBeVisible()
  })
  it('keeps purge disabled when activation or historical-data rules block it', async () => {
    vi.mocked(trashApi.list).mockResolvedValue(page([trashItem({ days_remaining: 0, purge_blockers: [{ code: 'PURGE_DISABLED', message: 'Disabled' }, { code: 'PROTECTED_HISTORY', message: 'Hold' }] })]))
    renderTrash()
    expect(await screen.findByText('Xóa vĩnh viễn đang chờ phê duyệt kích hoạt.')).toBeVisible()
    expect(screen.getByText('Lịch sử nghiệm thu hoặc tiền công đang được bảo toàn.')).toBeVisible()
    expect(screen.getByRole('button', { name: 'Xóa vĩnh viễn' })).toBeDisabled()
    expect(trashApi.purge).not.toHaveBeenCalled()
  })
  it('restores only after confirmation, clears private data and focuses the heading after removal', async () => {
    vi.mocked(trashApi.list).mockResolvedValueOnce(page([trashItem()])).mockResolvedValue(page())
    const cache = renderTrash()
    cache.setQueryData(['work', trashIds.profile, 'amount'], { amount: '500000' })
    cache.setQueryData(['notifications', trashIds.user], { privateTitle: 'Old task' })
    await screen.findByText(trashItem().title)
    await userEvent.click(itemRow(trashItem().title).getByRole('button', { name: 'Khôi phục' }))
    expect(trashApi.restore).not.toHaveBeenCalled()
    await userEvent.click(screen.getByRole('button', { name: 'Xác nhận khôi phục' }))
    await screen.findByRole('heading', { name: 'Thùng rác trống' })
    expect(trashApi.restore).toHaveBeenCalledWith('TASK', trashIds.task, expect.any(AbortSignal))
    expect(cache.getQueryData(['work', trashIds.profile, 'amount'])).toBeUndefined()
    expect(cache.getQueryData(['notifications', trashIds.user])).toBeUndefined()
    await waitFor(() => expect(screen.getByRole('heading', { name: 'Thùng rác' })).toHaveFocus())
    expect(screen.queryByText(trashItem().title)).not.toBeInTheDocument()
  })
  it('requires exact Workspace name and explicit acknowledgement before purge', async () => {
    const workspace = trashItem({ id: trashIds.workspace, object_type: 'WORKSPACE', title: 'Không gian cần xác nhận', days_remaining: 0, can_restore: false, can_purge: true, purge_blockers: [] })
    vi.mocked(trashApi.list).mockResolvedValueOnce(page([workspace])).mockResolvedValue(page())
    renderTrash()
    await screen.findByText(workspace.title)
    await userEvent.click(itemRow(workspace.title).getByRole('button', { name: 'Xóa vĩnh viễn' }))
    const confirm = screen.getByRole('button', { name: 'Xác nhận xóa vĩnh viễn' })
    expect(confirm).toBeDisabled()
    await userEvent.type(screen.getByLabelText('Nhập chính xác tên để xác nhận'), 'sai tên')
    await userEvent.click(screen.getByRole('checkbox'))
    expect(confirm).toBeDisabled()
    await userEvent.clear(screen.getByLabelText('Nhập chính xác tên để xác nhận'))
    await userEvent.type(screen.getByLabelText('Nhập chính xác tên để xác nhận'), workspace.title)
    expect(confirm).toBeEnabled()
    await userEvent.click(confirm)
    await screen.findByText('Thùng rác trống')
    expect(trashApi.purge).toHaveBeenCalledWith(workspace, workspace.title, expect.any(AbortSignal))
  })
  it('returns to the first filtered page after removing the final row of a later page', async () => {
    vi.mocked(trashApi.list).mockResolvedValueOnce(page([trashItem()], 21)).mockResolvedValue(page([], 20))
    renderTrash('/trash?object_type=TASK&page=2')
    await screen.findByText(trashItem().title)
    await userEvent.click(itemRow(trashItem().title).getByRole('button', { name: 'Khôi phục' }))
    await userEvent.click(screen.getByRole('button', { name: 'Xác nhận khôi phục' }))
    await waitFor(() => expect(trashApi.list).toHaveBeenLastCalledWith({ object_type: 'TASK' }, 1, expect.any(AbortSignal)))
    expect(screen.getByTestId('trash-location')).toHaveTextContent('/trash?object_type=TASK')
    expect(screen.getByTestId('trash-location')).not.toHaveTextContent('page=2')
  })
  it('prevents rapid duplicate confirmation while pending', async () => {
    const mutation = deferred<void>()
    vi.mocked(trashApi.list).mockResolvedValue(page([trashItem()]))
    vi.mocked(trashApi.restore).mockReturnValue(mutation.promise)
    renderTrash()
    await screen.findByText(trashItem().title)
    await userEvent.click(itemRow(trashItem().title).getByRole('button', { name: 'Khôi phục' }))
    const confirm = screen.getByRole('button', { name: 'Xác nhận khôi phục' })
    fireEvent.click(confirm); fireEvent.click(confirm)
    expect(trashApi.restore).toHaveBeenCalledTimes(1)
    expect(confirm).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Hủy' })).toBeDisabled()
    await act(async () => { mutation.resolve(); await mutation.promise })
  })
  it.each([400, 403, 404, 409])('shows mutation%d safely without success or automatic replay', async (status) => {
    vi.mocked(trashApi.list).mockResolvedValue(page([trashItem()]))
    vi.mocked(trashApi.restore).mockRejectedValue(new ApiError(status, status === 409 ? 'conflict' : 'forbidden', 'Quyền hoặc trạng thái đã thay đổi.'))
    renderTrash()
    await screen.findByText(trashItem().title)
    await userEvent.click(itemRow(trashItem().title).getByRole('button', { name: 'Khôi phục' }))
    await userEvent.click(screen.getByRole('button', { name: 'Xác nhận khôi phục' }))
    expect(await screen.findByText('Quyền hoặc trạng thái đã thay đổi.')).toBeVisible()
    expect(trashApi.restore).toHaveBeenCalledTimes(1)
    expect(screen.queryByText(/^Đã khôi phục\./)).not.toBeInTheDocument()
  })
  it('requires explicit refresh after uncertain network failure', async () => {
    vi.mocked(trashApi.list).mockResolvedValue(page([trashItem()]))
    vi.mocked(trashApi.restore).mockRejectedValue(new ApiError(0, 'network', 'Network'))
    renderTrash()
    await screen.findByText(trashItem().title)
    await userEvent.click(itemRow(trashItem().title).getByRole('button', { name: 'Khôi phục' }))
    await userEvent.click(screen.getByRole('button', { name: 'Xác nhận khôi phục' }))
    await screen.findByText(/Chưa thể xác nhận kết quả\. Tải lại trạng thái/)
    expect(screen.getByRole('button', { name: 'Xác nhận khôi phục' })).toBeDisabled()
    expect(trashApi.restore).toHaveBeenCalledTimes(1)
    await userEvent.click(screen.getByRole('button', { name: 'Làm mới trạng thái' }))
    await waitFor(() => expect(trashApi.list).toHaveBeenCalledTimes(2))
  })
  it('never displays stale rows when the list query fails after privilege revocation', async () => {
    vi.mocked(trashApi.list).mockRejectedValue(new ApiError(403, 'forbidden', 'Không còn quyền quản lý.'))
    renderTrash()
    expect(await screen.findByText('Không còn quyền quản lý.')).toBeVisible()
    expect(screen.queryByRole('button', { name: 'Khôi phục' })).not.toBeInTheDocument()
    expect(trashApi.list).toHaveBeenCalledTimes(1)
  })
})

describe('Soft delete entry', () => {
  it('does not show a delete action without a current server capability', () => {
    renderDelete(false)
    expect(screen.queryByRole('button', { name: 'Xóa công việc' })).not.toBeInTheDocument()
  })
  it('keeps normal delete distinct from purge and navigates only after server acknowledgement', async () => {
    const mutation = deferred<TrashItem>()
    vi.mocked(trashApi.delete).mockReturnValue(mutation.promise)
    const cache = renderDelete()
    cache.setQueryData(['work', trashIds.profile, 'task'], { title: 'Private task' })
    await userEvent.click(screen.getByRole('button', { name: 'Xóa công việc' }))
    expect(screen.getByRole('dialog', { name: 'Chuyển vào Thùng rác' })).toBeVisible()
    const confirm = screen.getByRole('button', { name: 'Xác nhận chuyển vào Thùng rác' })
    fireEvent.click(confirm); fireEvent.click(confirm)
    expect(trashApi.delete).toHaveBeenCalledTimes(1)
    expect(screen.getByTestId('trash-location')).toHaveTextContent('/task')
    expect(confirm).toBeDisabled()
    await act(async () => { mutation.resolve(trashItem()); await mutation.promise })
    expect(await screen.findByRole('heading', { name: 'Đã đến Thùng rác' })).toBeVisible()
    expect(cache.getQueryData(['work', trashIds.profile, 'task'])).toBeUndefined()
    expect(trashApi.purge).not.toHaveBeenCalled()
  })
  it('does not claim deletion after an uncertain failure', async () => {
    vi.mocked(trashApi.delete).mockRejectedValue(new ApiError(500, 'server', 'Server'))
    renderDelete()
    await userEvent.click(screen.getByRole('button', { name: 'Xóa công việc' }))
    await userEvent.click(screen.getByRole('button', { name: 'Xác nhận chuyển vào Thùng rác' }))
    expect(await screen.findByText(/Chưa thể xác nhận kết quả\. Mở Thùng rác/)).toBeVisible()
    expect(screen.getByRole('button', { name: 'Xác nhận chuyển vào Thùng rác' })).toBeDisabled()
    expect(screen.getByTestId('trash-location')).toHaveTextContent('/task')
    expect(trashApi.delete).toHaveBeenCalledTimes(1)
  })
})
