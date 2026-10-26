import { useEffect, useRef } from 'react'
import type { ReactNode } from 'react'
import { Link } from 'react-router'
import { ArrowLeftIcon } from '@phosphor-icons/react'

export function PageHeader({ eyebrow, title, description, action, back }: {
  eyebrow?: string; title: string; description?: string; action?: ReactNode; back?: { to: string; label: string }
}) {
  const heading = useRef<HTMLHeadingElement>(null)
  useEffect(() => {
    document.title = `${title} · HustlyTasker`
    heading.current?.focus({ preventScroll: true })
  }, [title])
  return <header className="page-header">
    <div>
      {back && <Link className="back-link" to={back.to}><ArrowLeftIcon aria-hidden="true" />{back.label}</Link>}
      {eyebrow && <p className="eyebrow">{eyebrow}</p>}
      <h1 ref={heading} tabIndex={-1}>{title}</h1>
      {description && <p className="page-description">{description}</p>}
    </div>
    {action && <div className="page-header__action">{action}</div>}
  </header>
}

export function dateLabel(value: string) {
  return new Intl.DateTimeFormat('vi-VN', { dateStyle: 'medium' }).format(new Date(value))
}

export function periodLabel(value: string | null) {
  if (!value) return 'Chưa có kỳ làm việc'
  return new Intl.DateTimeFormat('vi-VN', { month: 'long', year: 'numeric', timeZone: 'UTC' })
    .format(new Date(`${value}T00:00:00Z`))
}
