export type ApiErrorKind =
  | 'validation'
  | 'authentication'
  | 'forbidden'
  | 'csrf'
  | 'not-found'
  | 'conflict'
  | 'throttled'
  | 'server'
  | 'network'
  | 'invalid-response'

export class ApiError extends Error {
  readonly status: number
  readonly kind: ApiErrorKind
  readonly fieldErrors: Readonly<Record<string, string>>
  readonly retryAfterSeconds: number | null

  constructor(
    status: number,
    kind: ApiErrorKind,
    message: string,
    fieldErrors: Readonly<Record<string, string>> = {},
    retryAfterSeconds: number | null = null,
  ) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.kind = kind
    this.fieldErrors = fieldErrors
    this.retryAfterSeconds = retryAfterSeconds
  }
}

export function isApiError(error: unknown): error is ApiError {
  return error instanceof ApiError
}

export function invalidResponse(): ApiError {
  return new ApiError(
    0,
    'invalid-response',
    'Dữ liệu phản hồi chưa hợp lệ. Vui lòng thử lại.',
  )
}

export interface ApiRequestOptions {
  method?: 'GET' | 'OPTIONS' | 'POST' | 'PATCH' | 'DELETE'
  body?: unknown
  signal?: AbortSignal
  /** Only tenant-data requests use this; auth/me never calls back recursively. */
  protected?: boolean
}

type ForbiddenHandler = (() => void | Promise<void>) | null

function record(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
}

function apiPath(path: string): string {
  // A fixed synthetic origin makes this validation usable in browsers and tests.
  // The result always stays relative to our own origin and under /api/.
  if (path.includes('\\') || path.startsWith('//')) {
    throw new TypeError('Only same-origin API paths are allowed.')
  }
  const url = new URL(path, 'https://frontend.invalid/api/')
  if (
    url.origin !== 'https://frontend.invalid' ||
    !url.pathname.startsWith('/api/') ||
    url.hash ||
    url.username ||
    url.password
  ) {
    throw new TypeError('Only same-origin API paths are allowed.')
  }
  return `${url.pathname}${url.search}`
}

function safeFieldErrors(payload: unknown): Record<string, string> {
  if (!record(payload)) return {}
  const fields: Record<string, string> = {}
  // No raw server values, unknown keys, email identities, or HTML enter UI errors.
  if ('email' in payload) fields.email = 'Vui lòng nhập địa chỉ email hợp lệ.'
  if ('password' in payload) fields.password = 'Vui lòng kiểm tra mật khẩu.'
  const managementFields: Record<string, string> = {
    username: 'Tên đăng nhập chưa hợp lệ hoặc không khả dụng. Vui lòng kiểm tra lại.',
    first_name: 'Tên không được vượt quá 150 ký tự.',
    last_name: 'Họ không được vượt quá 150 ký tự.',
    password_confirm: 'Vui lòng nhập lại mật khẩu giống nhau.',
    new_password: 'Mật khẩu mới chưa đạt chính sách bảo mật. Vui lòng chọn mật khẩu khác.',
    new_password_confirm: 'Vui lòng nhập lại mật khẩu mới giống nhau.',
    token: 'Mã không hợp lệ hoặc không còn sử dụng được. Hãy kiểm tra mã mới nhất.',
    content: 'Nhập bình luận hợp lệ từ 1 đến 4.000 ký tự, không chứa ký tự rỗng hoặc Unicode không hợp lệ.',
    file_url: 'Vui lòng kiểm tra thông tin sản phẩm đã nộp (tối đa 500 ký tự).',
    comment: 'Vui lòng kiểm tra nội dung nhận xét; yêu cầu chỉnh sửa cần có lý do.',
    name: 'Vui lòng nhập tên hợp lệ (tối đa 255 ký tự).',
    description: 'Vui lòng kiểm tra nội dung mô tả.',
    period: 'Kỳ làm việc phải là ngày đầu tháng và chưa được sử dụng.',
    title: 'Vui lòng nhập tiêu đề hợp lệ (tối đa 255 ký tự).',
    deadline: 'Vui lòng nhập thời hạn hợp lệ và kiểm tra múi giờ.',
    priority: 'Vui lòng chọn mức ưu tiên được hỗ trợ.',
    parent_id: 'Quan hệ cha/con phải cùng không gian, không có vòng lặp và tối đa 3 cấp con.',
    target_profile_membership_id: 'Thành viên này chưa đủ điều kiện nhận việc. Hãy tải lại danh sách và chọn Editor hợp lệ.',
  }
  for (const [field, message] of Object.entries(managementFields)) {
    if (field in payload) fields[field] = message
  }
  // Django model validation uses `parent`; the API input control is parent_id.
  if ('parent' in payload) fields.parent_id = managementFields.parent_id ?? ''
  return fields
}

