import { useEffect, useId, useState } from 'react'
import { Alert, Button, ErrorState, Pagination } from '../../components/ui'
import { periodLabel } from '../../components/page'
import { tenantApi } from '../../services/api/queries'
import type { Page, Workspace } from '../../services/api/types'
import { workspaceInheritanceApi } from '../../services/api/workspace-inheritance'
import type { WorkspaceInheritancePreview, WorkspaceMembershipInput } from '../../services/api/workspace-inheritance'

const roleLabels = { ADMIN: 'Quản lý (ADMIN)', MEMBER: 'Editor (MEMBER)', VIEWER: 'Chỉ xem (VIEWER)' }
type Load<T> = { loading: boolean; data?: T; error?: unknown; attempt?: number }

/** Local, abortable previews never outlive the current User/Profile form. */
export function WorkspaceMembershipSetup({ profileId, pending, onChange, onReady }: {
  profileId: string; pending: boolean
  onChange: (input: WorkspaceMembershipInput) => void
  onReady: (ready: boolean) => void
}) {
  const id = useId()
  const [sourceId, setSourceId] = useState('')
  const [sourcePage, setSourcePage] = useState(1)
  const [previewPage, setPreviewPage] = useState(1)
  const [selected, setSelected] = useState<string[]>([])
  const [reload, setReload] = useState(0)
  const [sources, setSources] = useState<Load<Page<Workspace>>>({ loading: true })
  const [preview, setPreview] = useState<Load<WorkspaceInheritancePreview> & { sourceId?: string; page?: number }>({ loading: true })

  useEffect(() => {
    const controller = new AbortController()
    setSources({ loading: true, attempt: reload })
    void tenantApi.workspaces(profileId, sourcePage, controller.signal).then((data) => {
      if (!controller.signal.aborted) setSources({ loading: false, data, attempt: reload })
    }).catch((error: unknown) => { if (!controller.signal.aborted) setSources({ loading: false, error, attempt: reload }) })
    return () => controller.abort()
  }, [profileId, sourcePage, reload])

  useEffect(() => {
    const controller = new AbortController()
    onReady(false)
    setPreview({ loading: true, attempt: reload })
    void workspaceInheritanceApi.preview(profileId, sourceId, previewPage, controller.signal).then((data) => {
      if (!controller.signal.aborted) setPreview({ loading: false, data, sourceId, page: previewPage, attempt: reload })
    }).catch((error: unknown) => { if (!controller.signal.aborted) setPreview({ loading: false, error, attempt: reload }) })
    return () => controller.abort()
  }, [profileId, sourceId, previewPage, reload, onReady])

  useEffect(() => {
    const data = preview.sourceId === sourceId && preview.page === previewPage && preview.attempt === reload ? preview.data : undefined
    onReady(!preview.loading && !!data && !sources.loading && !!sources.data && sources.attempt === reload)
    onChange(sourceId ? { source_workspace_id: sourceId } : data?.mode === 'initial' ? { initial_profile_membership_ids: selected } : {})
  }, [preview, previewPage, sources.loading, sources.data, sources.attempt, sourceId, selected, reload, onReady, onChange])

  function changeSource(value: string) {
    onReady(false)
    setSourceId(value); setPreviewPage(1); setSelected([])
  }
  const data = preview.sourceId === sourceId && preview.page === previewPage && preview.attempt === reload ? preview.data : undefined
  const selectedSource = data?.source_workspace
  const listedSource = sources.data?.results.some((source) => source.id === sourceId)
  const retry = () => setReload((value) => value + 1)

  return <fieldset className="workspace-member-fields" disabled={pending}>
    <legend>Thành viên Workspace</legend>
    <p className="field__hint">Kế thừa chỉ sao chép thành viên còn hợp lệ và vai trò hiện tại. Không sao chép Task, phân công, Review hoặc Comment. Quyền quản trị kế thừa của Chủ sở hữu/Quản trị viên tổ chức được giữ nguyên.</p>
    <div className="field"><label className="field__label" htmlFor={id}>Workspace nguồn</label>
      <select id={id} className="input" value={sourceId} disabled={pending || sources.loading} onChange={(event) => changeSource(event.target.value)} aria-describedby={`${id}-hint`}>
        <option value="">Thiết lập thủ công / Workspace đầu tiên</option>
        {sourceId && !listedSource && <option value={sourceId}>{selectedSource ? `${selectedSource.name} · ${periodLabel(selectedSource.period)}` : 'Nguồn đã chọn'}</option>}
        {sources.data?.results.map((source) => <option value={source.id} key={source.id}>{source.name} · {periodLabel(source.period)}{source.status === 'ARCHIVED' ? ' · Đã lưu trữ' : ''}</option>)}
      </select>
      <p id={`${id}-hint`} className="field__hint">Chọn nguồn rõ ràng trong cùng tổ chức. Không tự lấy Workspace mới tạo gần nhất làm tháng trước. Nguồn đã lưu trữ có thể được đọc làm bản chụp quyền.</p>
    </div>
    {sources.loading && <p role="status">Đang tải Workspace nguồn…</p>}
    {sources.error !== undefined && <ErrorState error={sources.error} onRetry={retry} />}
    {sources.data && <Pagination label="Phân trang Workspace nguồn" count={sources.data.count} page={sourcePage} disabled={pending || sources.loading} onPageChange={setSourcePage} />}
    {preview.loading && <p role="status">Đang kiểm tra thành viên…</p>}
    {preview.error !== undefined && <ErrorState error={preview.error} onRetry={retry} />}
    {data?.mode === 'inheritance' && <>
      <p role="status"><strong>{data.count}</strong> thành viên sẽ được kế thừa từ <strong>{data.source_workspace?.name}</strong>.</p>
      <ul className="member-list" aria-label="Thành viên sẽ được kế thừa">{data.results.map((member) => <li key={member.profile_membership_id}><span>{member.display_name}</span><span>{roleLabels[member.role]}</span></li>)}</ul>
      {data.excluded_count > 0 && <p className="read-note">{data.excluded_count} phân quyền nguồn không được sao chép vì đã thu hồi, không còn đủ điều kiện hoặc đã có quyền quản trị kế thừa. Không hiển thị thông tin của người không còn quyền.</p>}
      <Alert>Vai trò là bản chụp tại thời điểm tạo. Backend kiểm tra lại trước khi lưu; thay đổi nguồn về sau không tự thay đổi Workspace mới.</Alert>
    </>}
    {data?.mode === 'initial' && <>
      <p>Đây là Workspace đầu tiên. Chọn và xác nhận thành viên tổ chức đang hoạt động để cấp vai trò Editor (MEMBER). Không tự cấp ADMIN.</p>
      <p role="status">{selected.length} thành viên đã chọn / {data.count} thành viên được đề xuất.</p>
      <ul className="member-list" aria-label="Thành viên Workspace đầu tiên">{data.results.map((member) => <li key={member.profile_membership_id}><label className="checkbox-label"><input type="checkbox" checked={selected.includes(member.profile_membership_id)} onChange={(event) => setSelected((current) => event.target.checked ? [...current, member.profile_membership_id] : current.filter((value) => value !== member.profile_membership_id))} />{member.display_name} · Editor (MEMBER)</label></li>)}</ul>
      {data.count === 0 && <p className="read-note">Chưa có thành viên cần phân quyền trực tiếp. Chủ sở hữu/Quản trị viên vẫn có quyền quản trị kế thừa.</p>}
      {selected.length > 0 && <Button variant="secondary" onClick={() => setSelected([])}>Bỏ chọn thành viên</Button>}
    </>}
    {data?.mode === 'manual' && <p className="read-note">Không kế thừa thành viên. Sau khi tạo, dùng mục Thành viên / Quyền truy cập để cấp quyền có chủ đích.</p>}
    {data && <Pagination label="Phân trang thành viên kế thừa" count={data.count} page={previewPage} disabled={pending || preview.loading} onPageChange={setPreviewPage} />}
    <p className="field__hint">Danh sách được kiểm tra lại khi tạo; bản xem trước không tự cấp quyền hoặc thay đổi Workspace nguồn.</p>
  </fieldset>
}
