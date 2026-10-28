import { useEffect, useRef, useState } from 'react'
import type { FormEvent, ReactNode } from 'react'
import { Link, Navigate } from 'react-router'
import { Brand } from '../components/brand'
import { PageHeader } from '../components/page'
import { Alert, Button, Card, FormField, Input } from '../components/ui'
import { useAuth } from '../features/auth/AuthProvider'
import { accountSecurityApi } from '../services/api/account-security'
import { isApiError } from '../services/api/client'
import { authApi } from '../services/api/queries'
import type { RegisterInput, User } from '../services/api/types'
import { SessionState } from './auth'

type Fields = Record<string, string>
const validEmail = (value: string) => value.length <= 254 && /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value.trim())
const validToken = (value: string) => value.length >= 32 && value.length <= 512 && !value.includes('\0') && !/[\s\uD800-\uDFFF]/u.test(value)

function useAccountAction() {
  const [busy, setBusy] = useState(false)
  const [failure, setFailure] = useState<{ message: string; fields: Fields } | null>(null)
  const [success, setSuccess] = useState('')
  const request = useRef<AbortController | null>(null)
  useEffect(() => () => { request.current?.abort() }, [])
  async function run<T>(fields: Fields, operation: (signal: AbortSignal) => Promise<T>, onSaved: (value: T) => void | Promise<void>, message: string) {
    if (request.current) return
    setSuccess('')
    if (Object.keys(fields).length) { setFailure({ message: 'Vui lòng kiểm tra thông tin bên dưới.', fields }); return }
    const controller = new AbortController()
    request.current = controller; setBusy(true); setFailure(null)
    try {
      const value = await operation(controller.signal)
      if (!controller.signal.aborted) {
        await onSaved(value)
        if (!controller.signal.aborted) setSuccess(message)
      }
    } catch (error) {
      if (!controller.signal.aborted) setFailure({ message: isApiError(error) ? error.message : 'Chưa thể hoàn tất. Vui lòng thử lại sau.', fields: isApiError(error) ? { ...error.fieldErrors } : {} })
    } finally {
      if (!controller.signal.aborted) { request.current = null; setBusy(false) }
    }
  }
  return { busy, failure, success, run }
}

function Feedback({ action, prefix, fields }: { action: ReturnType<typeof useAccountAction>; prefix: string; fields: string[] }) {
  const summary = useRef<HTMLDivElement>(null)
  useEffect(() => { if (action.failure) summary.current?.focus() }, [action.failure])
  return <>{action.failure && <div className="form-summary" tabIndex={-1} ref={summary}><Alert kind="error" title="Chưa thể hoàn tất"><p>{action.failure.message}</p><ul>{fields.filter((field) => action.failure?.fields[field]).map((field) => <li key={field}><a href={`#${prefix}${field}`} onClick={(event) => { event.preventDefault(); document.getElementById(`${prefix}${field}`)?.focus() }}>{action.failure?.fields[field]}</a></li>)}</ul></Alert></div>}{action.success && <Alert kind="success">{action.success}</Alert>}</>
}

function PublicAccountPage({ title, description, children }: { title: string; description: string; children: ReactNode }) {
  return <main className="status-page" id="main-content"><Brand /><Card><PageHeader title={title} description={description} /><div className="work-form">{children}<Link className="text-link" to="/login">Về đăng nhập</Link></div></Card></main>
}