function errorFor(response: Response, payload: unknown, unsafe: boolean): ApiError {
  const detail = record(payload) && typeof payload.detail === 'string' ? payload.detail : ''
  const csrf = response.status === 403 && unsafe && (
    !response.headers.get('content-type')?.includes('application/json') ||
    /^CSRF (Failed|verification failed)/i.test(detail)
  )
  if (csrf) {
    return new ApiError(403, 'csrf', 'Phiên bảo mật đã thay đổi. Vui lòng thử lại thao tác.')
  }
  switch (response.status) {
    case 400:
      return new ApiError(400, 'validation', 'Thông tin chưa hợp lệ. Vui lòng kiểm tra lại.', safeFieldErrors(payload))
    case 401:
      return new ApiError(401, 'authentication', 'Vui lòng đăng nhập lại để tiếp tục.')
    case 403:
      return new ApiError(403, 'forbidden', 'Bạn không có quyền thực hiện thao tác này.')
    case 404:
      return new ApiError(404, 'not-found', 'Không tìm thấy nội dung hoặc bạn không có quyền truy cập.')
    case 409:
      return new ApiError(409, 'conflict', 'Dữ liệu đã thay đổi. Vui lòng tải lại trước khi tiếp tục.')
    case 429: {
      const value = response.headers.get('retry-after')
      const seconds = value && /^\d+$/.test(value) ? Number(value) : null
      return new ApiError(429, 'throttled', 'Bạn đã thao tác quá nhanh. Vui lòng thử lại sau.', {},
        seconds !== null && Number.isSafeInteger(seconds) ? seconds : null)
    }
    default:
      return new ApiError(response.status, 'server', 'Không thể xử lý yêu cầu lúc này. Vui lòng thử lại sau.')
  }
}

function throwIfAborted(signal?: AbortSignal): void {
  if (signal?.aborted) throw new DOMException('The operation was aborted.', 'AbortError')
}

export class ApiClient {
  private csrfToken: string | null = null
  private csrfRequest: Promise<string> | null = null
  private csrfGeneration = 0
  private forbiddenHandler: ForbiddenHandler = null

  setForbiddenHandler(handler: ForbiddenHandler): void {
    this.forbiddenHandler = handler
  }

  clearCsrf(): void {
    this.csrfGeneration += 1
    this.csrfToken = null
    this.csrfRequest = null
  }

  async initializeCsrf(options: { force?: boolean } = {}): Promise<string> {
    if (options.force) this.clearCsrf()
    if (this.csrfToken) return this.csrfToken
    if (this.csrfRequest) return this.csrfRequest
    const generation = this.csrfGeneration
    const pending = this.fetchJson('auth/csrf/', { method: 'GET' }).then((payload: unknown) => {
      if (!record(payload) || typeof payload.csrf_token !== 'string' || !/^[A-Za-z0-9]{64}$/.test(payload.csrf_token)) {
        throw invalidResponse()
      }
      // A response initiated before login/logout must not repopulate a rotated token.
      if (this.csrfGeneration !== generation) throw invalidResponse()
      this.csrfToken = payload.csrf_token
      return payload.csrf_token
    }).finally(() => {
      if (this.csrfRequest === pending) this.csrfRequest = null
    })
    this.csrfRequest = pending
    return pending
  }

  async request<T>(path: string, options: ApiRequestOptions = {}): Promise<T> {
    const normalizedPath = apiPath(path)
    const method = options.method ?? 'GET'
    const unsafe = method !== 'GET' && method !== 'OPTIONS'
    throwIfAborted(options.signal)
    const headers: Record<string, string> = { Accept: 'application/json' }
    if (unsafe) {
      headers['X-CSRFToken'] = await this.initializeCsrf()
      headers['Content-Type'] = 'application/json'
      throwIfAborted(options.signal)
    }
    try {
      return await this.fetchJson(normalizedPath, { ...options, method }, headers) as T
    } catch (error) {
      throwIfAborted(options.signal)
      if (error instanceof ApiError) {
        if (error.kind === 'csrf') this.clearCsrf()
        if ((error.status === 401 || error.status === 403) && error.kind !== 'csrf' && options.protected) {
          // A tenant 403 is not proof of logout. The auth owner revalidates /me.
          try { await this.forbiddenHandler?.() } catch { /* Preserve the original safe error. */ }
        }
      }
      throw error
    }
  }

  private async fetchJson(
    path: string,
    options: ApiRequestOptions,
    headers: Record<string, string> = { Accept: 'application/json' },
  ): Promise<unknown> {
    let response: Response
    try {
      response = await fetch(apiPath(path), {
        method: options.method ?? 'GET',
        headers,
        credentials: 'same-origin',
        cache: 'no-store',
        redirect: 'error',
        signal: options.signal,
        ...(options.body === undefined ? {} : { body: JSON.stringify(options.body) }),
      })
    } catch (error) {
      if (error instanceof DOMException && error.name === 'AbortError') throw error
      if (options.signal?.aborted) throw new DOMException('The operation was aborted.', 'AbortError')
      throw new ApiError(0, 'network', 'Không thể kết nối đến máy chủ. Vui lòng kiểm tra kết nối và thử lại.')
    }
    throwIfAborted(options.signal)
    if (response.ok && response.status === 204) return undefined
    let payload: unknown
    if (response.headers.get('content-type')?.includes('application/json')) {
      try { payload = await response.json() } catch {
        if (response.ok) throw invalidResponse()
      }
    }
    throwIfAborted(options.signal)
    const method = options.method ?? 'GET'
    if (!response.ok) throw errorFor(response, payload, method !== 'GET' && method !== 'OPTIONS')
    if (payload === undefined) throw invalidResponse()
    return payload
  }
}

export const apiClient = new ApiClient()
