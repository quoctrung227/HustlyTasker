import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { Link, useLocation, useNavigate, useParams } from 'react-router'
import { PageHeader } from '../components/page'
import { Alert, Button, Card, Dialog, FormField, Input } from '../components/ui'
import { useAuth } from '../features/auth/AuthProvider'
import { OrganizationMembers } from '../features/members/OrganizationMembers'
import { isApiError } from '../services/api/client'
import { memberKeys, membersApi } from '../services/api/members'
import type { AcceptedInvitation } from '../services/api/members'

export const invitationResponsePath = '/invitations/respond'

export function ProfileMembersPage() {
  const { profileId = '' } = useParams()
  const { user } = useAuth()
  return <OrganizationMembers profileId={profileId} currentUserId={user?.id || ''} />
}

export function InvitationRespondPage() {
  const { user } = useAuth()
  return <ScopedInvitationRespond key={user?.id || ''} currentUserId={user?.id || ''} email={user?.email || ''} />
}

type Failure = { message: string; token?: string }
type Outcome = AcceptedInvitation | { status: 'DECLINED' }

function ScopedInvitationRespond({ currentUserId, email }: { currentUserId: string; email: string }) {
  const cache = useQueryClient()
  const location = useLocation(), navigate = useNavigate()
  const [token, setToken] = useState('')
  const [busy, setBusy] = useState(false)
  const [confirmDecline, setConfirmDecline] = useState(false)
  const [failure, setFailure] = useState<Failure | null>(null)
  const [outcome, setOutcome] = useState<Outcome | null>(null)
  const request = useRef<AbortController | null>(null)
  const summary = useRef<HTMLDivElement>(null)
  useEffect(() => () => { request.current?.abort() }, [])
  useEffect(() => { if (failure) summary.current?.focus() }, [failure])
  useEffect(() => {
    // Email currently contains an opaque token, not a URL. Never ingest or
    // forward token-bearing query/fragment input into login state or a POST.
    if (location.search || location.hash) void navigate(invitationResponsePath, { replace: true })
  }, [location.search, location.hash, navigate])

  function validate() {
    if (!token.trim() || token.length > 512 || token.includes('\0') || /[\uD800-\uDFFF]/u.test(token)) {
      setFailure({ message: 'Vui lòng kiểm tra mã lời mời.', token: 'Nhập nguyên mã từ email, tối đa 512 ký tự; không nhập đường dẫn.' })
      return false
    }
    return true
  }

  async function respond(action: 'accept' | 'decline') {
    if (request.current || !currentUserId || !validate()) return
    const controller = new AbortController()
    request.current = controller
    setBusy(true); setFailure(null)
    try {
      const result = action === 'accept'
        ? await membersApi.acceptInvitation(token, controller.signal)
        : await membersApi.declineInvitation(token, controller.signal)
      if (controller.signal.aborted) return
      setToken(''); setConfirmDecline(false); setOutcome(result)
      if (result.status === 'ACCEPTED') {
        void cache.invalidateQueries({ queryKey: ['profiles'] })
        void cache.invalidateQueries({ queryKey: memberKeys.user(currentUserId) })
      }
    } catch (error) {
      if (controller.signal.aborted) return
      setConfirmDecline(false)
      const conflict = isApiError(error) && error.status === 409
      const uncertain = !isApiError(error) || error.status === 0 || error.status >= 500
      setFailure({
        message: conflict
          ? 'Không thể xử lý mã lời mời này. Hãy kiểm tra mã mới nhất, tài khoản nhận lời mời và danh sách tổ chức của bạn.'
          : uncertain
            ? 'Chưa xác nhận được kết quả. Hãy kiểm tra danh sách tổ chức trước khi thử lại.'
            : error.message,
        ...(isApiError(error) && error.fieldErrors.token ? { token: error.fieldErrors.token } : {}),
      })
    } finally {
      if (!controller.signal.aborted) { request.current = null; setBusy(false) }
    }
  }

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    void respond('accept')
  }

  return <>
    <PageHeader eyebrow="THAM GIA TỔ CHỨC" title="Phản hồi lời mời" description="Đăng nhập đúng email nhận lời mời và nhập mã từ email. Chỉ thao tác xác nhận của bạn mới gửi yêu cầu." back={{ to: '/profiles', label: 'Tổ chức' }} />
    {outcome ? <Card className="section-block">
      <h2>{outcome.status === 'ACCEPTED' ? 'Đã tham gia tổ chức' : 'Đã từ chối lời mời'}</h2>
      <Alert kind="success">{outcome.status === 'ACCEPTED' ? 'Máy chủ đã xác nhận tư cách thành viên của bạn. Quyền truy cập từng không gian làm việc được kiểm tra riêng.' : 'Máy chủ đã ghi nhận việc từ chối. Thao tác này không tạo tư cách thành viên.'}</Alert>
      <div className="work-actions">{outcome.status === 'ACCEPTED' && <Link className="button button--primary" to={`/profiles/${outcome.profile_id}`}>Đến tổ chức</Link>}<Button variant="secondary" onClick={() => { setOutcome(null); setFailure(null) }}>Nhập mã khác</Button></div>
    </Card> : <Card className="section-block">
      <h2>Xác nhận bằng mã lời mời</h2>
      <p>Bạn đang đăng nhập bằng email <strong>{email}</strong>. Kiểm tra email mời để biết tổ chức và vai trò; trang này không tra cứu thông tin từ mã trước khi bạn xác nhận.</p>
      <form className="work-form" aria-label="Phản hồi lời mời" aria-busy={busy || undefined} noValidate onSubmit={submit}>
        {failure && <div className="form-summary" tabIndex={-1} ref={summary}><Alert kind="error" title="Chưa thể phản hồi lời mời"><p>{failure.message}</p>{failure.token && <Button variant="ghost" onClick={() => document.getElementById('invitation-token')?.focus()}>{failure.token}</Button>}</Alert></div>}
        <FormField id="invitation-token" label="Mã lời mời" hint="Mã là thông tin bí mật, chỉ được gửi khi bạn chọn chấp nhận hoặc xác nhận từ chối. Không dán mã vào địa chỉ trình duyệt." error={failure?.token}>
          <Input type="password" name="invitation-token" autoComplete="off" spellCheck={false} value={token} maxLength={512} required disabled={busy} onChange={(event) => setToken(event.target.value)} />
        </FormField>
        <div className="work-actions"><Button type="submit" busy={busy}>Chấp nhận lời mời</Button><Button variant="secondary" disabled={busy} onClick={() => { if (!request.current && validate()) { setFailure(null); setConfirmDecline(true) } }}>Từ chối lời mời</Button></div>
      </form>
      <p className="read-note">Mã không hợp lệ, hết hạn, đã dùng hoặc không khớp tài khoản đều được xử lý bằng thông báo chung. Xác minh email toàn cục và tham gia tổ chức là hai thao tác độc lập.</p>
    </Card>}
    <Dialog open={confirmDecline} busy={busy} title="Từ chối lời mời" onClose={() => { if (!busy) setConfirmDecline(false) }}>
      <p>Lời mời sẽ không còn dùng được sau khi máy chủ xác nhận từ chối.</p>
      <div className="work-actions"><Button variant="danger" busy={busy} onClick={() => void respond('decline')}>Xác nhận từ chối</Button><Button variant="secondary" disabled={busy} onClick={() => setConfirmDecline(false)}>Quay lại</Button></div>
    </Dialog>
  </>
}
