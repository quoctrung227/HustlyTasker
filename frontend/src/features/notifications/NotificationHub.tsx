import { useEffect, useRef, useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { BellIcon, ArrowClockwiseIcon } from '@phosphor-icons/react'
import { Link } from 'react-router'
import { Alert, Button, Card, Dialog, EmptyState, ErrorState, PageSkeleton, Pagination } from '../../components/ui'
import { isApiError } from '../../services/api/client'
import { notificationApi, notificationKeys, notificationTaskPath } from '../../services/api/collaboration'
import type { AppNotification } from '../../services/api/collaboration'
import type { Page } from '../../services/api/types'

export function useUnreadCount(userId: string) {
  return useQuery({ queryKey: notificationKeys.unreadCount(userId), queryFn: ({ signal }) => notificationApi.unreadCount(signal), enabled: !!userId, staleTime: 0 })
}

function timeLabel(value: string) { return new Intl.DateTimeFormat('vi-VN', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value)) }

export function NotificationFeed(props: { userId: string; preview?: boolean; onNavigate?: () => void }) {
  return <ScopedNotificationFeed key={props.userId} {...props} />
}

function ScopedNotificationFeed({ userId, preview = false, onNavigate }: { userId: string; preview?: boolean; onNavigate?: () => void }) {
  const cache = useQueryClient()
  const [filter, setFilter] = useState<'all' | 'unread' | 'read'>('all')
  const [page, setPage] = useState(1)
  const [busyId, setBusyId] = useState('')
  const [failure, setFailure] = useState<unknown>(null)
  const [notice, setNotice] = useState('')
  const request = useRef<AbortController | null>(null)
  const isRead = filter === 'all' ? undefined : filter === 'read'
  const query = useQuery({ queryKey: notificationKeys.feed(userId, isRead, page), queryFn: ({ signal }) => notificationApi.feed(isRead, page, signal), enabled: !!userId, staleTime: 0 })
  useEffect(() => () => { request.current?.abort() }, [])

  async function markRead(item: AppNotification) {
    if (request.current || item.is_read) return
    const controller = new AbortController()
    request.current = controller; setBusyId(item.id); setFailure(null); setNotice('')
    try {
      const saved = await notificationApi.markRead(item.id, controller.signal)
      if (controller.signal.aborted) return
      await cache.cancelQueries({ queryKey: [...notificationKeys.user(userId), 'feed'] })
      if (controller.signal.aborted) return
      cache.setQueriesData<Page<AppNotification>>({ queryKey: [...notificationKeys.user(userId), 'feed'] }, (old) => old ? { ...old, results: old.results.map((row) => row.id === saved.id ? saved : row) } : old)
      setNotice('Đã đánh dấu thông báo là đã đọc.')
      void cache.invalidateQueries({ queryKey: notificationKeys.user(userId) })
    } catch (error) {
      if (controller.signal.aborted) return
      setFailure(error)
      if (isApiError(error) && [403, 404].includes(error.status)) {
        await cache.cancelQueries({ queryKey: [...notificationKeys.user(userId), 'feed'] })
        if (controller.signal.aborted) return
        // A denied target is no longer safe to display from cached pages.
        cache.setQueriesData<Page<AppNotification>>({ queryKey: [...notificationKeys.user(userId), 'feed'] }, (old) => old ? { ...old, results: old.results.filter((row) => row.profile_id !== item.profile_id || row.workspace_id !== item.workspace_id) } : old)
        void cache.invalidateQueries({ queryKey: notificationKeys.user(userId) })
      }
    } finally { if (!controller.signal.aborted) { request.current = null; setBusyId('') } }
  }

  const rows = preview ? query.data?.results.slice(0, 5) : query.data?.results
  return <section className="notification-feed" aria-label={preview ? 'Thông báo gần đây' : 'Danh sách thông báo'}>
    {!preview && <div className="list-toolbar"><label className="page-search">Trạng thái thông báo<select className="input" aria-label="Trạng thái thông báo" value={filter} onChange={(event) => { setFilter(event.target.value as typeof filter); setPage(1); setFailure(null); setNotice('') }}><option value="all">Tất cả</option><option value="unread">Chưa đọc</option><option value="read">Đã đọc</option></select></label><Button variant="secondary" icon={<ArrowClockwiseIcon aria-hidden="true" />} disabled={query.isFetching} onClick={() => void cache.invalidateQueries({ queryKey: notificationKeys.user(userId) })}>Làm mới thông báo</Button></div>}
    {Boolean(failure) && <Alert kind="error">{isApiError(failure) ? failure.message : 'Chưa thể đánh dấu đã đọc. Vui lòng thử lại.'}</Alert>}
    {notice && <Alert kind="success">{notice}</Alert>}
    {query.isError ? <ErrorState error={query.error} onRetry={() => void query.refetch()} /> : query.isPending || query.isFetching ? <PageSkeleton label="Đang tải thông báo…" /> : !rows?.length ? <EmptyState title="Chưa có thông báo" description="Các cập nhật bạn được phép xem sẽ xuất hiện tại đây." /> : <>
      <ul className="notification-list">{rows.map((item) => <li key={item.id}><Card className={`notification-item${item.is_read ? '' : ' notification-item--unread'}`}><article aria-label={item.title}>
        <div className="collaboration-meta"><span className="collaboration-status">{item.is_read ? 'Đã đọc' : 'Chưa đọc'}</span><time dateTime={item.created_at}>{timeLabel(item.created_at)}</time></div>
        <h3>{item.title}</h3><p className="notification-message">{item.message}</p>
        <div className="work-actions"><Link className="text-link" to={notificationTaskPath(item)} onClick={onNavigate}>Mở công việc</Link>{!item.is_read && <Button variant="secondary" busy={busyId === item.id} disabled={!!busyId} onClick={() => void markRead(item)}>Đánh dấu đã đọc</Button>}</div>
      </article></Card></li>)}</ul>
      {preview ? <p className="field__hint">Hiển thị tối đa 5 thông báo trên trang đầu.</p> : <Pagination page={page} count={query.data.count} onPageChange={setPage} disabled={!!busyId} />}
    </>}
  </section>
}

export function NotificationMenu({ userId }: { userId: string }) {
  const [open, setOpen] = useState(false)
  const unread = useUnreadCount(userId)
  return <>
    <Button variant="ghost" className="notification-trigger" aria-label="Mở thông báo" onClick={() => setOpen(true)}><BellIcon aria-hidden="true" />
      {unread.isSuccess && !unread.isFetching && unread.data > 0 && <span className="notification-count" aria-hidden="true">{unread.data > 99 ? '99+' : unread.data}</span>}
      <span className="sr-only" role="status" aria-live="polite" aria-atomic="true">{unread.isError ? 'Chưa tải được số thông báo' : unread.isSuccess && !unread.isFetching ? `${unread.data} thông báo chưa đọc` : 'Đang kiểm tra thông báo'}</span>
    </Button>
    {open && <Dialog open title="Thông báo của bạn" onClose={() => setOpen(false)} className="notification-dialog"><NotificationFeed userId={userId} preview onNavigate={() => setOpen(false)} /><Link className="button button--secondary" to="/notifications" onClick={() => setOpen(false)}>Xem tất cả thông báo</Link></Dialog>}
  </>
}
