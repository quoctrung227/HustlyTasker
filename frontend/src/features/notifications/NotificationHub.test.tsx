import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { act, render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from '../../services/api/client'
import { notificationApi, notificationKeys, notificationTaskPath } from '../../services/api/collaboration'
import type { AppNotification } from '../../services/api/collaboration'
import { NotificationFeed, NotificationMenu } from './NotificationHub'

const id = '00000000-0000-4000-8000-000000000501'
const item: AppNotification = { id, event_type: 'TASK_COMMENTED', profile_id: '00000000-0000-4000-8000-000000000502', workspace_id: '00000000-0000-4000-8000-000000000503', task_id: '00000000-0000-4000-8000-000000000504', title: 'Task comment', message: 'A new comment was added.', target_url: 'https://untrusted.example/ignored', is_read: false, created_at: '2026-10-26T00:00:00Z', updated_at: '2026-10-26T00:00:00Z' }
const page = (rows: AppNotification[], count = rows.length) => ({ results: rows, count, next: null, previous: null })
function setup(component = <NotificationFeed userId="user-a" />) {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0, refetchOnWindowFocus: false }, mutations: { retry: false } } })
  const wrap = (content: React.ReactNode) => <QueryClientProvider client={client}><MemoryRouter>{content}</MemoryRouter></QueryClientProvider>
  const view = render(wrap(component))
  return { ...view, client, rerenderFeed: (content: React.ReactNode) => view.rerender(wrap(content)) }
}
beforeEach(() => {
  HTMLDialogElement.prototype.showModal = function () { this.setAttribute('open', '') }
  HTMLDialogElement.prototype.close = function () { this.removeAttribute('open') }
  vi.spyOn(notificationApi, 'feed').mockResolvedValue(page([item]))
  vi.spyOn(notificationApi, 'unreadCount').mockResolvedValue(1)
  vi.spyOn(notificationApi, 'markRead').mockResolvedValue({ ...item, is_read: true })
})

