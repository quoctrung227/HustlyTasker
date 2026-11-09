import { useCallback, useEffect, useId, useRef, useState } from 'react'
import type { FormEvent, ReactNode } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router'
import { Alert, Button, Card, Dialog, EmptyState, ErrorState, PageSkeleton, Pagination } from '../../components/ui'
import { isApiError } from '../../services/api/client'
import { queryKeys } from '../../services/api/queries'
import { workKeys } from '../../services/api/work-management'
import { workspaceAccessApi, workspaceAccessKeys } from '../../services/api/workspace-access'
import type { WorkspaceAccessCapabilities, WorkspaceAccessMember, WorkspaceAccessRole } from '../../services/api/workspace-access'

const roleLabels: Record<WorkspaceAccessRole, string> = { ADMIN: 'Quản lý (ADMIN)', MEMBER: 'Editor (MEMBER)', VIEWER: 'Chỉ xem (VIEWER)' }
const profileRoleLabels = { OWNER: 'Chủ sở hữu', ADMIN: 'Quản trị viên', MEMBER: 'Thành viên' }
const lostScope = (error: unknown) => isApiError(error) && error.kind !== 'csrf' && [401, 403, 404].includes(error.status)
const uncertain = (error: unknown) => !isApiError(error) || error.status === 0 || error.status >= 500
type Field = 'target_profile_membership_id' | 'role'
type Failure = { message: string; fields: Partial<Record<Field, string>> }
type Scope = { profileId: string; workspaceId: string; currentUserId: string }
type MutationProps = Scope & { onChanged: () => void; onDenied: (error: unknown) => void; onNotice: (message: string) => void }

function failureFor(error: unknown): Failure {
  const api = isApiError(error) ? error : null
  const fields: Failure['fields'] = {}
  if (api?.fieldErrors.target_profile_membership_id) fields.target_profile_membership_id = 'Thành viên này không còn đủ điều kiện. Hãy tải lại danh sách và kiểm tra quyền hiện tại.'
  if (api?.fieldErrors.role) fields.role = 'Chọn vai trò hiện được backend cho phép.'
  return { message: uncertain(error) ? 'Chưa xác nhận được kết quả. Hãy kiểm tra danh sách trước khi thử lại.' : api?.message || 'Chưa thể cập nhật quyền truy cập.', fields }
}

function FormFailure({ failure, ids }: { failure: Failure; ids: Partial<Record<Field, string>> }) {
  const summary = useRef<HTMLDivElement>(null)
  useEffect(() => { if (failure.message || Object.keys(failure.fields).length) summary.current?.focus() }, [failure])
  return <div ref={summary} className="form-summary" tabIndex={-1}><Alert kind="error" title="Chưa thể cập nhật quyền"><p>{failure.message}</p>
    {Object.keys(failure.fields).length > 0 && <ul>{Object.entries(failure.fields).map(([field, message]) => {
      const target = ids[field as Field]
      return <li key={field}>{target ? <a href={`#${target}`} onClick={(event) => { event.preventDefault(); document.getElementById(target)?.focus() }}>{message}</a> : message}</li>
    })}</ul>}
  </Alert></div>
}

function SelectField({ id, label, value, onChange, disabled, error, hint, children }: {
  id: string; label: string; value: string; onChange: (value: string) => void; disabled?: boolean; error?: string; hint: string; children: ReactNode
}) {
  return <div className={`field${error ? ' field--invalid' : ''}`}><label className="field__label" htmlFor={id}>{label}</label>
    <select id={id} className="input" value={value} required disabled={disabled} onChange={(event) => onChange(event.target.value)}
      aria-invalid={error ? true : undefined} aria-describedby={`${id}-hint${error ? ` ${id}-error` : ''}`}>{children}</select>
    <p className="field__hint" id={`${id}-hint`}>{hint}</p>{error && <p className="field__error" id={`${id}-error`}>{error}</p>}
  </div>
}

