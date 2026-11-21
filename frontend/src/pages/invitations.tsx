import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link, useParams } from 'react-router'
import { PageHeader, dateLabel } from '../components/page'
import { Card, EmptyState, ErrorState, PageSkeleton, Pagination } from '../components/ui'
import { useAuth } from '../features/auth/AuthProvider'
import { InvitationDecision, invitationRoleLabels } from '../features/members/InvitationDecision'
import { memberKeys, membersApi } from '../services/api/members'
import type { RecipientInvitation } from '../services/api/members'

function InvitationCard({ invitation, userId }: { invitation: RecipientInvitation; userId: string }) {
  return <Card className="collaboration-item"><article aria-label={`Lời mời từ ${invitation.profile_name}`}>
    <h2 className="preserve-text">{invitation.profile_name}</h2>
    <p className="preserve-text">Người mời: {invitation.inviter_display_label} · Vai trò: {invitationRoleLabels[invitation.requested_role]}</p>
    <p className="read-note">Hạn phản hồi: {dateLabel(invitation.expires_at)}</p>
    <InvitationDecision key={`${userId}:${invitation.id}`} invitation={invitation} userId={userId} />
    <Link className="text-link" to={`/invitations/${invitation.id}`}>Chi tiết lời mời</Link>
  </article></Card>
}

export function InvitationsPage() {
  const { user } = useAuth()
  return <ScopedInvitations key={user?.id || ''} userId={user?.id || ''} />
}
function ScopedInvitations({ userId }: { userId: string }) {
  const [page, setPage] = useState(1)
  const query = useQuery({ queryKey: memberKeys.inbox(userId, page), queryFn: ({ signal }) => membersApi.recipientInvitations(page, signal), enabled: !!userId, staleTime: 0, retry: false })
  return <>
    <PageHeader eyebrow="DÀNH CHO TÀI KHOẢN CỦA BẠN" title="Lời mời tổ chức" description="Chấp nhận hoặc từ chối lời mời ngay trên Web. Không cần nhập mã; email chỉ dùng để thông báo." back={{ to: '/profiles', label: 'Tổ chức' }} />
    {query.isPending || query.isFetching ? <PageSkeleton label="Đang tải lời mời của bạn…" /> : query.isError ? <ErrorState error={query.error} onRetry={() => void query.refetch()} />
      : !query.data.results.length ? <EmptyState title="Chưa có lời mời tổ chức" description="Lời mời dành đúng tài khoản này sẽ xuất hiện ở đây và trong Thông báo." /> : <>
        <ul className="collaboration-list" aria-label="Lời mời dành cho bạn">{query.data.results.map((invitation) => <li key={invitation.id}><InvitationCard invitation={invitation} userId={userId} /></li>)}</ul>
        <Pagination page={page} count={query.data.count} onPageChange={setPage} label="Phân trang lời mời của bạn" />
      </>}
  </>
}

export function InvitationDetailPage() {
  const { invitationId = '' } = useParams()
  const { user } = useAuth()
  return <ScopedInvitationDetail key={`${user?.id}:${invitationId}`} userId={user?.id || ''} invitationId={invitationId} />
}
function ScopedInvitationDetail({ userId, invitationId }: { userId: string; invitationId: string }) {
  const query = useQuery({ queryKey: memberKeys.recipient(userId, invitationId), queryFn: ({ signal }) => membersApi.recipientInvitation(invitationId, signal), enabled: !!userId, staleTime: 0, retry: false })
  return <>
    <PageHeader eyebrow="PHẢN HỒI CỦA BẠN" title="Chi tiết lời mời" description="Chỉ tài khoản được mời mới xem và phản hồi được lời mời này." back={{ to: '/invitations', label: 'Lời mời tổ chức' }} />
    {query.isPending || query.isFetching ? <PageSkeleton label="Đang tải lời mời…" /> : query.isError ? <ErrorState error={query.error} onRetry={() => void query.refetch()} /> : <InvitationCard invitation={query.data} userId={userId} />}
  </>
}
