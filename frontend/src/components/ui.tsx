import { cloneElement, useEffect, useId, useRef } from 'react'
import type { ComponentProps, HTMLAttributes, InputHTMLAttributes, ReactElement, ReactNode } from 'react'
import { ArrowClockwise, ArrowLeft, ArrowRight, CheckCircle, CircleNotch, Info, Tray, WarningCircle, X } from '@phosphor-icons/react'
import { isApiError } from '../services/api/client'

function classes(...values: (string | undefined | false)[]) {
  return values.filter(Boolean).join(' ')
}

type ButtonProps = ComponentProps<'button'> & {
  variant?: 'primary' | 'secondary' | 'ghost' | 'danger'
  busy?: boolean
  icon?: ReactNode
}

export function Button({ variant = 'primary', busy = false, disabled, className, children, icon, type = 'button', ...props }: ButtonProps) {
  return (
    <button {...props} type={type} disabled={disabled || busy} aria-busy={busy || undefined} className={classes('button', `button--${variant}`, className)}>
      {busy ? <CircleNotch size={18} className="spinner" aria-hidden="true" /> : icon ? <span className="button__icon" aria-hidden="true">{icon}</span> : null}
      {children}
    </button>
  )
}

export function Input({ className, ...props }: ComponentProps<'input'>) {
  return <input {...props} className={classes('input', className)} />
}

export function Card({ className, ...props }: HTMLAttributes<HTMLDivElement>) {
  return <div {...props} className={classes('card', className)} />
}

export function Badge({ status, className }: { status: 'ACTIVE' | 'ARCHIVED'; className?: string }) {
  return (
    <span className={classes('badge', status === 'ACTIVE' ? 'badge--active' : 'badge--archived', className)}>
      <span className="badge__dot" aria-hidden="true" />
      {status === 'ACTIVE' ? 'Đang hoạt động' : 'Đã lưu trữ'}
    </span>
  )
}

export function Alert({ kind = 'info', title, children, className }: {
  kind?: 'error' | 'info' | 'success'; title?: string; children: ReactNode; className?: string
}) {
  const Icon = kind === 'error' ? WarningCircle : kind === 'success' ? CheckCircle : Info
  return (
    <div className={classes('alert', `alert--${kind}`, className)} role={kind === 'error' ? 'alert' : 'status'}>
      <Icon size={20} aria-hidden="true" />
      <div>{title && <p className="alert__title">{title}</p>}<div>{children}</div></div>
    </div>
  )
}

export function EmptyState({ title, description, action }: { title: string; description: string; action?: ReactNode }) {
  return (
    <div className="empty-state">
      <span className="empty-state__icon" aria-hidden="true"><Tray size={28} /></span>
      <h2>{title}</h2>
      <p>{description}</p>
      {action && <div className="empty-state__action">{action}</div>}
    </div>
  )
}

export function ErrorState({ error, onRetry }: { error: unknown; onRetry?: () => void }) {
  const apiError = isApiError(error) ? error : null
  const unavailable = apiError?.kind === 'not-found' || apiError?.kind === 'forbidden'
  const title = unavailable ? 'Nội dung không khả dụng' : 'Chưa thể tải nội dung'
  const message = apiError?.message ?? 'Kết nối đang gặp sự cố. Vui lòng thử lại sau.'
  return (
    <div className="error-state">
      <Alert kind="error" title={title}>{message}</Alert>
      {onRetry && <Button variant="secondary" onClick={onRetry} icon={<ArrowClockwise size={18} />}>Thử lại</Button>}
    </div>
  )
}

export function PageSkeleton({ label = 'Đang tải nội dung…' }: { label?: string }) {
  return (
    <div className="page-skeleton" role="status" aria-busy="true">
      <span className="sr-only">{label}</span>
      <div aria-hidden="true">
        <div className="skeleton skeleton--heading" />
        <div className="skeleton skeleton--text" />
        <div className="skeleton-grid">
          {[0, 1, 2].map((item) => <div className="skeleton skeleton--card" key={item} />)}
        </div>
      </div>
    </div>
  )
}