export function RegisterPage() {
  const auth = useAuth()
  const action = useAccountAction()
  const [input, setInput] = useState<RegisterInput>({ email: '', username: '', first_name: '', last_name: '', password: '', password_confirm: '' })
  const [created, setCreated] = useState(false)
  const fields = ['email', 'username', 'first_name', 'last_name', 'password', 'password_confirm'] as const
  if (auth.status === 'checking' || auth.status === 'unavailable') return <SessionState />
  if (auth.status === 'authenticated') return <Navigate to="/account" replace />
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const errors: Fields = {}
    if (!validEmail(input.email)) errors.email = 'Vui lòng nhập địa chỉ email hợp lệ.'
    if (!input.username.trim() || input.username.length > 150) errors.username = 'Nhập tên đăng nhập từ 1 đến 150 ký tự.'
    if ((input.first_name?.length ?? 0) > 150) errors.first_name = 'Tên không được vượt quá 150 ký tự.'
    if ((input.last_name?.length ?? 0) > 150) errors.last_name = 'Họ không được vượt quá 150 ký tự.'
    if (input.password.length < 8 || input.password.length > 128) errors.password = 'Nhập mật khẩu từ 8 đến 128 ký tự; máy chủ sẽ kiểm tra độ an toàn.'
    if (input.password !== input.password_confirm) errors.password_confirm = 'Vui lòng nhập lại mật khẩu giống nhau.'
    void action.run(errors, (signal) => authApi.register({ ...input, email: input.email.trim(), username: input.username.trim() }, signal), () => { setCreated(true); setInput({ email: '', username: '', first_name: '', last_name: '', password: '', password_confirm: '' }) }, 'Tài khoản đã được tạo. Hãy đăng nhập để xác minh email và truy cập các tổ chức đã mời bạn.')
  }
  return <PublicAccountPage title="Đăng ký tài khoản" description="Tạo tài khoản cá nhân. Quyền tham gia tổ chức được cấp qua lời mời."><Feedback action={action} prefix="register-" fields={[...fields]} />{!created && <form className="work-form" noValidate onSubmit={submit} aria-label="Đăng ký tài khoản" aria-busy={action.busy || undefined}>
    {fields.map((field) => <FormField key={field} id={`register-${field}`} label={({ email: 'Email', username: 'Tên đăng nhập', first_name: 'Tên (không bắt buộc)', last_name: 'Họ (không bắt buộc)', password: 'Mật khẩu', password_confirm: 'Xác nhận mật khẩu' })[field]} error={action.failure?.fields[field]} hint={field === 'password' ? 'Từ 8 đến 128 ký tự. Tránh mật khẩu phổ biến, toàn số hoặc giống thông tin cá nhân.' : undefined}><Input type={field === 'email' ? 'email' : field.startsWith('password') ? 'password' : 'text'} name={field} value={input[field]} autoComplete={field === 'email' ? 'email' : field.startsWith('password') ? 'new-password' : field === 'username' ? 'username' : field === 'first_name' ? 'given-name' : 'family-name'} maxLength={field === 'email' ? 254 : field.startsWith('password') ? 128 : 150} required={!['first_name', 'last_name'].includes(field)} disabled={action.busy} onChange={(event) => setInput({ ...input, [field]: event.target.value })} /></FormField>)}
    <Button type="submit" busy={action.busy}>Tạo tài khoản</Button>
  </form>}</PublicAccountPage>
}

export function ForgotPasswordPage() {
  const action = useAccountAction()
  const [email, setEmail] = useState('')
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    void action.run(validEmail(email) ? {} : { email: 'Vui lòng nhập địa chỉ email hợp lệ.' }, (signal) => accountSecurityApi.requestReset(email.trim(), signal), () => { setEmail('') }, 'Nếu tài khoản đủ điều kiện tồn tại, yêu cầu đã được tiếp nhận. Kiểm tra email để lấy mã khôi phục; thông báo này không xác nhận việc gửi email thành công.')
  }
  return <PublicAccountPage title="Quên mật khẩu" description="Yêu cầu mã khôi phục cho tài khoản của bạn."><form className="work-form" noValidate onSubmit={submit} aria-label="Yêu cầu khôi phục mật khẩu" aria-busy={action.busy || undefined}><Feedback action={action} prefix="reset-request-" fields={['email']} /><FormField id="reset-request-email" label="Email" error={action.failure?.fields.email}><Input type="email" name="email" autoComplete="email" value={email} maxLength={254} disabled={action.busy} required onChange={(event) => setEmail(event.target.value)} /></FormField><Button type="submit" busy={action.busy}>Yêu cầu mã khôi phục</Button></form><Link className="text-link" to="/reset-password">Tôi đã có mã khôi phục</Link></PublicAccountPage>
}

