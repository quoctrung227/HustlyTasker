import { useCallback, useEffect, useId, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Alert, Button, Card, Dialog, EmptyState, ErrorState, FormField, Input, PageSkeleton, Pagination } from '../../components/ui'
import { PageHeader, dateLabel } from '../../components/page'
import { isApiError } from '../../services/api/client'
import { memberKeys, membersApi } from '../../services/api/members'
import type { InvitationRole, MemberCapabilities, ProfileInvitation, ProfileRole } from '../../services/api/members'
import { queryKeys, tenantApi } from '../../services/api/queries'

const roleLabels: Record<ProfileRole, string> = { OWNER: 'Chủ sở hữu', ADMIN: 'Quản trị viên', MEMBER: 'Thành viên' }
const invitationLabels: Record<ProfileInvitation['status'], string> = {
  PENDING: 'Đang chờ phản hồi', ACCEPTED: 'Đã chấp nhận', DECLINED: 'Đã từ chối', REVOKED: 'Đã hủy', EXPIRED: 'Đã hết hạn',
}
const deliveryLabels: Record<ProfileInvitation['delivery_status'], string> = {
  QUEUED: 'Đang chờ xử lý email', SENT: 'Hệ thống email đã tiếp nhận', FAILED: 'Gửi email chưa thành công',
}
const lostScope = (error: unknown) => isApiError(error) && error.kind !== 'csrf' && [401, 403, 404].includes(error.status)
const uncertain = (error: unknown) => !isApiError(error) || error.status === 0 || error.status >= 500
const uncertainMessage = 'Chưa thể xác nhận kết quả. Lời mời có thể đã được lưu. Đóng biểu mẫu và kiểm tra danh sách trước khi thử lại.'

type MutationProps = {
  profileId: string
  onChanged: () => void
  onDenied: (error: unknown) => void
  onNotice: (message: string) => void
}
type Failure = { message: string; fields: Partial<Record<'recipient_email' | 'requested_role', string>> }

