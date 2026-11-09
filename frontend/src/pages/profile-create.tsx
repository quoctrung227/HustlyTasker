import { useEffect, useId, useRef, useState } from 'react'
import type { FormEvent } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { Link, useNavigate } from 'react-router'
import { PageHeader } from '../components/page'
import { Alert, Button, Card, FormField, Input } from '../components/ui'
import { isApiError } from '../services/api/client'
import { queryKeys, tenantApi } from '../services/api/queries'
import { useAuth } from '../features/auth/AuthProvider'

export function CreateProfilePage() {
  const { user } = useAuth()
  // Quiet identity revalidation can keep the route mounted. Bind the draft
  // and request lifetime to the current user, not just the URL/component.
  return <ProfileCreateForm key={user?.id || ''} />
}

function ProfileCreateForm() {
  const cache = useQueryClient()
  const navigate = useNavigate()
  const nameId = useId()
  const [name, setName] = useState('')
  const [pending, setPending] = useState(false)
  const [failure, setFailure] = useState<{ message: string; name?: string } | null>(null)
  const request = useRef<AbortController | null>(null)
  const summary = useRef<HTMLDivElement>(null)
  useEffect(() => () => { request.current?.abort() }, [])
  useEffect(() => { if (failure) summary.current?.focus() }, [failure])

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (request.current) return
    const normalized = name.trim()
    if (!normalized || Array.from(normalized).length > 255 || normalized.includes('\0') || /[\uD800-\uDFFF]/u.test(normalized)) {
      setFailure({ message: 'Vui lòng kiểm tra tên tổ chức.', name: 'Nhập tên tổ chức từ 1 đến 255 ký tự, không chứa ký tự rỗng hoặc Unicode không hợp lệ.' })
      return
    }
    const controller = new AbortController()
    request.current = controller
    setPending(true)
    setFailure(null)
    try {
      const profile = await tenantApi.createProfile({ name: normalized }, controller.signal)
      if (controller.signal.aborted) return
      cache.setQueryData(queryKeys.profile(profile.id), profile)
      // Profile pages share a root with tenant detail keys. Invalidate only list
      // pages; do not fabricate pagination counts or refetch unrelated tenants.
      void cache.invalidateQueries({ predicate: ({ queryKey }) => queryKey[0] === 'profiles' && typeof queryKey[1] === 'number' })
      // The URL is the existing active Profile authority; no parallel store.
      navigate(`/profiles/${profile.id}/workspaces`, { replace: true, state: { profileCreated: profile.id } })
    } catch (error) {
      if (!controller.signal.aborted) {
        const apiError = isApiError(error) ? error : null
        setFailure({ message: apiError?.message ?? 'Chưa thể tạo tổ chức. Vui lòng thử lại sau.',
          name: apiError?.fieldErrors.name })
      }
    } finally {
      if (!controller.signal.aborted) { request.current = null; setPending(false) }
    }
  }

  return <>
    <PageHeader eyebrow="BẮT ĐẦU CÙNG NHÓM" title="Tạo tổ chức mới"
      description="Tổ chức đại diện cho công ty hoặc nhóm làm việc của bạn."
      back={{ to: '/profiles', label: 'Tổ chức' }} />
    <Card className="profile-create-card">
      <form className="work-form" onSubmit={submit} noValidate aria-label="Tạo tổ chức mới" aria-busy={pending || undefined}>
        <p>Bạn sẽ trở thành Chủ sở hữu của tổ chức mới. Sau đó, bạn có thể tạo không gian làm việc theo tháng.</p>
        {failure && <div className="form-summary" tabIndex={-1} ref={summary}>
          <Alert kind="error" title="Chưa thể tạo tổ chức"><p>{failure.message}</p>
            {failure.name && <ul><li><a href={`#${nameId}`} onClick={(event) => { event.preventDefault(); document.getElementById(nameId)?.focus() }}>{failure.name}</a></li></ul>}
          </Alert>
        </div>}
        <FormField id={nameId} label="Tên tổ chức *" hint="Bắt buộc. Từ 1 đến 255 ký tự." error={failure?.name}>
          <Input name="name" autoComplete="organization" value={name} onChange={(event) => setName(event.target.value)} required disabled={pending} />
        </FormField>
        <div className="work-actions">
          <Button type="submit" busy={pending}>Tạo tổ chức</Button>
          {pending ? <Button variant="secondary" disabled>Hủy</Button> : <Link className="button button--secondary" to="/profiles">Hủy</Link>}
        </div>
      </form>
    </Card>
  </>
}