function InheritedWarning() {
  return <Alert>Người này có quyền quản trị kế thừa từ tổ chức. Thay đổi hoặc thu hồi phân quyền trực tiếp không loại bỏ quyền kế thừa đó.</Alert>
}

function AddForm({ capabilities, onClose, onPending, ...props }: MutationProps & {
  capabilities: WorkspaceAccessCapabilities; onClose: () => void; onPending: (pending: boolean) => void
}) {
  const id = useId()
  const [page, setPage] = useState(1)
  const [selected, setSelected] = useState('')
  const [role, setRole] = useState<WorkspaceAccessRole | ''>(capabilities.allowed_roles.includes('MEMBER') ? 'MEMBER' : '')
  const [pending, setPending] = useState(false)
  const [failure, setFailure] = useState<Failure | null>(null)
  const request = useRef<AbortController | null>(null)
  const candidates = useQuery({ queryKey: workspaceAccessKeys.candidates(props.currentUserId, props.profileId, props.workspaceId, page),
    queryFn: ({ signal }) => workspaceAccessApi.candidates(props.profileId, props.workspaceId, page, signal) })
  const current = candidates.isSuccess ? candidates.data.results.find((candidate) => candidate.profile_membership_id === selected) : undefined
  const ids = { target_profile_membership_id: `${id}-candidate`, role: `${id}-role` }
  useEffect(() => () => { request.current?.abort() }, [])
  useEffect(() => { if (candidates.isError && lostScope(candidates.error)) props.onDenied(candidates.error) }, [candidates.error, candidates.isError, props.onDenied])
  useEffect(() => {
    if (role && !capabilities.allowed_roles.includes(role)) {
      request.current?.abort(); request.current = null; setPending(false); onPending(false); setRole('')
      setFailure({ message: 'Quyền quản lý đã thay đổi. Kiểm tra danh sách trước khi thao tác tiếp.', fields: { role: 'Chọn vai trò hiện được phép.' } })
    }
  }, [capabilities.allowed_roles, onPending, role])

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (request.current || candidates.isPending || candidates.isError) return
    const fields: Failure['fields'] = {}
    if (!current) fields.target_profile_membership_id = 'Chọn một thành viên tổ chức đủ điều kiện trong trang hiện tại.'
    if (!role || !capabilities.allowed_roles.includes(role)) fields.role = 'Chọn vai trò hiện được phép.'
    if (Object.keys(fields).length || !role || !current) { setFailure({ message: 'Vui lòng kiểm tra thông tin phân quyền.', fields }); return }
    const controller = new AbortController()
    request.current = controller; setPending(true); onPending(true); setFailure(null)
    let saved = false
    try {
      await workspaceAccessApi.add(props.profileId, props.workspaceId, { target_profile_membership_id: current.profile_membership_id, role }, controller.signal)
      saved = !controller.signal.aborted
    } catch (error) {
      if (!controller.signal.aborted) {
        setFailure(failureFor(error))
        if (lostScope(error)) props.onDenied(error)
        else if (uncertain(error) || (isApiError(error) && error.status === 409)) props.onChanged()
      }
    } finally {
      if (!controller.signal.aborted) { request.current = null; setPending(false); onPending(false) }
    }
    if (saved) { props.onNotice('Đã cấp phân quyền trực tiếp trong Workspace. Quyền nhận việc vẫn được kiểm tra riêng.'); props.onChanged(); onClose() }
  }

  return <form className="work-form" aria-label="Thêm thành viên Workspace" noValidate onSubmit={(event) => void submit(event)} aria-busy={pending || undefined}>
    <p>Chỉ chọn người đã là thành viên đang hoạt động của cùng tổ chức. Không gửi lời mời email từ biểu mẫu này.</p>
    {failure && <FormFailure failure={failure} ids={ids} />}
    {candidates.isPending && <p role="status">Đang tải thành viên đủ điều kiện…</p>}
    {candidates.isError && <ErrorState error={candidates.error} onRetry={() => void candidates.refetch()} />}
    <SelectField id={ids.target_profile_membership_id} label="Chọn thành viên tổ chức" value={current?.profile_membership_id || ''} onChange={setSelected}
      disabled={pending || candidates.isPending || candidates.isError} error={failure?.fields.target_profile_membership_id} hint="Bắt buộc. Danh sách chỉ gồm người có thể được cấp phân quyền trực tiếp trong Workspace này.">
      <option value="">Chọn thành viên</option>{candidates.isSuccess && candidates.data.results.map((candidate) => <option key={candidate.profile_membership_id} value={candidate.profile_membership_id}>{candidate.display_label}{candidates.data.results.filter((entry) => entry.display_label === candidate.display_label).length > 1 ? ` (…${candidate.profile_membership_id.slice(-8)})` : ''}{candidate.has_inherited_access ? ' · Quyền kế thừa' : ''}</option>)}
    </SelectField>
    {candidates.isSuccess && candidates.data.results.length === 0 && <p className="read-note">Không có thành viên đủ điều kiện trong trang này. Người đã có phân quyền trực tiếp không xuất hiện lại.</p>}
    {candidates.isSuccess && <Pagination label="Phân trang ứng viên Workspace" count={candidates.data.count} page={page} disabled={pending || candidates.isFetching} onPageChange={(next) => { if (!pending) { setSelected(''); setPage(next) } }} />}
    {current?.has_inherited_access && <InheritedWarning />}
    <SelectField id={ids.role} label="Vai trò trong Workspace" value={role} onChange={(value) => setRole(value as WorkspaceAccessRole | '')} disabled={pending}
      error={failure?.fields.role} hint="Bắt buộc. Chỉ các vai trò trong phạm vi quản lý hiện tại của bạn được hiển thị.">
      <option value="">Chọn vai trò</option>{capabilities.allowed_roles.map((value) => <option key={value} value={value}>{roleLabels[value]}</option>)}
    </SelectField>
    <p className="read-note">Quản lý và Chỉ xem không tự trở thành Editor nhận việc. Backend kiểm tra lại quyền khi lưu.</p>
    {capabilities.profile_role === 'OWNER' || capabilities.profile_role === 'ADMIN'
      ? <Link className="text-link" to={`/profiles/${props.profileId}/members`}>Mời người chưa thuộc tổ chức</Link>
      : <p className="read-note">Người chưa thuộc tổ chức cần được Chủ sở hữu hoặc Quản trị viên tổ chức mời và tự chấp nhận trước.</p>}
    <div className="work-actions"><Button type="submit" busy={pending} disabled={candidates.isPending || candidates.isError || !candidates.data?.results.length}>Cấp quyền truy cập</Button><Button variant="secondary" disabled={pending} onClick={onClose}>Đóng</Button></div>
  </form>
}