function InviteForm({ profileId, roles, onChanged, onDenied, onNotice, onClose, onPending }: MutationProps & {
  roles: InvitationRole[]; onClose: () => void; onPending: (pending: boolean) => void
}) {
  const id = useId()
  const [email, setEmail] = useState('')
  const [role, setRole] = useState<InvitationRole | ''>(roles.includes('MEMBER') ? 'MEMBER' : '')
  const [pending, setPending] = useState(false)
  const [failure, setFailure] = useState<Failure | null>(null)
  const request = useRef<AbortController | null>(null)
  const summary = useRef<HTMLDivElement>(null)
  const ids = { recipient_email: `${id}-recipient`, requested_role: `${id}-role` }
  useEffect(() => () => { request.current?.abort() }, [])
  useEffect(() => { if (failure) summary.current?.focus() }, [failure])
  useEffect(() => {
    if (role && !roles.includes(role)) {
      request.current?.abort(); request.current = null
      setPending(false); onPending(false); setRole('')
      setFailure({ message: 'Vai trò được phép đã thay đổi. Kiểm tra danh sách lời mời trước khi gửi lại.', fields: { requested_role: 'Chọn vai trò hiện được phép.' } })
    }
  }, [onPending, role, roles])

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (request.current) return
    const fields: Failure['fields'] = {}
    const normalized = email.trim()
    if (!normalized || normalized.length > 254 || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(normalized) || normalized.includes('\u0000')) {
      fields.recipient_email = 'Nhập địa chỉ email hợp lệ (tối đa 254 ký tự).'
    }
    if (!role || !roles.includes(role)) fields.requested_role = 'Chọn vai trò hiện được phép.'
    if (Object.keys(fields).length) { setFailure({ message: 'Vui lòng kiểm tra thông tin lời mời.', fields }); return }
    if (!role) return
    const controller = new AbortController()
    request.current = controller
    setPending(true); onPending(true); setFailure(null)
    let saved = false
    try {
      await membersApi.createInvitation(profileId, { recipient_email: normalized, requested_role: role }, controller.signal)
      saved = !controller.signal.aborted
    } catch (error) {
      if (!controller.signal.aborted) {
        const api = isApiError(error) ? error : null
        const fieldErrors: Failure['fields'] = {}
        for (const name of ['recipient_email', 'requested_role'] as const) if (api?.fieldErrors[name]) fieldErrors[name] = api.fieldErrors[name]
        setFailure({ message: uncertain(error) ? uncertainMessage : api?.message || 'Chưa thể tạo lời mời. Vui lòng thử lại.', fields: fieldErrors })
        if (lostScope(error)) onDenied(error)
        else if (uncertain(error) || api?.status === 409) onChanged()
      }
    } finally {
      if (!controller.signal.aborted) { request.current = null; setPending(false); onPending(false) }
    }
    if (saved) {
      onNotice('Đã tạo lời mời. Hãy xem trạng thái email trong danh sách; lời mời chưa đồng nghĩa thành viên đã tham gia.')
      onChanged(); onClose()
    }
  }

  return <form className="work-form" aria-label="Mời thành viên" noValidate onSubmit={(event) => void submit(event)} aria-busy={pending || undefined}>
    <p>Người nhận phải đăng nhập đúng tài khoản và chủ động chấp nhận lời mời. Quyền Workspace được quản lý riêng.</p>
    {failure && <div ref={summary} className="form-summary" tabIndex={-1}><Alert kind="error" title="Chưa thể tạo lời mời"><p>{failure.message}</p>
      {Object.keys(failure.fields).length > 0 && <ul>{Object.entries(failure.fields).map(([name, message]) => <li key={name}><a href={`#${ids[name as keyof typeof ids]}`} onClick={(event) => {
        event.preventDefault(); document.getElementById(ids[name as keyof typeof ids])?.focus()
      }}>{message}</a></li>)}</ul>}
    </Alert></div>}
    <FormField id={ids.recipient_email} label="Email người nhận" hint="Bắt buộc. Dùng email của tài khoản sẽ chấp nhận lời mời." error={failure?.fields.recipient_email}>
      <Input type="email" autoComplete="off" maxLength={254} required disabled={pending} value={email} onChange={(event) => setEmail(event.target.value)} />
    </FormField>
    <div className={`field${failure?.fields.requested_role ? ' field--invalid' : ''}`}>
      <label className="field__label" htmlFor={ids.requested_role}>Vai trò tổ chức</label>
      <select id={ids.requested_role} className="input" required value={role} disabled={pending} onChange={(event) => setRole(event.target.value as InvitationRole | '')}
        aria-invalid={failure?.fields.requested_role ? true : undefined} aria-describedby={`${ids.requested_role}-hint${failure?.fields.requested_role ? ` ${ids.requested_role}-error` : ''}`}>
        <option value="">Chọn vai trò</option>{roles.map((value) => <option key={value} value={value}>{roleLabels[value]}</option>)}
      </select>
      <p className="field__hint" id={`${ids.requested_role}-hint`}>Chỉ các vai trò bạn được quyền mời xuất hiện ở đây. Lời mời không thể cấp quyền Chủ sở hữu.</p>
      {failure?.fields.requested_role && <p className="field__error" id={`${ids.requested_role}-error`}>{failure.fields.requested_role}</p>}
    </div>
    <div className="work-actions"><Button type="submit" busy={pending}>Gửi lời mời</Button><Button variant="secondary" disabled={pending} onClick={onClose}>Đóng</Button></div>
  </form>
}

function InviteCreate({ capabilities, ...props }: MutationProps & { capabilities: MemberCapabilities }) {
  const [open, setOpen] = useState(false)
  const [pending, setPending] = useState(false)
  const allowed = capabilities.can_invite && capabilities.allowed_invitation_roles.length > 0
  useEffect(() => { if (!allowed) { setOpen(false); setPending(false) } }, [allowed])
  const close = () => { if (!pending) setOpen(false) }
  if (!allowed) return null
  return <><Button onClick={() => setOpen(true)}>Mời thành viên</Button>
    {open && <Dialog open busy={pending} title="Mời thành viên" onClose={close}>
      <InviteForm {...props} roles={capabilities.allowed_invitation_roles} onClose={() => setOpen(false)} onPending={setPending} />
    </Dialog>}
  </>
}

