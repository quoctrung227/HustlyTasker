import { useEffect, useId, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { Alert, Button, Dialog, FormField, Input } from '../../components/ui'
import { isApiError } from '../../services/api/client'
import type { Workspace } from '../../services/api/types'
import type { WorkspaceCreateInput, WorkspaceUpdateInput } from '../../services/api/work-management'
export type { WorkspaceCreateInput, WorkspaceUpdateInput } from '../../services/api/work-management'

type CommonFormProps = {
  onSaved: (workspace: Workspace) => void
  onCancel: () => void
  onPendingChange: (pending: boolean) => void
  onDenied?: () => void
}

type WorkspaceFormProps = CommonFormProps & (
  | { mode: 'create'; onSubmit: (input: WorkspaceCreateInput, signal?: AbortSignal) => Promise<Workspace> }
  | { mode: 'edit'; workspace: Workspace; onSubmit: (input: WorkspaceUpdateInput, signal?: AbortSignal) => Promise<Workspace> }
)

type FieldErrors = Partial<Record<'name' | 'description' | 'period', string>>

// Both forms submit only the fields explicitly accepted by the existing API.
export function WorkspaceForm(props: WorkspaceFormProps) {
  const id = useId()
  const [name, setName] = useState(props.mode === 'edit' ? props.workspace.name : '')
  const [description, setDescription] = useState(props.mode === 'edit' ? props.workspace.description ?? '' : '')
  const [month, setMonth] = useState('')
  const [pending, setPending] = useState(false)
  const [failure, setFailure] = useState<{ message: string; fields: FieldErrors } | null>(null)
  const summary = useRef<HTMLDivElement>(null)
  const request = useRef<AbortController | null>(null)
  const fieldIds = { name: `${id}-name`, description: `${id}-description`, period: `${id}-period` }

  useEffect(() => () => { request.current?.abort() }, [])
  useEffect(() => { if (failure) summary.current?.focus() }, [failure])

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (request.current) return
    const fields: FieldErrors = {}
    if (!name.trim() || name.trim().length > 255) fields.name = 'Nhập tên không gian từ 1 đến 255 ký tự.'
    if (props.mode === 'create' && !/^(?!0000)\d{4}-(0[1-9]|1[0-2])$/.test(month)) {
      fields.period = 'Chọn tháng làm việc hợp lệ.'
    }
    if (Object.keys(fields).length) {
      setFailure({ message: 'Vui lòng kiểm tra các thông tin bên dưới.', fields })
      return
    }

    const controller = new AbortController()
    request.current = controller
    setPending(true)
    props.onPendingChange(true)
    setFailure(null)
    let saved: Workspace | undefined
    try {
      const metadata = { name: name.trim(), description }
      saved = props.mode === 'create'
        ? await props.onSubmit({ ...metadata, period: `${month}-01` }, controller.signal)
        : await props.onSubmit(metadata, controller.signal)
    } catch (error) {
      if (!controller.signal.aborted) {
        const apiError = isApiError(error) ? error : null
        const errors: FieldErrors = {}
        for (const field of ['name', 'description', 'period'] as const) {
          if (apiError?.fieldErrors[field]) errors[field] = apiError.fieldErrors[field]
        }
        setFailure({ message: apiError?.message ?? 'Chưa thể lưu không gian. Vui lòng thử lại sau.', fields: errors })
        if (apiError?.kind === 'forbidden' || apiError?.status === 404) props.onDenied?.()
      }
    } finally {
      if (!controller.signal.aborted) {
        request.current = null
        setPending(false)
        props.onPendingChange(false)
      }
    }
    if (saved && !controller.signal.aborted) props.onSaved(saved)
  }

  return (
    <form className="work-form" onSubmit={submit} noValidate aria-busy={pending || undefined}>
      {failure && <div ref={summary} className="form-summary" tabIndex={-1}>
        <Alert kind="error" title="Chưa thể lưu không gian">
          <p>{failure.message}</p>
          {Object.keys(failure.fields).length > 0 && <ul>{Object.entries(failure.fields).map(([field, error]) => (
            <li key={field}><a href={`#${fieldIds[field as keyof FieldErrors]}`} onClick={(event) => {
              event.preventDefault()
              document.getElementById(fieldIds[field as keyof FieldErrors])?.focus()
            }}>{error}</a></li>
          ))}</ul>}
        </Alert>
      </div>}
      <FormField id={fieldIds.name} label="Tên không gian" error={failure?.fields.name} hint="Tối đa 255 ký tự.">
        <Input value={name} onChange={(event) => setName(event.target.value)} maxLength={255} required disabled={pending} autoComplete="off" />
      </FormField>
      <div className={`field${failure?.fields.description ? ' field--invalid' : ''}`}>
        <label className="field__label" htmlFor={fieldIds.description}>Mô tả</label>
        <textarea id={fieldIds.description} className="input" rows={4} value={description} onChange={(event) => setDescription(event.target.value)} disabled={pending}
          aria-invalid={failure?.fields.description ? true : undefined} aria-describedby={failure?.fields.description ? `${fieldIds.description}-error` : undefined} />
        {failure?.fields.description && <p id={`${fieldIds.description}-error`} className="field__error">{failure.fields.description}</p>}
      </div>
      {props.mode === 'create' ? <FormField id={fieldIds.period} label="Tháng làm việc" error={failure?.fields.period} hint="Mỗi tháng có một không gian trong tổ chức. Tháng không thể thay đổi sau khi tạo.">
        <Input type="month" min="0001-01" max="9999-12" value={month} onChange={(event) => setMonth(event.target.value)} required disabled={pending} />
      </FormField> : <p className="field__hint">Tháng làm việc không thể thay đổi sau khi tạo.</p>}
      <div className="work-actions">
        <Button type="submit" busy={pending}>{props.mode === 'create' ? 'Tạo không gian' : 'Lưu thay đổi'}</Button>
        <Button variant="secondary" disabled={pending} onClick={props.onCancel}>Hủy</Button>
      </div>
    </form>
  )
}

type WorkspaceCreateProps = {
  profileId: string
  canCreate?: boolean
  onCreate: (input: WorkspaceCreateInput, signal?: AbortSignal) => Promise<Workspace>
  onCreated?: (workspace: Workspace) => void
  onDenied?: () => void
}

export function WorkspaceCreate(props: WorkspaceCreateProps) {
  return <ScopedWorkspaceCreate key={props.profileId} {...props} />
}

function ScopedWorkspaceCreate({ profileId, canCreate = false, onCreate, onCreated, onDenied }: WorkspaceCreateProps) {
  const [open, setOpen] = useState(false)
  const [pending, setPending] = useState(false)
  const close = () => { if (!pending) setOpen(false) }
  useEffect(() => {
    if (!canCreate) { setOpen(false); setPending(false) }
  }, [canCreate])
  if (!canCreate || !profileId) return null

  return <>
    <Button onClick={() => setOpen(true)}>Tạo không gian</Button>
    {open && <Dialog open busy={pending} title="Tạo không gian làm việc" onClose={close}>
      <WorkspaceForm key={profileId} mode="create" onSubmit={onCreate} onPendingChange={setPending} onDenied={onDenied}
        onCancel={close} onSaved={(workspace) => { setOpen(false); onCreated?.(workspace) }} />
    </Dialog>}
  </>
}
