import { useState } from 'react'
import { fireEvent, render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterAll, beforeAll, describe, expect, it, vi } from 'vitest'
import { ApiError } from '../services/api/client'
import { Alert, Badge, Button, Dialog, EmptyState, ErrorState, FormField, Input, PageSkeleton, Pagination } from './ui'

function ControlledDialog() {
  const [open, setOpen] = useState(false)
  return <><Button onClick={() => setOpen(true)}>Mở menu</Button><Dialog open={open} title="Điều hướng" onClose={() => setOpen(false)}><a href="/profiles">Tổ chức</a></Dialog></>
}

describe('semantic UI primitives', () => {
  it('buttons default to type=button and prevent repeat clicks while busy', async () => {
    const user = userEvent.setup()
    const clicked = vi.fn()
    const { rerender } = render(<Button busy onClick={clicked}>Đăng nhập</Button>)
    const button = screen.getByRole('button', { name: 'Đăng nhập' })
    expect(button).toHaveAttribute('type', 'button')
    expect(button).toHaveAttribute('aria-busy', 'true')
    expect(button).toBeDisabled()
    await user.click(button)
    expect(clicked).not.toHaveBeenCalled()
    rerender(<Button variant="secondary" onClick={clicked}>Đăng nhập</Button>)
    await user.click(button)
    expect(clicked).toHaveBeenCalledOnce()
    expect(button).toHaveClass('button--secondary')
  })

  it('retains native submit type and caller disabled state', () => {
    render(<Button type="submit" disabled>Lưu</Button>)
    expect(screen.getByRole('button', { name: 'Lưu' })).toHaveAttribute('type', 'submit')
    expect(screen.getByRole('button', { name: 'Lưu' })).toBeDisabled()
  })

  it('shows lifecycle meaning in text, rather than color alone', () => {
    render(<><Badge status="ACTIVE" /><Badge status="ARCHIVED" /></>)
    expect(screen.getByText('Đang hoạt động')).toHaveClass('badge--active')
    expect(screen.getByText('Đã lưu trữ')).toHaveClass('badge--archived')
  })

  it('announces errors and non-error feedback with appropriate roles', () => {
    render(<><Alert kind="error" title="Chưa thể lưu">Thử lại sau.</Alert><Alert kind="success">Đã hoàn tất.</Alert></>)
    expect(screen.getByRole('alert')).toHaveTextContent('Chưa thể lưu')
    expect(screen.getByRole('status')).toHaveTextContent('Đã hoàn tất.')
  })

  it('connects a field label, hint and inline error to its input', () => {
    render(<FormField id="email" label="Email" hint="Địa chỉ của bạn" error="Kiểm tra email"><Input type="email" autoComplete="email" /></FormField>)
    const input = screen.getByRole('textbox', { name: 'Email' })
    expect(input).toHaveAttribute('id', 'email')
    expect(input).toHaveAttribute('aria-invalid', 'true')
    expect(input).toHaveAttribute('aria-describedby', 'email-hint email-error')
    expect(input).toHaveAccessibleDescription('Địa chỉ của bạn Kiểm tra email')
    expect(input).toHaveAttribute('autocomplete', 'email')
  })

  it('retains an existing description and clears removed validation state', () => {
    const { rerender } = render(<FormField id="email" label="Email" error="Kiểm tra email"><Input aria-describedby="extra" /></FormField>)
    expect(screen.getByRole('textbox')).toHaveAttribute('aria-describedby', 'extra email-error')
    rerender(<FormField id="email" label="Email"><Input /></FormField>)
    expect(screen.getByRole('textbox')).not.toHaveAttribute('aria-invalid')
    expect(screen.getByRole('textbox')).not.toHaveAttribute('aria-describedby')
  })

  it('renders an honest empty state with an optional working action', async () => {
    const retry = vi.fn()
    render(<EmptyState title="Chưa có tổ chức" description="Các tổ chức được cấp quyền sẽ xuất hiện tại đây." action={<Button onClick={retry}>Tải lại</Button>} />)
    expect(screen.getByRole('heading', { name: 'Chưa có tổ chức' })).toBeInTheDocument()
    await userEvent.setup().click(screen.getByRole('button', { name: 'Tải lại' }))
    expect(retry).toHaveBeenCalledOnce()
  })

  it('never reflects unknown server or network exception details', () => {
    render(<ErrorState error={new Error('private stack trace or database details')} />)
    expect(screen.getByRole('alert')).toHaveTextContent('Kết nối đang gặp sự cố.')
    expect(screen.queryByText(/private stack/)).not.toBeInTheDocument()
  })

  it('uses centralized safe API feedback and offers retry', async () => {
    const retry = vi.fn()
    render(<ErrorState error={new ApiError(404, 'not-found', 'Không tìm thấy nội dung hoặc bạn không có quyền truy cập.')} onRetry={retry} />)
    expect(screen.getByRole('alert')).toHaveTextContent('Nội dung không khả dụng')
    await userEvent.setup().click(screen.getByRole('button', { name: 'Thử lại' }))
    expect(retry).toHaveBeenCalledOnce()
  })

  it('provides one screen-reader loading status and decorative placeholders', () => {
    render(<PageSkeleton label="Đang tải tổ chức…" />)
    const status = screen.getByRole('status')
    expect(status).toHaveTextContent('Đang tải tổ chức…')
    expect(status).toHaveAttribute('aria-busy', 'true')
    expect(status.querySelector('[aria-hidden="true"]')).not.toBeNull()
  })
})