function InvitationActions({ invitation, capabilities, ...props }: MutationProps & { invitation: ProfileInvitation; capabilities: MemberCapabilities }) {
  const [confirm, setConfirm] = useState(false)
  const [pending, setPending] = useState<'revoke' | 'resend' | null>(null)
  const [failure, setFailure] = useState<string | null>(null)
  const request = useRef<AbortController | null>(null)
  const errorSummary = useRef<HTMLDivElement>(null)
  const authorized = capabilities.can_manage_invitations && capabilities.allowed_invitation_roles.includes(invitation.requested_role)
  const canRevoke = authorized && invitation.status === 'PENDING'
  const canResend = authorized && ['PENDING', 'EXPIRED'].includes(invitation.status)
  const allowed = canRevoke || canResend
  useEffect(() => () => { request.current?.abort() }, [])
  useEffect(() => {
    if (!allowed || (pending === 'revoke' && !canRevoke)) { request.current?.abort(); request.current = null; setPending(null) }
    if (!canRevoke) setConfirm(false)
  }, [allowed, canRevoke, pending])
  useEffect(() => { if (failure) errorSummary.current?.focus() }, [failure])

  async function mutate(action: 'revoke' | 'resend') {
    if (request.current || !(action === 'revoke' ? canRevoke : canResend)) return
    const controller = new AbortController()
    request.current = controller; setPending(action); setFailure(null)
    let saved = false
    try {
      if (action === 'revoke') await membersApi.revokeInvitation(props.profileId, invitation.id, controller.signal)
      else await membersApi.resendInvitation(props.profileId, invitation.id, controller.signal)
      saved = !controller.signal.aborted
    } catch (error) {
      if (!controller.signal.aborted) {
        setFailure(uncertain(error) ? 'Chưa thể xác nhận kết quả. Kiểm tra lại danh sách trước khi thao tác tiếp.' : isApiError(error) ? error.message : 'Chưa thể xử lý lời mời.')
        if (lostScope(error)) props.onDenied(error)
        else if (uncertain(error) || (isApiError(error) && error.status === 409)) props.onChanged()
      }
    } finally {
      if (!controller.signal.aborted) { request.current = null; setPending(null) }
    }
    if (saved) {
      setConfirm(false)
      props.onNotice(action === 'revoke' ? 'Đã hủy lời mời.' : 'Đã tạo lời mời thay thế. Mã cũ không còn dùng được; xem trạng thái email mới trong danh sách.')
      props.onChanged()
    }
  }

  return <>
    {failure && !confirm && <div ref={errorSummary} className="form-summary" tabIndex={-1}><Alert kind="error">{failure}</Alert></div>}
    {allowed && <div className="work-actions">{canResend && <Button variant="secondary" busy={pending === 'resend'} disabled={pending !== null} onClick={() => void mutate('resend')}>Gửi lại lời mời</Button>}
      {canRevoke && <Button variant="danger" disabled={pending !== null} onClick={() => { setFailure(null); setConfirm(true) }}>Hủy lời mời</Button>}</div>}
    {confirm && canRevoke && <Dialog open busy={pending !== null} title="Hủy lời mời" onClose={() => { if (!pending) setConfirm(false) }}>
      <p>Người nhận sẽ không thể dùng lời mời này để tham gia tổ chức. Bạn có chắc muốn hủy?</p>
      {failure && <div ref={errorSummary} className="form-summary" tabIndex={-1}><Alert kind="error">{failure}</Alert></div>}
      <div className="work-actions"><Button variant="danger" busy={pending === 'revoke'} disabled={pending !== null} onClick={() => void mutate('revoke')}>Xác nhận hủy lời mời</Button><Button variant="secondary" disabled={pending !== null} onClick={() => setConfirm(false)}>Giữ lời mời</Button></div>
    </Dialog>}
  </>
}

export function OrganizationMembers({ profileId, currentUserId }: { profileId: string; currentUserId: string }) {
  return <ScopedOrganizationMembers key={`${currentUserId}:${profileId}`} profileId={profileId} currentUserId={currentUserId} />
}

