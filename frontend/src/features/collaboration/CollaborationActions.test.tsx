/** Mock UI tests; real isolated PostgreSQL/browser flows are separate evidence. */
import { act, fireEvent, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterAll, beforeAll, beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from '../../services/api/client'
import { collaborationApi } from '../../services/api/collaboration'
import type { Deliverable } from '../../services/api/collaboration'
import { ReviewDeliverable, SubmitDeliverable } from './CollaborationActions'

const time = '2026-10-26T00:00:00Z'
const item: Deliverable = { id: 'deliverable', task_id: 'task', revision: 1, file_url: 'Văn bản sản phẩm', status: 'SUBMITTED', uploaded_by_profile_membership_id: null, review: null, can_approve: true, can_request_changes: true, created_at: time, updated_at: time }
const context = () => ({ profileId: 'profile', workspaceId: 'workspace', taskId: 'task', active: true, onSaved: vi.fn(), onFailure: vi.fn() })
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
  vi.spyOn(collaborationApi, 'submitDeliverable').mockResolvedValue(item)
  vi.spyOn(collaborationApi, 'approveDeliverable').mockResolvedValue({ ...item, status: 'APPROVED', can_approve: false, can_request_changes: false })
  vi.spyOn(collaborationApi, 'requestDeliverableChanges').mockResolvedValue({ ...item, status: 'REJECTED', can_approve: false, can_request_changes: false })
})
async function openSubmit(props = context()) {
  const view = render(<SubmitDeliverable {...props} canSubmit />)
  const user = userEvent.setup()
  await user.click(screen.getByRole('button', { name: 'Nộp sản phẩm' }))
  const dialog = screen.getByRole('dialog', { name: 'Nộp sản phẩm' })
  return { ...view, props, user, dialog, input: within(dialog).getByLabelText('Đường dẫn hoặc nội dung sản phẩm') }
}

describe('Submit Deliverable controls', () => {
  it.each([{ active: true, canSubmit: false }, { active: false, canSubmit: true }])('fails closed for an unavailable capability or archived context (%#)', (state) => {
    render(<SubmitDeliverable {...context()} {...state} />)
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })
  it('submits trimmed text without inventing a URL/upload requirement and waits for the server', async () => {
    const { props, user, dialog, input } = await openSubmit()
    fireEvent.change(input, { target: { value: '  Sản phẩm dưới dạng văn bản  ' } })
    await user.click(within(dialog).getByRole('button', { name: 'Nộp sản phẩm' }))
    expect(collaborationApi.submitDeliverable).toHaveBeenCalledWith('profile', 'workspace', 'task', { file_url: 'Sản phẩm dưới dạng văn bản' }, expect.any(AbortSignal))
    expect(props.onSaved).toHaveBeenCalledWith(item, 'submit')
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })
  it.each(['', 'a'.repeat(501), 'Có\0NUL', '\uD800'])('rejects invalid input and focuses a linked error summary (%#)', async (value) => {
    const { user, dialog, input } = await openSubmit()
    fireEvent.change(input, { target: { value } })
    await user.click(within(dialog).getByRole('button', { name: 'Nộp sản phẩm' }))
    expect(collaborationApi.submitDeliverable).not.toHaveBeenCalled()
    expect(input).toHaveAttribute('aria-invalid', 'true')
    const summary = within(dialog).getByRole('alert')
    expect(summary.parentElement).toHaveFocus()
    await user.click(within(summary).getByRole('link'))
    expect(input).toHaveFocus()
  })
  it.each([400, 403, 404, 409])('keeps the draft and exposes safe failure without retry/success (%s)', async (status) => {
    const error = new ApiError(status, status === 403 ? 'forbidden' : 'validation', 'Không thể lưu thay đổi.', { file_url: 'Kiểm tra sản phẩm.' })
    vi.mocked(collaborationApi.submitDeliverable).mockRejectedValue(error)
    const { props, user, dialog, input } = await openSubmit()
    fireEvent.change(input, { target: { value: 'Bản nháp cần giữ' } })
    await user.click(within(dialog).getByRole('button', { name: 'Nộp sản phẩm' }))
    expect(input).toHaveValue('Bản nháp cần giữ')
    expect(within(dialog).getByRole('alert')).toHaveTextContent('Không thể lưu thay đổi.')
    expect(props.onFailure).toHaveBeenCalledWith(error)
    expect(props.onSaved).not.toHaveBeenCalled()
    expect(collaborationApi.submitDeliverable).toHaveBeenCalledTimes(1)
  })
  it('guards duplicate submits, disables cancellation while pending, and aborts on unmount', async () => {
    let resolve: (value: Deliverable) => void = () => { throw new Error('Missing resolver') }
    vi.mocked(collaborationApi.submitDeliverable).mockReturnValue(new Promise<Deliverable>((done) => { resolve = done }))
    const view = await openSubmit()
    fireEvent.change(view.input, { target: { value: 'Đang gửi' } })
    fireEvent.submit(view.input.closest('form') as HTMLFormElement)
    fireEvent.submit(view.input.closest('form') as HTMLFormElement)
    expect(collaborationApi.submitDeliverable).toHaveBeenCalledTimes(1)
    expect(within(view.dialog).getByRole('button', { name: 'Hủy' })).toBeDisabled()
    expect(view.props.onSaved).not.toHaveBeenCalled()
    const signal = vi.mocked(collaborationApi.submitDeliverable).mock.calls[0]?.[4] as AbortSignal
    view.unmount()
    expect(signal.aborted).toBe(true)
    await act(async () => { resolve(item) })
    expect(view.props.onSaved).not.toHaveBeenCalled()
  })
  it('stops a stale open form when refreshed capability is false and keeps its draft', async () => {
    const view = await openSubmit()
    fireEvent.change(view.input, { target: { value: 'Bản nháp' } })
    view.rerender(<SubmitDeliverable {...view.props} canSubmit={false} />)
    expect(within(view.dialog).getByRole('button', { name: 'Nộp sản phẩm' })).toBeDisabled()
    expect(view.input).toHaveValue('Bản nháp')
    fireEvent.submit(view.input.closest('form') as HTMLFormElement)
    expect(collaborationApi.submitDeliverable).not.toHaveBeenCalled()
  })
})