function AddMember({ capabilities, ...props }: MutationProps & { capabilities: WorkspaceAccessCapabilities }) {
  const [open, setOpen] = useState(false)
  const [pending, setPending] = useState(false)
  const allowed = capabilities.can_add && capabilities.allowed_roles.length > 0
  useEffect(() => { if (!allowed) { setOpen(false); setPending(false) } }, [allowed])
  if (!allowed) return null
  return <><Button onClick={() => setOpen(true)}>Thêm thành viên</Button>{open && <Dialog open busy={pending} title="Thêm thành viên Workspace" onClose={() => { if (!pending) setOpen(false) }}>
    <AddForm {...props} capabilities={capabilities} onClose={() => setOpen(false)} onPending={setPending} />
  </Dialog>}</>
}

function UpdateForm({ member, onClose, onPending, ...props }: MutationProps & { member: WorkspaceAccessMember; onClose: () => void; onPending: (pending: boolean) => void }) {
  const id = useId()
  const [role, setRole] = useState<WorkspaceAccessRole | ''>(member.capabilities.allowed_roles.includes(member.role) ? member.role : '')
  const [pending, setPending] = useState(false)
  const [failure, setFailure] = useState<Failure | null>(null)
  const request = useRef<AbortController | null>(null)
  useEffect(() => () => { request.current?.abort() }, [])
  useEffect(() => {
    if (role && !member.capabilities.allowed_roles.includes(role)) {
      request.current?.abort(); request.current = null; setPending(false); onPending(false); setRole('')
      setFailure({ message: 'Vai trò được phép đã thay đổi. Kiểm tra danh sách trước khi thao tác tiếp.', fields: { role: 'Chọn vai trò hiện được phép.' } })
    }
  }, [member.capabilities.allowed_roles, onPending, role])
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (request.current) return
    if (!role || !member.capabilities.allowed_roles.includes(role)) { setFailure({ message: 'Vui lòng kiểm tra vai trò.', fields: { role: 'Chọn vai trò hiện được phép.' } }); return }
    const controller = new AbortController()
    request.current = controller; setPending(true); onPending(true); setFailure(null)
    let saved = false
    try { await workspaceAccessApi.update(props.profileId, props.workspaceId, member.id, { role }, controller.signal); saved = !controller.signal.aborted } catch (error) {
      if (!controller.signal.aborted) {
        setFailure(failureFor(error))
        if (lostScope(error)) props.onDenied(error)
        else if (uncertain(error) || (isApiError(error) && error.status === 409)) props.onChanged()
      }
    } finally { if (!controller.signal.aborted) { request.current = null; setPending(false); onPending(false) } }
    if (saved) { props.onNotice('Đã cập nhật phân quyền trực tiếp.'); props.onChanged(); onClose() }
  }
  return <form className="work-form" aria-label="Cập nhật quyền Workspace" noValidate onSubmit={(event) => void submit(event)} aria-busy={pending || undefined}>
    <p>Xác nhận thay đổi phân quyền trực tiếp của <strong>{member.display_label}</strong>. Vai trò hiện tại: {roleLabels[member.role]}.</p>
    {member.capabilities.has_inherited_access && <InheritedWarning />}
    {failure && <FormFailure failure={failure} ids={{ role: id }} />}
    <SelectField id={id} label="Vai trò trong Workspace" value={role} onChange={(value) => setRole(value as WorkspaceAccessRole | '')} disabled={pending}
      error={failure?.fields.role} hint="Chọn vai trò mới rồi xác nhận. Backend sẽ kiểm tra lại quyền và trạng thái hiện tại.">
      <option value="">Chọn vai trò</option>{member.capabilities.allowed_roles.map((value) => <option key={value} value={value}>{roleLabels[value]}</option>)}
    </SelectField>
    <div className="work-actions"><Button type="submit" busy={pending} disabled={role === member.role}>Xác nhận cập nhật quyền</Button><Button variant="secondary" disabled={pending} onClick={onClose}>Giữ quyền hiện tại</Button></div>
  </form>
}