export function ResetPasswordPage() {
  const auth = useAuth()
  const action = useAccountAction()
  const [input, setInput] = useState({ token: '', new_password: '', new_password_confirm: '' })
  const [finished, setFinished] = useState(false)
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const errors: Fields = {}
    if (!validToken(input.token)) errors.token = 'Dán đầy đủ mã khôi phục mới nhất từ email (32 đến 512 ký tự).'
    if (input.new_password.length < 8 || input.new_password.length > 128) errors.new_password = 'Nhập mật khẩu mới từ 8 đến 128 ký tự; máy chủ sẽ kiểm tra độ an toàn.'
    if (input.new_password !== input.new_password_confirm) errors.new_password_confirm = 'Vui lòng nhập lại mật khẩu mới giống nhau.'
    void action.run(errors, (signal) => accountSecurityApi.confirmReset(input, signal), async () => { setInput({ token: '', new_password: '', new_password_confirm: '' }); setFinished(true); await auth.revalidate() }, 'Mật khẩu đã được đặt lại. Hãy đăng nhập bằng mật khẩu mới; thao tác này không tự đăng nhập.')
  }
  return <PublicAccountPage title="Đặt lại mật khẩu" description="Dán mã được gửi qua email và chọn mật khẩu mới. Mã chỉ dùng được một lần."><Feedback action={action} prefix="reset-confirm-" fields={['token', 'new_password', 'new_password_confirm']} />{!finished && <form className="work-form" noValidate onSubmit={submit} aria-label="Đặt lại mật khẩu" aria-busy={action.busy || undefined}><FormField id="reset-confirm-token" label="Mã khôi phục" error={action.failure?.fields.token} hint="Cho phép dán mã. Mã được che và chỉ giữ trong biểu mẫu hiện tại."><Input type="password" name="token" autoComplete="off" spellCheck={false} value={input.token} maxLength={512} disabled={action.busy} required onChange={(event) => setInput({ ...input, token: event.target.value })} /></FormField>
    {(['new_password', 'new_password_confirm'] as const).map((field) => <FormField key={field} id={`reset-confirm-${field}`} label={field === 'new_password' ? 'Mật khẩu mới' : 'Xác nhận mật khẩu mới'} error={action.failure?.fields[field]} hint={field === 'new_password' ? 'Từ 8 đến 128 ký tự. Máy chủ vẫn kiểm tra mật khẩu phổ biến, toàn số hoặc tương tự thông tin cá nhân.' : undefined}><Input type="password" name={field} autoComplete="new-password" value={input[field]} maxLength={128} disabled={action.busy} required onChange={(event) => setInput({ ...input, [field]: event.target.value })} /></FormField>)}<Button type="submit" busy={action.busy}>Lưu mật khẩu mới</Button></form>}<Link className="text-link" to="/forgot-password">Yêu cầu mã mới</Link></PublicAccountPage>
}

function CurrentAccount({ user }: { user: User }) {
  const auth = useAuth()
  const request = useAccountAction()
  const confirm = useAccountAction()
  const [token, setToken] = useState('')
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    void confirm.run(validToken(token) ? {} : { token: 'Dán đầy đủ mã xác minh mới nhất từ email (32 đến 512 ký tự).' }, (signal) => accountSecurityApi.confirmVerification(token, signal), async () => { setToken(''); await auth.revalidate() }, 'Email đã được xác minh.')
  }
  return <><PageHeader title="Tài khoản" description="Thông tin và trạng thái xác minh của chính bạn." /><Card><h2>Địa chỉ email</h2><p className="preserve-text">{user.email}</p><p className="read-note">{user.email_verified ? 'Email đã được xác minh.' : 'Email chưa được xác minh. Bạn vẫn có thể sử dụng các quyền hiện có.'}</p>{!user.email_verified && <div className="work-form"><Feedback action={request} prefix="verify-request-" fields={[]} /><Button disabled={confirm.busy} busy={request.busy} onClick={() => { void request.run({}, (signal) => accountSecurityApi.requestVerification(signal), () => {}, 'Yêu cầu xác minh đã được tiếp nhận. Kiểm tra email và dùng mã mới nhất; yêu cầu lại sẽ vô hiệu mã cũ.') }}>Gửi mã xác minh</Button><form className="work-form" noValidate onSubmit={submit} aria-label="Xác nhận email" aria-busy={confirm.busy || undefined}><Feedback action={confirm} prefix="verify-" fields={['token']} /><FormField id="verify-token" label="Mã xác minh" error={confirm.failure?.fields.token} hint="Dán mã từ email dành cho tài khoản đang đăng nhập. Mã được che và không lưu vào đường dẫn."><Input type="password" name="token" autoComplete="off" spellCheck={false} maxLength={512} value={token} required disabled={confirm.busy || request.busy} onChange={(event) => setToken(event.target.value)} /></FormField><Button type="submit" busy={confirm.busy} disabled={request.busy}>Xác nhận email</Button></form></div>}</Card></>
}

export function AccountPage() {
  const { user } = useAuth()
  return user ? <CurrentAccount key={user.id} user={user} /> : <SessionState />
}
