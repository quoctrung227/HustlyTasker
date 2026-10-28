import { useEffect, useId, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { Alert, Button, Dialog } from '../../components/ui'
import { isApiError } from '../../services/api/client'
import { collaborationApi } from '../../services/api/collaboration'
import type { Deliverable } from '../../services/api/collaboration'

type Action = 'submit' | 'approve' | 'changes'
type Context = { profileId: string; workspaceId: string; taskId: string; active: boolean; onSaved: (value: Deliverable, action: Action) => void; onFailure: (error: unknown) => void }
const titles: Record<Action, string> = { submit: 'Nộp sản phẩm', approve: 'Phê duyệt sản phẩm', changes: 'Yêu cầu chỉnh sửa' }
const labels: Record<Action, string> = { submit: 'Đường dẫn hoặc nội dung sản phẩm', approve: 'Nhận xét', changes: 'Nội dung cần chỉnh sửa' }
const buttons: Record<Action, string> = { submit: 'Nộp sản phẩm', approve: 'Xác nhận phê duyệt', changes: 'Gửi yêu cầu chỉnh sửa' }

function ActionForm({ action, allowed, onSubmit, onSaved, onFailure, onClose, onPending }: {
  action: Action; allowed: boolean; onSubmit: (value: string, signal: AbortSignal) => Promise<Deliverable>
  onSaved: (value: Deliverable) => void; onFailure: (error: unknown) => void; onClose: () => void; onPending: (value: boolean) => void
}) {
  const id = useId()
  const [value, setValue] = useState('')
  const [pending, setPending] = useState(false)
  const [failure, setFailure] = useState<{ message: string; field?: string } | null>(null)
  const summary = useRef<HTMLDivElement>(null)
  const request = useRef<AbortController | null>(null)
  useEffect(() => () => { request.current?.abort() }, [])
  useEffect(() => { if (failure) summary.current?.focus() }, [failure])
  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (request.current || !allowed) return
    const clean = value.trim()
    const invalidUnicode = value.includes('\0') || Array.from(value).some((char) => char.length === 1 && /[\uD800-\uDFFF]/u.test(char))
    let field = ''
    if (action !== 'approve' && !clean) field = action === 'submit' ? 'Nhập đường dẫn hoặc nội dung sản phẩm.' : 'Nhập nội dung cần chỉnh sửa.'
    if (action === 'submit' && Array.from(clean).length > 500) field = 'Sản phẩm tối đa 500 ký tự.'
    if (invalidUnicode) field = 'Nội dung chứa ký tự không hợp lệ. Vui lòng kiểm tra lại.'
    if (field) { setFailure({ message: 'Thông tin chưa hợp lệ.', field }); return }
    const controller = new AbortController()
    request.current = controller; setPending(true); onPending(true); setFailure(null)
    let saved: Deliverable | undefined
    try { saved = await onSubmit(clean, controller.signal) } catch (error) {
      if (!controller.signal.aborted) {
        const apiError = isApiError(error) ? error : null
        setFailure({ message: apiError?.message ?? 'Chưa thể lưu thay đổi. Vui lòng thử lại sau.', field: apiError?.fieldErrors[action === 'submit' ? 'file_url' : 'comment'] })
        onFailure(error)
      }
    } finally { if (!controller.signal.aborted) { request.current = null; setPending(false); onPending(false) } }
    if (saved && !controller.signal.aborted) onSaved(saved)
  }
  return <form className="work-form" onSubmit={submit} noValidate aria-busy={pending || undefined}>
    {failure && <div className="form-summary" ref={summary} tabIndex={-1}><Alert kind="error" title="Chưa thể lưu thay đổi"><p>{failure.message}</p>{failure.field && <a href={`#${id}`} onClick={(event) => { event.preventDefault(); document.getElementById(id)?.focus() }}>{failure.field}</a>}</Alert></div>}
    {action === 'approve' && <p>Phê duyệt phiên bản này? Máy chủ sẽ kiểm tra lại quyền và trạng thái trước khi hoàn thành công việc.</p>}
    <div className={`field${failure?.field ? ' field--invalid' : ''}`}><label className="field__label" htmlFor={id}>{labels[action]}{action === 'approve' && <span className="field__hint"> (không bắt buộc)</span>}</label>
      <textarea id={id} className="input" rows={4} value={value} onChange={(event) => setValue(event.target.value)} disabled={pending} required={action !== 'approve'} maxLength={action === 'submit' ? 1000 : undefined} aria-invalid={failure?.field ? true : undefined} aria-describedby={`${id}-hint${failure?.field ? ` ${id}-error` : ''}`} />
      <p className="field__hint" id={`${id}-hint`}>{action === 'submit' ? `${Array.from(value.trim()).length} / 500 ký tự. Có thể nhập văn bản hoặc đường dẫn; không tải tệp lên.` : action === 'changes' ? 'Mô tả rõ những phần cần chỉnh sửa để người thực hiện có thể nộp lại.' : 'Nhận xét sẽ được lưu cùng quyết định đánh giá.'}</p>
      {failure?.field && <p className="field__error" id={`${id}-error`}>{failure.field}</p>}
    </div>
    {!allowed && <p className="read-note">Quyền hoặc trạng thái đã thay đổi. Đóng hộp thoại và kiểm tra thông tin mới trước khi tiếp tục.</p>}
    <div className="work-actions"><Button type="submit" busy={pending} disabled={!allowed}>{buttons[action]}</Button><Button variant="secondary" disabled={pending} onClick={onClose}>Hủy</Button></div>
  </form>
}