function MemberActions({ member, ...props }: MutationProps & { member: WorkspaceAccessMember }) {
  const [action, setAction] = useState<'update' | 'revoke' | null>(null)
  const [pending, setPending] = useState(false)
  const [failure, setFailure] = useState<Failure | null>(null)
  const request = useRef<AbortController | null>(null)
  const canUpdate = member.capabilities.can_update && member.capabilities.allowed_roles.length > 0
  const canRevoke = member.capabilities.can_revoke
  useEffect(() => () => { request.current?.abort() }, [])
  useEffect(() => {
    if ((action === 'update' && !canUpdate) || (action === 'revoke' && !canRevoke)) {
      request.current?.abort(); request.current = null; setAction(null); setPending(false); setFailure(null)
    }
  }, [action, canRevoke, canUpdate])
  function close() { if (!pending) { setAction(null); setFailure(null) } }
  async function revoke() {
    if (request.current || !canRevoke) return
    const controller = new AbortController()
    request.current = controller; setPending(true); setFailure(null)
    let saved = false
    try { await workspaceAccessApi.revoke(props.profileId, props.workspaceId, member.id, controller.signal); saved = !controller.signal.aborted } catch (error) {
      if (!controller.signal.aborted) {
        setFailure(failureFor(error))
        if (lostScope(error)) props.onDenied(error)
        else if (uncertain(error) || (isApiError(error) && error.status === 409)) props.onChanged()
      }
    } finally { if (!controller.signal.aborted) { request.current = null; setPending(false) } }
    if (saved) { setAction(null); props.onNotice('Đã thu hồi phân quyền trực tiếp trong Workspace.'); props.onChanged() }
  }
  if (!canUpdate && !canRevoke) return null
  return <><fieldset className="work-actions" aria-label={`Quyền của ${member.display_label}`}>
    {canUpdate && <Button variant="secondary" onClick={() => setAction('update')}>Cập nhật quyền</Button>}
    {canRevoke && <Button variant="danger" onClick={() => setAction('revoke')}>Thu hồi quyền</Button>}
  </fieldset>
    {action === 'update' && canUpdate && <Dialog open busy={pending} title="Cập nhật quyền Workspace" onClose={close}>
      <UpdateForm {...props} member={member} onClose={() => setAction(null)} onPending={setPending} />
    </Dialog>}
    {action === 'revoke' && canRevoke && <Dialog open busy={pending} title="Thu hồi quyền Workspace" onClose={close}>
      <p>Thu hồi phân quyền trực tiếp của <strong>{member.display_label}</strong> trong Workspace này?</p>
      <p>Công việc và sản phẩm đã nộp không bị xóa. Quyền truy cập và nhận việc vẫn được backend kiểm tra theo trạng thái hiện tại.</p>
      {member.capabilities.has_inherited_access && <InheritedWarning />}
      {failure && <FormFailure failure={failure} ids={{}} />}
      <div className="work-actions"><Button variant="danger" busy={pending} onClick={() => void revoke()}>Xác nhận thu hồi quyền</Button><Button variant="secondary" disabled={pending} onClick={close}>Giữ quyền hiện tại</Button></div>
    </Dialog>}
  </>
}