describe('bounded pagination', () => {
  it('disables the previous action on the first page and requests the next page', async () => {
    const changed = vi.fn()
    render(<Pagination page={1} count={41} onPageChange={changed} />)
    expect(screen.getByRole('navigation', { name: 'Phân trang' })).toHaveTextContent('1–20 trong 41 kết quả')
    expect(screen.getByRole('button', { name: 'Trang trước' })).toBeDisabled()
    await userEvent.setup().click(screen.getByRole('button', { name: 'Trang sau' }))
    expect(changed).toHaveBeenCalledWith(2)
  })

  it('disables next on the last page and requests only a previous page', async () => {
    const changed = vi.fn()
    render(<Pagination page={3} count={41} onPageChange={changed} />)
    expect(screen.getByText('41–41 trong 41 kết quả')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Trang sau' })).toBeDisabled()
    await userEvent.setup().click(screen.getByRole('button', { name: 'Trang trước' }))
    expect(changed).toHaveBeenCalledWith(2)
  })

  it('does not show pagination for an empty response', () => {
    render(<Pagination page={1} count={0} onPageChange={vi.fn()} />)
    expect(screen.queryByRole('navigation')).not.toBeInTheDocument()
  })
})

// jsdom does not implement native dialog behavior. These mocks exercise the
// controlled lifecycle only; native focus trapping/ESC is verified in a browser.
describe('native dialog controlled lifecycle', () => {
  const showModalDescriptor = Object.getOwnPropertyDescriptor(HTMLDialogElement.prototype, 'showModal')
  const closeDescriptor = Object.getOwnPropertyDescriptor(HTMLDialogElement.prototype, 'close')

  beforeAll(() => {
    Object.defineProperty(HTMLDialogElement.prototype, 'showModal', { configurable: true, value(this: HTMLDialogElement) { this.open = true } })
    Object.defineProperty(HTMLDialogElement.prototype, 'close', { configurable: true, value(this: HTMLDialogElement) {
      this.open = false
      this.dispatchEvent(new Event('close'))
    } })
  })

  afterAll(() => {
    if (showModalDescriptor) Object.defineProperty(HTMLDialogElement.prototype, 'showModal', showModalDescriptor)
    else Reflect.deleteProperty(HTMLDialogElement.prototype, 'showModal')
    if (closeDescriptor) Object.defineProperty(HTMLDialogElement.prototype, 'close', closeDescriptor)
    else Reflect.deleteProperty(HTMLDialogElement.prototype, 'close')
  })

  it('associates a title, locks scrolling and restores focus on close', async () => {
    const previousOverflow = document.body.style.overflow
    render(<ControlledDialog />)
    const trigger = screen.getByRole('button', { name: 'Mở menu' })
    trigger.focus()
    await userEvent.setup().click(trigger)
    expect(screen.getByRole('dialog', { name: 'Điều hướng' })).toHaveAttribute('open')
    expect(document.body.style.overflow).toBe('hidden')
    await userEvent.setup().click(screen.getByRole('button', { name: 'Đóng hộp thoại' }))
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
    expect(document.body.style.overflow).toBe(previousOverflow)
    expect(trigger).toHaveFocus()
  })

  it('handles a cancel request through the controlled close path', async () => {
    render(<ControlledDialog />)
    await userEvent.setup().click(screen.getByRole('button', { name: 'Mở menu' }))
    fireEvent(screen.getByRole('dialog'), new Event('cancel', { bubbles: true, cancelable: true }))
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })
})