function ScopedOrganizationMembers({ profileId, currentUserId }: { profileId: string; currentUserId: string }) {
  const client = useQueryClient()
  const [memberPage, setMemberPage] = useState(1)
  const [invitationPage, setInvitationPage] = useState(1)
  const [notice, setNotice] = useState('')
  const [blocked, setBlocked] = useState<unknown>(null)
  const profile = useQuery({ queryKey: queryKeys.profile(profileId), queryFn: ({ signal }) => tenantApi.profile(profileId, signal), enabled: !blocked })
  const members = useQuery({ queryKey: memberKeys.members(currentUserId, profileId, memberPage), queryFn: ({ signal }) => membersApi.members(profileId, memberPage, signal), enabled: !blocked && profile.isSuccess })
  const invitations = useQuery({ queryKey: memberKeys.invitations(currentUserId, profileId, invitationPage), queryFn: ({ signal }) => membersApi.invitations(profileId, invitationPage, signal), enabled: !blocked && profile.isSuccess && members.isSuccess })
  const scopeKey = memberKeys.profile(currentUserId, profileId)
  const deny = useCallback((error: unknown) => {
    setBlocked(error)
    const key = memberKeys.profile(currentUserId, profileId)
    void client.cancelQueries({ queryKey: key }).then(() => { client.removeQueries({ queryKey: key }) })
  }, [client, currentUserId, profileId])
  const scopeError = blocked || (profile.isError ? profile.error : members.isError ? members.error : null)
  useEffect(() => { if (!blocked && lostScope(scopeError)) deny(scopeError) }, [blocked, deny, scopeError])
  useEffect(() => { if (!blocked && invitations.isError && lostScope(invitations.error)) deny(invitations.error) }, [blocked, deny, invitations.error, invitations.isError])
  const changed = () => { void client.invalidateQueries({ queryKey: scopeKey }) }
  const retry = () => { setBlocked(null); void profile.refetch(); void members.refetch() }
  const header = <PageHeader title="Thành viên tổ chức" eyebrow={profile.isSuccess ? profile.data.name : 'TỔ CHỨC'} description="Thông tin thành viên trong phạm vi truy cập hiện tại của bạn." back={{ to: `/profiles/${profileId}`, label: 'Thông tin tổ chức' }} />
  if (scopeError) return <>{header}<ErrorState error={scopeError} onRetry={retry} /><p className="read-note">Chỉ Chủ sở hữu hoặc Quản trị viên tổ chức được xem danh sách này. Quyền trong Workspace không tự cấp quyền quản trị tổ chức.</p></>
  if (!profile.isSuccess || !members.isSuccess) return <>{header}<PageSkeleton label="Đang tải thành viên tổ chức…" /></>
  const capabilities = members.data.capabilities
  const mutation = { profileId, onChanged: changed, onDenied: deny, onNotice: setNotice }
  return <>
    <PageHeader title="Thành viên tổ chức" eyebrow={profile.data.name} description="Mời đúng người, cấp đúng phạm vi truy cập." back={{ to: `/profiles/${profileId}`, label: 'Thông tin tổ chức' }}
      action={<InviteCreate {...mutation} capabilities={capabilities} />} />
    <Alert>Thành viên tổ chức và quyền Workspace được quản lý độc lập. Người nhận chỉ tham gia sau khi chấp nhận lời mời hợp lệ.</Alert>
    {profile.data.status === 'ARCHIVED' && <Alert>Tổ chức đã lưu trữ. Danh sách chỉ đọc; không thể tạo, gửi lại hoặc hủy lời mời.</Alert>}
    {notice && <Alert kind="success">{notice}</Alert>}
    <section className="section-block" aria-labelledby="organization-members-heading"><div className="section-heading"><div><p className="eyebrow">NHỮNG NGƯỜI TRONG TỔ CHỨC</p><h2 id="organization-members-heading">Thành viên</h2></div><span className="subtle-label">{members.data.count} thành viên</span></div>
      {members.data.results.length ? <Card><ul className="member-list" aria-label="Thành viên tổ chức">{members.data.results.map((member) => <li key={member.id}><strong>{member.display_label}</strong><span>{roleLabels[member.role]} · {member.is_active ? 'Đang hoạt động' : 'Không hoạt động'}</span></li>)}</ul></Card> : <EmptyState title="Chưa có thành viên để hiển thị" description="Danh sách trong phạm vi bạn được phép xem sẽ xuất hiện tại đây." />}
      <Pagination page={memberPage} count={members.data.count} onPageChange={setMemberPage} label="Phân trang thành viên" />
      <p className="read-note">Trạng thái ở đây thuộc thành viên tổ chức. Trang này chưa hỗ trợ đổi vai trò hoặc loại thành viên.</p>
    </section>
    <section className="section-block" aria-labelledby="organization-invitations-heading"><div className="section-heading"><div><p className="eyebrow">THEO DÕI LỜI MỜI</p><h2 id="organization-invitations-heading">Lời mời tổ chức</h2></div></div>
      <p className="read-note">Bao gồm lời mời đang chờ và đã xử lý trong phạm vi quản lý của bạn. Hệ thống email tiếp nhận không xác nhận email đã đến hộp thư người nhận.</p>
      {invitations.isPending ? <PageSkeleton label="Đang tải lời mời…" /> : invitations.isError ? <ErrorState error={invitations.error} onRetry={() => void invitations.refetch()} /> : <>
        {invitations.data.results.length ? <ul className="collaboration-list" aria-label="Lời mời tổ chức">{invitations.data.results.map((invitation) => <li className="card collaboration-item" key={invitation.id}>
          <h3 className="preserve-text">{invitation.recipient_email}</h3><p>{roleLabels[invitation.requested_role]} · {invitationLabels[invitation.status]}</p>
          <p>{deliveryLabels[invitation.delivery_status]}</p><p className="read-note">Tạo {dateLabel(invitation.created_at)} · Hạn {dateLabel(invitation.expires_at)}</p>
          <InvitationActions {...mutation} invitation={invitation} capabilities={capabilities} />
        </li>)}</ul> : <EmptyState title="Chưa có lời mời" description="Tạo lời mời bằng email để người nhận chủ động tham gia tổ chức." />}
        <Pagination page={invitationPage} count={invitations.data.count} onPageChange={setInvitationPage} label="Phân trang lời mời" />
      </>}
    </section>
  </>
}