export function WorkspaceMembers(props: Scope) {
  return <ScopedWorkspaceMembers key={`${props.currentUserId}:${props.profileId}:${props.workspaceId}`} {...props} />
}

function ScopedWorkspaceMembers(props: Scope) {
  const client = useQueryClient()
  const [page, setPage] = useState(1)
  const [notice, setNotice] = useState('')
  const [blocked, setBlocked] = useState<unknown>(null)
  const members = useQuery({ queryKey: workspaceAccessKeys.members(props.currentUserId, props.profileId, props.workspaceId, page),
    queryFn: ({ signal }) => workspaceAccessApi.members(props.profileId, props.workspaceId, page, signal), enabled: !blocked })
  const deny = useCallback((error: unknown) => {
    setBlocked(error)
    const key = workspaceAccessKeys.scope(props.currentUserId, props.profileId, props.workspaceId)
    void client.cancelQueries({ queryKey: key }).then(() => { client.removeQueries({ queryKey: key }) })
    // Roster403 may simply mean Editor/Viewer authority: do not erase otherwise
    // legitimate Task reads.404 is a stale/missing scope and requires fresh
    // Workspace authority plus removal of cached work in that scope.
    if (isApiError(error) && error.status === 404) {
      const workScope = workKeys.scope(props.profileId, props.workspaceId)
      void client.cancelQueries({ queryKey: workScope }).then(() => { client.removeQueries({ queryKey: workScope }) })
      void client.invalidateQueries({ queryKey: queryKeys.workspace(props.profileId, props.workspaceId) })
      void client.invalidateQueries({ queryKey: ['profiles', props.profileId, 'workspaces'] })
    }
  }, [client, props.currentUserId, props.profileId, props.workspaceId])
  const scopeError = blocked || (members.isError ? members.error : null)
  useEffect(() => { if (!blocked && lostScope(scopeError)) deny(scopeError) }, [blocked, deny, scopeError])
  const changed = () => {
    void client.invalidateQueries({ queryKey: workspaceAccessKeys.scope(props.currentUserId, props.profileId, props.workspaceId) })
    void client.invalidateQueries({ queryKey: workKeys.scope(props.profileId, props.workspaceId) })
    void client.invalidateQueries({ queryKey: ['profiles', props.profileId, 'workspaces'] })
    void client.invalidateQueries({ queryKey: queryKeys.profile(props.profileId) })
  }
  const retry = () => { setBlocked(null); void members.refetch() }
  const heading = <div className="section-heading"><div><p className="eyebrow">PHÂN QUYỀN CÙNG LÀM VIỆC</p><h2 id="workspace-members-heading">Thành viên Workspace</h2></div></div>
  if (scopeError) return <section className="section-block" id="workspace-members" aria-labelledby="workspace-members-heading">{heading}
    <ErrorState error={scopeError} onRetry={lostScope(scopeError) ? undefined : retry} />
    <p className="read-note">Chỉ Chủ sở hữu/Quản trị viên tổ chức hoặc Quản lý Workspace được xem và quản lý danh sách này. Quyền xem công việc không tự cấp quyền quản trị thành viên.</p>
  </section>
  if (!members.isSuccess) return <section className="section-block" id="workspace-members" aria-labelledby="workspace-members-heading">{heading}<PageSkeleton label="Đang tải quyền truy cập Workspace…" /></section>
  const capabilities = members.data.capabilities
  const mutation = { ...props, onChanged: changed, onDenied: deny, onNotice: setNotice }
  return <section className="section-block" id="workspace-members" aria-labelledby="workspace-members-heading">
    <div className="section-heading"><div><p className="eyebrow">PHÂN QUYỀN CÙNG LÀM VIỆC</p><h2 id="workspace-members-heading">Thành viên Workspace</h2></div><AddMember {...mutation} capabilities={capabilities} /></div>
    <p className="read-note">Danh sách chỉ gồm phân quyền Workspace trực tiếp đang hoạt động. Chủ sở hữu/Quản trị viên tổ chức có quyền kế thừa dù không có dòng trong danh sách.</p>
    <Card className="metadata-card"><dl><div><dt>Vai trò tổ chức của bạn</dt><dd>{profileRoleLabels[capabilities.profile_role]}</dd></div><div><dt>Quyền Workspace trong ngữ cảnh truy cập</dt><dd>{capabilities.has_inherited_access ? 'Quản trị kế thừa từ tổ chức' : capabilities.workspace_role ? roleLabels[capabilities.workspace_role] : 'Không xác định phân quyền trực tiếp'}</dd></div></dl></Card>
    {capabilities.has_inherited_access && <p className="read-note">Bạn đang có quyền quản trị kế thừa từ tổ chức. Thu hồi một dòng phân quyền trực tiếp không làm mất quyền này.</p>}
    {!capabilities.can_add && <Alert>Phân quyền hiện tại chỉ cho phép xem danh sách. Workspace hoặc tổ chức đã lưu trữ không thể thay đổi thành viên.</Alert>}
    {notice && <Alert kind="success">{notice}</Alert>}
    {members.data.results.length ? <ul className="collaboration-list" aria-label="Thành viên Workspace">{members.data.results.map((member) => <li className="card collaboration-item" key={member.id}>
      <h3 className="preserve-text">{member.display_label}</h3><p>{roleLabels[member.role]} · Đang hoạt động</p>
      {member.capabilities.has_inherited_access && <p className="read-note">Có quyền quản trị kế thừa từ tổ chức.</p>}
      <MemberActions {...mutation} member={member} />
    </li>)}</ul> : <EmptyState title="Chưa có phân quyền trực tiếp" description="Cấp quyền cho thành viên tổ chức đủ điều kiện. Quyền quản trị kế thừa từ tổ chức vẫn được giữ nguyên." />}
    <Pagination label="Phân trang thành viên Workspace" count={members.data.count} page={page} onPageChange={setPage} />
  </section>
}