describe('Review decision controls', () => {
  it('uses server hints independently and does not guess reviewer identity or latest revision', () => {
    const props = context()
    const view = render(<ReviewDeliverable {...props} item={{ ...item, can_approve: false }} />)
    expect(screen.queryByRole('button', { name: 'Phê duyệt sản phẩm' })).not.toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Yêu cầu chỉnh sửa' })).toBeVisible()
    view.rerender(<ReviewDeliverable {...props} item={{ ...item, can_approve: false, can_request_changes: false }} />)
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })
  it('confirms approval with optional feedback and never updates Task state locally', async () => {
    const props = context()
    render(<ReviewDeliverable {...props} item={item} />)
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: 'Phê duyệt sản phẩm' }))
    const dialog = screen.getByRole('dialog', { name: 'Phê duyệt sản phẩm' })
    expect(collaborationApi.approveDeliverable).not.toHaveBeenCalled()
    await user.click(within(dialog).getByRole('button', { name: 'Xác nhận phê duyệt' }))
    expect(collaborationApi.approveDeliverable).toHaveBeenCalledWith('profile', 'workspace', 'task', 'deliverable', {}, expect.any(AbortSignal))
    expect(props.onSaved).toHaveBeenCalledWith(expect.objectContaining({ status: 'APPROVED' }), 'approve')
  })
  it('requires feedback for request changes and submits the real decision endpoint', async () => {
    const props = context()
    render(<ReviewDeliverable {...props} item={item} />)
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: 'Yêu cầu chỉnh sửa' }))
    const dialog = screen.getByRole('dialog', { name: 'Yêu cầu chỉnh sửa' })
    await user.click(within(dialog).getByRole('button', { name: 'Gửi yêu cầu chỉnh sửa' }))
    expect(collaborationApi.requestDeliverableChanges).not.toHaveBeenCalled()
    fireEvent.change(within(dialog).getByLabelText('Nội dung cần chỉnh sửa'), { target: { value: '  Sửa phần mở đầu.  ' } })
    await user.click(within(dialog).getByRole('button', { name: 'Gửi yêu cầu chỉnh sửa' }))
    expect(collaborationApi.requestDeliverableChanges).toHaveBeenCalledWith('profile', 'workspace', 'task', 'deliverable', { comment: 'Sửa phần mở đầu.' }, expect.any(AbortSignal))
    expect(props.onSaved).toHaveBeenCalledWith(expect.objectContaining({ status: 'REJECTED' }), 'changes')
  })
  it.each([403, 404, 409])('preserves Review failure and feedback when stale permission/state is rejected (%s)', async (status) => {
    vi.mocked(collaborationApi.approveDeliverable).mockRejectedValue(new ApiError(status, 'forbidden', 'Quyết định chưa được lưu.'))
    const props = context()
    render(<ReviewDeliverable {...props} item={item} />)
    const user = userEvent.setup()
    await user.click(screen.getByRole('button', { name: 'Phê duyệt sản phẩm' }))
    const dialog = screen.getByRole('dialog')
    fireEvent.change(within(dialog).getByLabelText(/Nhận xét/), { target: { value: 'Nhận xét còn giữ' } })
    await user.click(within(dialog).getByRole('button', { name: 'Xác nhận phê duyệt' }))
    await waitFor(() => expect(within(dialog).getByRole('alert')).toHaveTextContent('Quyết định chưa được lưu.'))
    expect(within(dialog).getByLabelText(/Nhận xét/)).toHaveValue('Nhận xét còn giữ')
    expect(props.onSaved).not.toHaveBeenCalled()
    expect(collaborationApi.approveDeliverable).toHaveBeenCalledTimes(1)
  })
  it('keeps archived contexts read-only even if old hints were true', () => {
    render(<ReviewDeliverable {...context()} active={false} item={item} />)
    expect(screen.queryByRole('button')).not.toBeInTheDocument()
  })
})