describe('Personal notification UI', () => {
  it('renders real metadata and a validated internal route, ignoring server target_url', async () => {
    setup()
    expect(await screen.findByRole('article', { name: item.title })).toHaveTextContent(item.message)
    expect(screen.getByRole('link', { name: 'Mở công việc' })).toHaveAttribute('href', notificationTaskPath(item))
    expect(notificationApi.markRead).not.toHaveBeenCalled()
  })
  it('waits for server confirmation and blocks duplicate mark-read requests', async () => {
    let resolve!: (value: AppNotification) => void
    vi.mocked(notificationApi.markRead).mockReturnValue(new Promise((done) => { resolve = done }))
    vi.mocked(notificationApi.feed).mockResolvedValueOnce(page([item])).mockResolvedValue(page([{ ...item, is_read: true }]))
    setup()
    const user = userEvent.setup(), button = await screen.findByRole('button', { name: 'Đánh dấu đã đọc' })
    await user.click(button); await user.click(button)
    expect(button).toBeDisabled()
    expect(notificationApi.markRead).toHaveBeenCalledTimes(1)
    expect(screen.queryByText('Đã đánh dấu thông báo là đã đọc.')).not.toBeInTheDocument()
    await act(async () => { resolve({ ...item, is_read: true }) })
    expect(await screen.findByText('Đã đánh dấu thông báo là đã đọc.')).toBeVisible()
    await waitFor(() => expect(screen.queryByRole('button', { name: 'Đánh dấu đã đọc' })).not.toBeInTheDocument())
  })
  it('filters read/unread and resets pagination through server query arguments', async () => {
    setup()
    await screen.findByRole('article')
    await userEvent.setup().selectOptions(screen.getByLabelText('Trạng thái thông báo'), 'unread')
    await waitFor(() => expect(notificationApi.feed).toHaveBeenLastCalledWith(false, 1, expect.any(AbortSignal)))
    await userEvent.setup().selectOptions(screen.getByLabelText('Trạng thái thông báo'), 'read')
    await waitFor(() => expect(notificationApi.feed).toHaveBeenLastCalledWith(true, 1, expect.any(AbortSignal)))
  })
  it('requests another page without following arbitrary response next links', async () => {
    vi.mocked(notificationApi.feed).mockResolvedValue(page([item], 21))
    setup()
    await userEvent.setup().click(await screen.findByRole('button', { name: 'Trang sau' }))
    await waitFor(() => expect(notificationApi.feed).toHaveBeenLastCalledWith(undefined, 2, expect.any(AbortSignal)))
  })
  it('does not offer another mutation for a notification already read', async () => {
    vi.mocked(notificationApi.feed).mockResolvedValue(page([{ ...item, is_read: true }]))
    setup()
    await screen.findByRole('article')
    expect(screen.queryByRole('button', { name: 'Đánh dấu đã đọc' })).not.toBeInTheDocument()
  })
  it('shows empty and failed-feed states without stale private body', async () => {
    vi.mocked(notificationApi.feed).mockResolvedValue(page([]))
    const { client } = setup()
    expect(await screen.findByRole('heading', { name: 'Chưa có thông báo' })).toBeVisible()
    vi.mocked(notificationApi.feed).mockRejectedValue(new ApiError(403, 'forbidden', 'Quyền đã thay đổi.'))
    await act(async () => { await client.invalidateQueries({ queryKey: notificationKeys.user('user-a') }) })
    expect(await screen.findByRole('alert')).toHaveTextContent('Quyền đã thay đổi.')
    expect(screen.queryByRole('article')).not.toBeInTheDocument()
  })
  it('redacts denied Workspace notifications and refreshes once instead of looping', async () => {
    vi.mocked(notificationApi.markRead).mockRejectedValue(new ApiError(404, 'not-found', 'Thông báo không còn khả dụng.'))
    vi.mocked(notificationApi.feed).mockResolvedValueOnce(page([item])).mockResolvedValue(page([]))
    setup()
    await userEvent.setup().click(await screen.findByRole('button', { name: 'Đánh dấu đã đọc' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Thông báo không còn khả dụng.')
    await waitFor(() => expect(screen.queryByRole('article')).not.toBeInTheDocument())
    expect(notificationApi.markRead).toHaveBeenCalledTimes(1)
    expect(notificationApi.feed).toHaveBeenCalledTimes(2)
  })
  it('does not report success or retry automatically after a failed mark-read', async () => {
    vi.mocked(notificationApi.markRead).mockRejectedValue(new ApiError(409, 'conflict', 'Dữ liệu đã thay đổi.'))
    setup()
    await userEvent.setup().click(await screen.findByRole('button', { name: 'Đánh dấu đã đọc' }))
    expect(await screen.findByRole('alert')).toHaveTextContent('Dữ liệu đã thay đổi.')
    expect(screen.queryByText('Đã đánh dấu thông báo là đã đọc.')).not.toBeInTheDocument()
    expect(notificationApi.markRead).toHaveBeenCalledTimes(1)
  })
  it('abort guards prevent late mutation callbacks after unmount', async () => {
    let resolve!: (value: AppNotification) => void
    vi.mocked(notificationApi.markRead).mockReturnValue(new Promise((done) => { resolve = done }))
    const { client, unmount } = setup()
    const invalidation = vi.spyOn(client, 'invalidateQueries')
    await userEvent.setup().click(await screen.findByRole('button', { name: 'Đánh dấu đã đọc' }))
    const signal = vi.mocked(notificationApi.markRead).mock.calls[0]?.[1]
    unmount()
    expect(signal?.aborted).toBe(true)
    await act(async () => { resolve({ ...item, is_read: true }) })
    expect(invalidation).not.toHaveBeenCalled()
  })
  it('preview is bounded and has no mutation merely from opening the dialog', async () => {
    setup(<NotificationMenu userId="user-a" />)
    expect(await screen.findByText('1 thông báo chưa đọc')).toHaveAttribute('aria-atomic', 'true')
    expect(notificationApi.feed).not.toHaveBeenCalled()
    await userEvent.setup().click(screen.getByRole('button', { name: 'Mở thông báo' }))
    const dialog = screen.getByRole('dialog', { name: 'Thông báo của bạn' })
    expect(await within(dialog).findByRole('article')).toBeVisible()
    expect(notificationApi.markRead).not.toHaveBeenCalled()
    expect(within(dialog).getByRole('link', { name: 'Xem tất cả thông báo' })).toHaveAttribute('href', '/notifications')
  })
  it('hides a stale unread badge when count refresh fails', async () => {
    const { client } = setup(<NotificationMenu userId="user-a" />)
    await screen.findByText('1 thông báo chưa đọc')
    vi.mocked(notificationApi.unreadCount).mockRejectedValue(new ApiError(403, 'forbidden', 'Phiên không còn khả dụng.'))
    await act(async () => { await client.invalidateQueries({ queryKey: notificationKeys.user('user-a') }) })
    await waitFor(() => expect(screen.queryByText('1 thông báo chưa đọc')).not.toBeInTheDocument())
  })
  it('separates User cache and ignores a late response from the previous account', async () => {
    let resolve!: (value: ReturnType<typeof page>) => void
    vi.mocked(notificationApi.feed).mockReturnValueOnce(new Promise((done) => { resolve = done }))
      .mockResolvedValue(page([{ ...item, message: 'Nội dung User B' }]))
    const { rerenderFeed } = setup()
    await waitFor(() => expect(notificationApi.feed).toHaveBeenCalledTimes(1))
    rerenderFeed(<NotificationFeed userId="user-b" />)
    expect(await screen.findByText('Nội dung User B')).toBeVisible()
    await act(async () => { resolve(page([{ ...item, message: 'Nội dung User A' }])) })
    expect(screen.queryByText('Nội dung User A')).not.toBeInTheDocument()
  })
})
