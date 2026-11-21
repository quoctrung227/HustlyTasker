import { useEffect, useRef, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router'
import { Alert, Button } from '../../components/ui'
import { isApiError } from '../../services/api/client'
import { notificationKeys } from '../../services/api/collaboration'
import type { AppNotification } from '../../services/api/collaboration'
import { memberKeys, membersApi } from '../../services/api/members'
import type { RecipientInvitation } from '../../services/api/members'
import type { Page } from '../../services/api/types'
import './InvitationV2.css'

export const invitationStatusLabels: Record<RecipientInvitation['status'], string> = {
  PENDING: 'Đang chờ phản hồi', ACCEPTED: 'Đã chấp nhận', DECLINED: 'Đã từ chối', REVOKED: 'Đã thu hồi', EXPIRED: 'Đã hết hạn',
}
export const invitationRoleLabels = { ADMIN: 'Quản trị viên', MEMBER: 'Thành viên' }

/** Explicit decisions are independent from notification read state and active Profile. */
export function InvitationDecision({ invitation, userId, onUpdated, onNavigate }: {
  invitation: RecipientInvitation; userId: string; onUpdated?: (value: RecipientInvitation) => void; onNavigate?: () => void
}) {
  const cache = useQueryClient()
  const [pending, setPending] = useState<'accept' | 'decline' | 'refresh' | null>(null)
  const [confirmDecline, setConfirmDecline] = useState(false)
  const [failure, setFailure] = useState('')
  const [notice, setNotice] = useState('')
  const [needsRefresh, setNeedsRefresh] = useState(false)
  const request = useRef<AbortController | null>(null)
  const summary = useRef<HTMLDivElement>(null)
  useEffect(() => () => { request.current?.abort() }, [])
  useEffect(() => { if (failure) summary.current?.focus() }, [failure])

  async function store(saved: RecipientInvitation, signal: AbortSignal) {
    await cache.cancelQueries({ queryKey: memberKeys.recipientRoot(userId) })
    if (signal.aborted) return
    cache.setQueryData(memberKeys.recipient(userId, saved.id), saved)
    cache.setQueriesData<Page<RecipientInvitation>>({ queryKey: [...memberKeys.recipientRoot(userId), 'inbox'] }, (old) => old ? { ...old, results: old.results.map((row) => row.id === saved.id ? saved : row) } : old)
    cache.setQueriesData<Page<AppNotification>>({ queryKey: [...notificationKeys.user(userId), 'feed'] }, (old) => old ? { ...old, results: old.results.map((row) => row.target_type === 'PROFILE_INVITATION' && row.invitation_id === saved.id ? { ...row, invitation: saved } : row) } : old)
    onUpdated?.(saved)
    void cache.invalidateQueries({ queryKey: ['profiles'] })
    void cache.invalidateQueries({ queryKey: memberKeys.user(userId) })
    void cache.invalidateQueries({ queryKey: notificationKeys.user(userId) })
  }

  async function respond(action: 'accept' | 'decline' | 'refresh') {
    if (request.current || !userId || (action !== 'refresh' && needsRefresh) ||
        (action === 'accept' && !invitation.can_accept) || (action === 'decline' && !invitation.can_decline)) return
    const controller = new AbortController()
    request.current = controller; setPending(action); setFailure(''); setNotice('')
    try {
      const saved = action === 'refresh' ? await membersApi.recipientInvitation(invitation.id, controller.signal)
        : action === 'accept' ? await membersApi.acceptAccountInvitation(invitation.id, controller.signal)
          : await membersApi.declineAccountInvitation(invitation.id, controller.signal)
      if (controller.signal.aborted) return
      await store(saved, controller.signal)
      if (controller.signal.aborted) return
      setNeedsRefresh(false); setConfirmDecline(false)
      setNotice(action === 'refresh' ? 'Đã tải trạng thái hiện tại từ máy chủ.'
        : saved.status === 'ACCEPTED' ? 'Máy chủ đã xác nhận chấp nhận lời mời.' : 'Đã từ chối lời mời; không tạo tư cách thành viên.')
    } catch (error) {
      if (controller.signal.aborted) return
      setConfirmDecline(false)
      const uncertain = !isApiError(error) || error.status === 0 || error.status >= 500
      setNeedsRefresh(true)
      setFailure(uncertain ? 'Chưa thể xác nhận kết quả. Tải lại trạng thái lời mời trước khi thao tác tiếp; hệ thống không tự gửi lại quyết định.'
        : isApiError(error) ? error.message : 'Chưa thể xử lý lời mời.')
      if (isApiError(error) && error.kind !== 'csrf' && [403, 404].includes(error.status)) {
        await cache.cancelQueries({ queryKey: memberKeys.recipientRoot(userId) })
        if (controller.signal.aborted) return
        cache.removeQueries({ queryKey: memberKeys.recipient(userId, invitation.id), exact: true })
        cache.setQueriesData<Page<AppNotification>>({ queryKey: [...notificationKeys.user(userId), 'feed'] }, (old) => old ? { ...old, results: old.results.filter((row) => row.target_type !== 'PROFILE_INVITATION' || row.invitation_id !== invitation.id) } : old)
        void cache.invalidateQueries({ queryKey: notificationKeys.user(userId) })
      }
    } finally { if (!controller.signal.aborted) { request.current = null; setPending(null) } }
  }

  return <div className="invitation-decision" aria-busy={pending !== null || undefined}>
    <p className="read-note">{invitationStatusLabels[invitation.status]} · Vai trò {invitationRoleLabels[invitation.requested_role]}</p>
    {failure && <div ref={summary} tabIndex={-1} className="form-summary"><Alert kind="error">{failure}</Alert></div>}
    {notice && <Alert kind="success">{notice}</Alert>}
    {confirmDecline ? <Alert title="Xác nhận từ chối"><p>Bạn muốn từ chối lời mời của {invitation.profile_name}? Thao tác này không tạo tư cách thành viên.</p>
      <div className="work-actions"><Button variant="danger" busy={pending === 'decline'} disabled={pending !== null} onClick={() => void respond('decline')}>Xác nhận từ chối</Button><Button variant="secondary" disabled={pending !== null} onClick={() => setConfirmDecline(false)}>Quay lại</Button></div>
    </Alert> : <div className="work-actions">
      {invitation.can_accept && <Button busy={pending === 'accept'} disabled={pending !== null || needsRefresh} onClick={() => void respond('accept')}>Chấp nhận lời mời</Button>}
      {invitation.can_decline && <Button variant="secondary" disabled={pending !== null || needsRefresh} onClick={() => setConfirmDecline(true)}>Từ chối lời mời</Button>}
      {needsRefresh && <Button variant="secondary" busy={pending === 'refresh'} disabled={pending !== null} onClick={() => void respond('refresh')}>Làm mới trạng thái lời mời</Button>}
      {invitation.status === 'ACCEPTED' && invitation.can_open_profile && <Link className="text-link" to={`/profiles/${invitation.profile_id}`} onClick={onNavigate}>Đến tổ chức</Link>}
    </div>}
    <p className="field__hint">Đọc thông báo không đồng nghĩa chấp nhận lời mời. Quyền truy cập được kiểm tra lại tại máy chủ.</p>
  </div>
}
