import { useEffect, useRef, useState } from 'react'
import { Alert, Button, Dialog } from '../../components/ui'
import { isApiError } from '../../services/api/client'
import type { Workspace } from '../../services/api/types'
import { WorkspaceForm } from './WorkspaceCreate'
import type { WorkspaceUpdateInput } from './WorkspaceCreate'

type LifecycleAction = 'archive' | 'restore'

type WorkspaceActionsProps = {
  profileId: string
  workspace: Workspace
  capabilities: { canEdit?: boolean; canArchive?: boolean; canRestore?: boolean }
  onUpdate: (input: WorkspaceUpdateInput, signal?: AbortSignal) => Promise<Workspace>
  onLifecycle: (action: LifecycleAction, signal?: AbortSignal) => Promise<Workspace>
  onSaved?: (workspace: Workspace) => void
  onDenied?: () => void
}

export function WorkspaceActions(props: WorkspaceActionsProps) {
  return <ScopedWorkspaceActions key={`${props.profileId}:${props.workspace.id}`} {...props} />
}

function ScopedWorkspaceActions({ profileId, workspace, capabilities, onUpdate, onLifecycle, onSaved, onDenied }: WorkspaceActionsProps) {
  const [action, setAction] = useState<'edit' | LifecycleAction | null>(null)
  const [pending, setPending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const request = useRef<AbortController | null>(null)
  const summary = useRef<HTMLDivElement>(null)
  const inScope = workspace.profile_id === profileId
  const canEdit = inScope && workspace.status === 'ACTIVE' && capabilities.canEdit === true
  const canArchive = inScope && workspace.status === 'ACTIVE' && capabilities.canArchive === true
  const canRestore = inScope && workspace.status === 'ARCHIVED' && capabilities.canRestore === true

  useEffect(() => () => { request.current?.abort() }, [])
  useEffect(() => { if (error) summary.current?.focus() }, [error])
  useEffect(() => {
    if ((action === 'edit' && !canEdit) || (action === 'archive' && !canArchive) || (action === 'restore' && !canRestore)) {
      request.current?.abort()
      request.current = null
      setAction(null)
      setPending(false)
      setError(null)
    }
  }, [action, canEdit, canArchive, canRestore])

  function close() {
    if (!pending) { setAction(null); setError(null) }
  }

  async function confirmLifecycle() {
    if (request.current || (action !== 'archive' && action !== 'restore')) return
    if ((action === 'archive' && !canArchive) || (action === 'restore' && !canRestore)) return
    const controller = new AbortController()
    request.current = controller
    setPending(true)
    setError(null)
    let saved: Workspace | undefined
    try {
      saved = await onLifecycle(action, controller.signal)
    } catch (failure) {
      if (!controller.signal.aborted) {
        const apiError = isApiError(failure) ? failure : null
        setError(apiError?.message ?? 'Chưa thể cập nhật trạng thái không gian. Vui lòng thử lại sau.')
        if (apiError?.kind === 'forbidden' || apiError?.status === 404) onDenied?.()
      }
    } finally {
      if (!controller.signal.aborted) { request.current = null; setPending(false) }
    }
    if (saved && !controller.signal.aborted) { setAction(null); onSaved?.(saved) }
  }

  if (!canEdit && !canArchive && !canRestore) return null
  const lifecycleOpen = action === 'archive' ? canArchive : action === 'restore' && canRestore

  return <>
    <section className="work-actions" aria-label="Quản lý không gian">
      {canEdit && <Button variant="secondary" onClick={() => setAction('edit')}>Chỉnh sửa không gian</Button>}
      {canArchive && <Button variant="secondary" onClick={() => setAction('archive')}>Lưu trữ không gian</Button>}
      {canRestore && <Button variant="secondary" onClick={() => setAction('restore')}>Khôi phục không gian</Button>}
    </section>
    {action === 'edit' && canEdit && <Dialog open busy={pending} title="Chỉnh sửa không gian" onClose={close}>
      <WorkspaceForm key={`${profileId}:${workspace.id}`} mode="edit" workspace={workspace} onSubmit={onUpdate} onPendingChange={setPending}
        onCancel={close} onDenied={onDenied} onSaved={(saved) => { setAction(null); onSaved?.(saved) }} />
    </Dialog>}
    {lifecycleOpen && <Dialog open busy={pending} title={action === 'archive' ? 'Lưu trữ không gian' : 'Khôi phục không gian'} onClose={close}>
      {error && <div ref={summary} className="form-summary" tabIndex={-1}><Alert kind="error">{error}</Alert></div>}
      <p>{action === 'archive'
        ? `Lưu trữ “${workspace.name}”? Không gian sẽ được giữ lại và chuyển sang chế độ chỉ đọc.`
        : `Khôi phục “${workspace.name}”? Không gian sẽ hoạt động trở lại theo quyền hiện tại.`}</p>
      <div className="work-actions">
        <Button variant={action === 'archive' ? 'danger' : 'primary'} busy={pending} onClick={() => { void confirmLifecycle() }}>
          {action === 'archive' ? 'Xác nhận lưu trữ' : 'Xác nhận khôi phục'}
        </Button>
        <Button variant="secondary" disabled={pending} onClick={close}>Hủy</Button>
      </div>
    </Dialog>}
  </>
}
