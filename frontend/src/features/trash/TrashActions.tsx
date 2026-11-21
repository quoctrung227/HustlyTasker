import { useEffect, useRef, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import type { QueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router'
import { TrashIcon } from '@phosphor-icons/react'
import { Alert, Button, Dialog } from '../../components/ui'
import { isApiError } from '../../services/api/client'
import { trashApi } from '../../services/api/trash'
import type { TrashObjectType } from '../../services/api/trash'

/** Reset observers as well as cached values, including financial/collaboration data. */
export async function resetPrivateAfterTrash(cache: QueryClient) {
  await cache.cancelQueries()
  await cache.resetQueries({ predicate: (query) => query.queryKey[0] !== 'auth' }, { cancelRefetch: true })
}
export const trashTypeLabels: Record<TrashObjectType, string> = { TASK: 'Công việc', WORKSPACE: 'Không gian', PROFILE: 'Tổ chức' }

export function TrashDeleteAction({ objectType, objectId, title, canDelete, onDenied }: {
  objectType: TrashObjectType; objectId: string; title: string; canDelete: boolean; onDenied?: () => void
}) {
  const cache = useQueryClient(), navigate = useNavigate()
  const [open, setOpen] = useState(false), [pending, setPending] = useState(false), [failure, setFailure] = useState(''), [uncertain, setUncertain] = useState(false)
  const request = useRef<AbortController | null>(null), summary = useRef<HTMLDivElement>(null)
  useEffect(() => () => { request.current?.abort() }, [])
  useEffect(() => { if (failure) summary.current?.focus() }, [failure])
  useEffect(() => { if (!canDelete && !pending) setOpen(false) }, [canDelete, pending])
  if (!canDelete) return null
  const close = () => { if (!pending) { setOpen(false); setFailure(''); setUncertain(false) } }
  async function submit() {
    if (request.current || uncertain || !canDelete) return
    const controller = new AbortController()
    request.current = controller; setPending(true); setFailure('')
    try {
      await trashApi.delete(objectType, objectId, controller.signal)
      if (controller.signal.aborted) return
      // Navigate only after server confirmation; the removed detail cannot retain
      // its private data while all current query observers are reset.
      navigate('/trash', { replace: true, state: { trashMutation: 'deleted' } })
      await resetPrivateAfterTrash(cache)
    } catch (error) {
      if (controller.signal.aborted) return
      const unknownResult = !isApiError(error) || error.status === 0 || error.status >= 500
      setUncertain(unknownResult)
      setFailure(unknownResult ? 'Chưa thể xác nhận kết quả. Mở Thùng rác để kiểm tra trước khi thao tác lại.' : isApiError(error) ? error.message : 'Chưa thể chuyển vào Thùng rác.')
      if (isApiError(error) && [403, 404].includes(error.status)) onDenied?.()
    } finally { if (!controller.signal.aborted) { request.current = null; setPending(false) } }
  }
  return <>
    <Button variant="danger" icon={<TrashIcon />} onClick={() => setOpen(true)}>Xóa {trashTypeLabels[objectType].toLocaleLowerCase('vi-VN')}</Button>
    <Dialog open={open} onClose={close} busy={pending} title="Chuyển vào Thùng rác">
      {failure && <div ref={summary} className="form-summary" tabIndex={-1}><Alert kind="error">{failure}</Alert></div>}
      <p>Bạn muốn chuyển <strong>{title}</strong> vào Thùng rác?</p>
      <p>Dữ liệu và lịch sử được giữ lại. Bạn có thể khôi phục trong 30 ngày nếu còn đủ quyền và đối tượng cha khả dụng.</p>
      {objectType !== 'TASK' && <p>Các không gian hoặc công việc bên trong sẽ tạm không khả dụng. Những mục đã xóa riêng không tự được khôi phục cùng đối tượng cha.</p>}
      <p className="field__hint">Sau 30 ngày, mục này đến hạn xóa vĩnh viễn nếu đủ điều kiện bảo toàn dữ liệu.</p>
      <div className="work-actions">
        <Button variant="danger" busy={pending} disabled={uncertain} onClick={() => void submit()}>Xác nhận chuyển vào Thùng rác</Button>
        <Button variant="secondary" disabled={pending} onClick={close}>Hủy</Button>
        {uncertain && <Button variant="secondary" onClick={() => navigate('/trash')}>Mở Thùng rác</Button>}
      </div>
    </Dialog>
  </>
}