export function FormField({ id, label, error, hint, children }: {
  id: string; label: string; error?: string; hint?: string
  children: ReactElement<InputHTMLAttributes<HTMLInputElement>>
}) {
  const descriptions = [children.props['aria-describedby'], hint ? `${id}-hint` : undefined, error ? `${id}-error` : undefined].filter(Boolean).join(' ')
  return (
    <div className={classes('field', error && 'field--invalid')}>
      <label className="field__label" htmlFor={id}>{label}</label>
      {cloneElement(children, {
        id,
        'aria-invalid': error ? true : children.props['aria-invalid'],
        'aria-describedby': descriptions || undefined,
      })}
      {hint && <p className="field__hint" id={`${id}-hint`}>{hint}</p>}
      {error && <p className="field__error" id={`${id}-error`}>{error}</p>}
    </div>
  )
}

export function Dialog({ open, onClose, title, children, className, busy = false }: {
  open: boolean; onClose: () => void; title: string; children: ReactNode; className?: string; busy?: boolean
}) {
  const dialogRef = useRef<HTMLDialogElement>(null)
  const closeRequest = useRef(onClose)
  const titleId = useId()

  useEffect(() => { closeRequest.current = onClose }, [onClose])

  useEffect(() => {
    const dialog = dialogRef.current
    if (!open || !dialog) return

    const previouslyFocused = document.activeElement
    const previousOverflow = document.body.style.overflow
    const nativeClose = () => { if (!dialog.open) closeRequest.current() }
    dialog.addEventListener('close', nativeClose)
    document.body.style.overflow = 'hidden'
    if (!dialog.open) dialog.showModal()

    return () => {
      dialog.removeEventListener('close', nativeClose)
      if (dialog.open) dialog.close()
      document.body.style.overflow = previousOverflow
      if (previouslyFocused instanceof HTMLElement && previouslyFocused.isConnected) previouslyFocused.focus()
    }
  }, [open])

  return (
    <dialog ref={dialogRef} aria-labelledby={titleId} className={classes('dialog', className)} onCancel={(event) => {
      event.preventDefault()
      if (!busy) onClose()
    }}>
      <div className="dialog__header">
        <h2 id={titleId}>{title}</h2>
        <Button variant="ghost" className="icon-button" aria-label="Đóng hộp thoại" disabled={busy} onClick={onClose}><X size={20} aria-hidden="true" /></Button>
      </div>
      <div className="dialog__body">{children}</div>
    </dialog>
  )
}

export function Pagination({ page, count, onPageChange, pageSize = 20, disabled = false }: {
  page: number; count: number; onPageChange: (page: number) => void; pageSize?: number; disabled?: boolean
}) {
  if (count <= 0) return null
  const size = Number.isFinite(pageSize) && pageSize > 0 ? Math.floor(pageSize) : 20
  const pages = Math.max(1, Math.ceil(count / size))
  const current = Number.isFinite(page) ? Math.max(1, Math.min(Math.floor(page), pages)) : 1
  const number = new Intl.NumberFormat('vi-VN')
  const start = (current - 1) * size + 1
  const end = Math.min(current * size, count)

  return (
    <nav className="pagination" aria-label="Phân trang">
      <p className="pagination__summary">{number.format(start)}–{number.format(end)} trong {number.format(count)} kết quả</p>
      <div className="pagination__controls">
        <Button variant="secondary" onClick={() => onPageChange(current - 1)} disabled={disabled || current === 1} aria-label="Trang trước"><ArrowLeft size={18} aria-hidden="true" /></Button>
        <span className="pagination__page" aria-live="polite" aria-atomic="true">Trang {number.format(current)} / {number.format(pages)}</span>
        <Button variant="secondary" onClick={() => onPageChange(current + 1)} disabled={disabled || current === pages} aria-label="Trang sau"><ArrowRight size={18} aria-hidden="true" /></Button>
      </div>
    </nav>
  )
}
