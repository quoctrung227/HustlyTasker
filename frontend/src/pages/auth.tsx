import { useEffect, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { Link, Navigate, useLocation } from 'react-router'
import { ArrowRightIcon, EyeIcon, EyeSlashIcon, LockKeyIcon, CheckIcon } from '@phosphor-icons/react'
import { Brand } from '../components/brand'
import { Alert, Button, Card, FormField, Input, PageSkeleton } from '../components/ui'
import { useAuth } from '../features/auth/AuthProvider'
import { isApiError } from '../services/api/client'

export function SessionState() {
  const { status, error, revalidate } = useAuth()
  useEffect(() => { document.title = 'Xác minh phiên · HustlyTasker' }, [])
  return <main className="session-page" id="main-content">
    <Brand />
    {status === 'checking' ? <PageSkeleton label="Đang kiểm tra phiên đăng nhập…" /> :
      <Card><h1>Chưa thể xác nhận phiên đăng nhập</h1><p>Dữ liệu riêng tư đã được ẩn. {isApiError(error) ? error.message : 'Hãy kiểm tra kết nối rồi thử lại.'}</p><Button onClick={() => void revalidate()}>Kiểm tra lại</Button></Card>}
  </main>
}

function destination(state: unknown): string {
  const from = state && typeof state === 'object' && 'from' in state ? state.from : null
  return typeof from === 'string' && from.startsWith('/') && !from.startsWith('//') && !from.startsWith('/login') && !from.includes('\\') ? from : '/dashboard'
}

export function LoginPage() {
  const auth = useAuth()
  const location = useLocation()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [visible, setVisible] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [fields, setFields] = useState<Record<string, string>>({})
  const summary = useRef<HTMLDivElement>(null)
  useEffect(() => {
    if (auth.status === 'anonymous') document.title = 'Đăng nhập · HustlyTasker'
  }, [auth.status])

  if (auth.status === 'authenticated') return <Navigate to={destination(location.state)} replace />
  if (auth.status === 'checking' || auth.status === 'unavailable') return <SessionState />

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const invalid: Record<string, string> = {}
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim())) invalid.email = 'Vui lòng nhập địa chỉ email hợp lệ.'
    if (!password || password.length > 128) invalid.password = 'Vui lòng nhập mật khẩu (tối đa 128 ký tự).'
    setFields(invalid)
    setError(null)
    if (Object.keys(invalid).length) {
      setError('Vui lòng kiểm tra thông tin đăng nhập.')
      window.requestAnimationFrame(() => summary.current?.focus())
      return
    }
    setBusy(true)
    try { await auth.signIn({ email: email.trim(), password }) }
    catch (failure) {
      setError(isApiError(failure) ? failure.message : 'Không thể đăng nhập. Vui lòng thử lại.')
      if (isApiError(failure)) setFields({ ...failure.fieldErrors })
      window.requestAnimationFrame(() => summary.current?.focus())
    } finally { setPassword(''); setBusy(false) }
  }

  return <div className="login-page">
    <a href="#login-form" className="skip-link">Đến biểu mẫu đăng nhập</a>
    <section className="login-story" aria-label="HustlyTasker">
      <Brand light />
      <div className="login-story__body"><p className="eyebrow">LÀM VIỆC CÙNG NHAU, TỐT HƠN MỖI NGÀY</p>
        <p className="login-story__headline">Ít phân tán.<br />Nhiều <span>kết nối.</span></p>
        <p>Đưa nhóm của bạn về cùng một không gian.<br />Rõ việc cần làm. Đồng lòng tiến về phía trước.</p>
        <div className="collaboration-art" aria-hidden="true"><div className="art-orbit" /><div className="art-card art-card--back" /><div className="art-card art-card--front"><span className="art-check"><CheckIcon /></span><span className="art-line" /><span className="art-line art-line--short" /><div className="art-avatars"><i /><i /><i /></div></div><span className="art-spark">+</span></div>
      </div>
      <p className="login-story__footer">Mỗi đóng góp đều tạo nên sự khác biệt.</p>
    </section>
    <main className="login-main" id="login-form">
      <div className="login-mobile-brand"><Brand /></div>
      <div className="login-form-wrap"><span className="login-symbol" aria-hidden="true"><ArrowRightIcon /></span>
        <p className="eyebrow">CHÀO MỪNG TRỞ LẠI</p><h1>Đăng nhập vào<br />không gian của bạn.</h1>
        <p className="login-description">Tiếp tục nơi cả nhóm đang chờ bạn.</p>
        <form onSubmit={(event) => void submit(event)} noValidate aria-label="Đăng nhập">
          {error && <div ref={summary} tabIndex={-1} className="form-summary"><Alert kind="error" title="Chưa thể đăng nhập">{error}{Object.keys(fields).length > 0 && <ul>{Object.entries(fields).map(([field, message]) => <li key={field}><a href={`#${field}`}>{message}</a></li>)}</ul>}</Alert></div>}
          <FormField id="email" label="Email" error={fields.email}><Input type="email" name="email" autoComplete="username" value={email} onChange={(event) => setEmail(event.target.value)} disabled={busy} placeholder="ban@congty.com" required /></FormField>
          <FormField id="password" label="Mật khẩu" error={fields.password}>
            <Input type={visible ? 'text' : 'password'} name="password" autoComplete="current-password" value={password} onChange={(event) => setPassword(event.target.value)} disabled={busy} maxLength={128} required />
          </FormField>
          <Button className="password-toggle" variant="ghost" onClick={() => setVisible(!visible)} aria-pressed={visible}>{visible ? <EyeSlashIcon aria-hidden="true" /> : <EyeIcon aria-hidden="true" />}{visible ? 'Ẩn mật khẩu' : 'Hiện mật khẩu'}</Button>
          <Button className="login-submit" type="submit" busy={busy}>Đăng nhập<ArrowRightIcon aria-hidden="true" /></Button>
        </form>
        <div className="work-actions"><Link className="text-link" to="/forgot-password">Quên mật khẩu?</Link><Link className="text-link" to="/register">Đăng ký tài khoản</Link></div>
        <p className="login-security"><LockKeyIcon aria-hidden="true" />Đăng nhập an toàn bằng tài khoản của bạn.</p>
      </div>
      <footer className="login-main__footer">HustlyTasker<span>Không gian cho những người cùng làm.</span></footer>
    </main>
  </div>
}