export function SubmitDeliverable({ canSubmit, ...context }: Context & { canSubmit: boolean }) {
  const [open, setOpen] = useState(false)
  const [pending, setPending] = useState(false)
  const allowed = context.active && canSubmit
  const close = () => { if (!pending) setOpen(false) }
  return <>{allowed && <Button onClick={() => setOpen(true)}>Nộp sản phẩm</Button>}
    {context.active && open && <Dialog open title={titles.submit} busy={pending} onClose={close}><ActionForm action="submit" allowed={allowed} onPending={setPending} onClose={close} onFailure={context.onFailure}
      onSubmit={(file_url, signal) => collaborationApi.submitDeliverable(context.profileId, context.workspaceId, context.taskId, { file_url }, signal)} onSaved={(saved) => { setOpen(false); context.onSaved(saved, 'submit') }} /></Dialog>}</>
}

export function ReviewDeliverable({ item, ...context }: Context & { item: Deliverable }) {
  const [action, setAction] = useState<'approve' | 'changes' | null>(null)
  const [pending, setPending] = useState(false)
  const allowed = context.active && (action === 'approve' ? item.can_approve : item.can_request_changes)
  const close = () => { if (!pending) setAction(null) }
  return <><div className="work-actions">{context.active && item.can_approve && <Button onClick={() => setAction('approve')}>Phê duyệt sản phẩm</Button>}{context.active && item.can_request_changes && <Button variant="secondary" onClick={() => setAction('changes')}>Yêu cầu chỉnh sửa</Button>}</div>
    {context.active && action && <Dialog open title={titles[action]} busy={pending} onClose={close}><ActionForm key={action} action={action} allowed={allowed} onPending={setPending} onClose={close} onFailure={context.onFailure}
      onSubmit={(comment, signal) => action === 'approve' ? collaborationApi.approveDeliverable(context.profileId, context.workspaceId, context.taskId, item.id, comment ? { comment } : {}, signal) : collaborationApi.requestDeliverableChanges(context.profileId, context.workspaceId, context.taskId, item.id, { comment }, signal)} onSaved={(saved) => { setAction(null); context.onSaved(saved, action) }} /></Dialog>}</>
}
