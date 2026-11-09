/** Mocked wire/validation tests; real Django/PostgreSQL browser acceptance is separate. */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiError, apiClient } from './client'
import { feedbackAnalysisApi, feedbackAnalysisKeys, validateFeedbackAnalysis, validateFeedbackFocus, validateFeedbackInput } from './feedback-analysis'
import type { FeedbackAnalysisResult, FeedbackSelection } from './feedback-analysis'

const profileId = '00000000-0000-4000-8000-000000000701'
const workspaceId = '00000000-0000-4000-8000-000000000702'
const taskId = '00000000-0000-4000-8000-000000000703'
const reviewId = '00000000-0000-4000-8000-000000000704'
const commentId = '00000000-0000-4000-8000-000000000705'
const otherId = '00000000-0000-4000-8000-000000000706'
const path = `/api/v1/profiles/${profileId}/workspaces/${workspaceId}/tasks/${taskId}/ai/feedback-analysis/`
const selected: FeedbackSelection[] = [{ kind: 'review', id: reviewId }, { kind: 'comment', id: commentId }]
const json = (body: unknown, status = 200, headers: Record<string, string> = {}) =>
  new Response(JSON.stringify(body), { status, headers: { 'content-type': 'application/json', ...headers } })
const result = (sources = selected): FeedbackAnalysisResult => ({
  contract_version: 'ai.v1', status: 'READY', mode: 'fixture_demo', generated_by_ai: false,
  persisted: false, fixture_version: 'fixture.v1',
  sources: sources.map((source, index) => ({ ref: `S${index + 1}`, ...source })),
  payload: {
    contract_version: 'ai.feedback.v1', summary: 'Ví dụ synthetic: kiểm tra độ tương phản phụ đề.',
    issues: [{ category: 'TECHNICAL', description: 'Ví dụ về khả năng đọc.', source_refs: ['S1'] }],
    suggested_actions: [{ action: 'Kiểm tra tương phản phụ đề.', priority: 'MEDIUM', rationale: 'Gợi ý synthetic cố định.', source_refs: ['S1'] }],
    uncertainty: 'Không phân tích nội dung nguồn bằng model; chỉ fixture synthetic.',
    warnings: ['Demo fixture — không gọi AI.'],
  },
  usage: { input_tokens: 0, billable_output_tokens: 0, cost_usd: '0.000000', status: 'fixture_zero' },
})
function firstIssue(value: FeedbackAnalysisResult) {
  const item = value.payload.issues[0]
  if (!item) throw new Error('Missing synthetic test issue')
  return item
}
function firstAction(value: FeedbackAnalysisResult) {
  const item = value.payload.suggested_actions[0]
  if (!item) throw new Error('Missing synthetic test action')
  return item
}
function at<T>(values: T[], index = 0): T {
  const item = values[index]
  if (item === undefined) throw new Error('Missing synthetic test item')
  return item
}

beforeEach(() => { apiClient.clearCsrf(); apiClient.setForbiddenHandler(null) })
afterEach(() => { apiClient.clearCsrf(); apiClient.setForbiddenHandler(null); vi.unstubAllGlobals() })

describe('stateless Feedback Analyzer strict contracts', () => {
  it('accepts actual fixture provenance, manifest and payload without inventing persistence', () => {
    expect(validateFeedbackAnalysis(result(), selected)).toEqual(result())
    expect(validateFeedbackInput({ sources: selected, focus: 'Ưu tiên phụ đề.' })).toEqual({ sources: selected, focus: 'Ưu tiên phụ đề.' })
    expect(validateFeedbackInput({ sources: selected })).toEqual({ sources: selected })
  })
  it('clones the request and normalizes UUIDs without mutating caller input', () => {
    const input = { sources: [{ kind: 'review', id: 'ABCDEF00-0000-4000-8000-000000000704' }], focus: '' }
    const saved = validateFeedbackInput(input)
    at(input.sources).id = otherId
    expect(saved.sources).toEqual([{ kind: 'review', id: 'abcdef00-0000-4000-8000-000000000704' }])
    expect(saved.focus).toBe('')
  })
  it('allows one or twenty source pairs, including the same UUID in distinct source kinds', () => {
    const twenty: FeedbackSelection[] = Array.from({ length: 20 }, (_, index) => ({ kind: 'review', id: `00000000-0000-4000-8000-${String(index + 1).padStart(12, '0')}` }))
    for (const sources of [[at(selected)], twenty, [{ kind: 'review' as const, id: reviewId }, { kind: 'comment' as const, id: reviewId }]]) {
      expect(validateFeedbackInput({ sources }).sources).toHaveLength(sources.length)
      expect(validateFeedbackAnalysis(result(sources), sources).sources).toHaveLength(sources.length)
    }
  })
  it.each([
    null, true, 'raw feedback', [], {}, { sources: [] }, { sources: null }, { sources: 'S1' },
    { sources: Array.from({ length: 21 }, () => selected[0]) },
    { sources: [selected[0], selected[0]] }, { sources: [{ kind: 'review', id: 'not-a-uuid' }] },
    { sources: [{ kind: 'deliverable', id: reviewId }] }, { sources: [{ kind: 'review', id: 1 }] },
    { sources: [{ kind: 'review', id: null }] }, { sources: [{ kind: 1, id: reviewId }] },
    { sources: [{ kind: 'review', id: reviewId, content: 'Untrusted raw feedback' }] },
    { sources: selected, provider: 'live' }, { sources: selected, workspace_id: otherId },
    { sources: selected, role: 'ADMIN' }, { sources: selected, raw_feedback: 'private' },
    { sources: selected, confirmed: true }, { sources: selected, status: 'COMPLETED' },
  ])('rejects invalid/mutation/identity input without coercion: %j', (input) => {
    expect(() => validateFeedbackInput(input)).toThrow(ApiError)
  })
  it('rejects duplicate source identity despite UUID case changes', () => {
    expect(() => validateFeedbackInput({ sources: [
      { kind: 'review', id: 'ABCDEF00-0000-4000-8000-000000000704' },
      { kind: 'review', id: 'abcdef00-0000-4000-8000-000000000704' },
    ] })).toThrow(ApiError)
  })
  it.each([null, true, 1, [], {}, 'x'.repeat(1001), 'nul\0text', '\uD800'])('rejects invalid focus without reflecting text: %j', (focus) => {
    expect(validateFeedbackFocus(focus)).toBe(false)
    expect(() => validateFeedbackInput({ sources: selected, focus })).toThrow(ApiError)
  })
  it('counts Unicode codepoints, permits empty focus, and preserves whitespace per backend contract', () => {
    for (const focus of ['', ' ', '😀'.repeat(1000)]) {
      expect(validateFeedbackFocus(focus)).toBe(true)
      expect(validateFeedbackInput({ sources: selected, focus }).focus).toBe(focus)
    }
    expect(validateFeedbackFocus('😀'.repeat(1001))).toBe(false)
  })
  it.each([
    (value: FeedbackAnalysisResult) => { Object.assign(value, { generated_by_ai: true }) },
    (value: FeedbackAnalysisResult) => { Object.assign(value, { persisted: true }) },
    (value: FeedbackAnalysisResult) => { Object.assign(value, { mode: 'live_private' }) },
    (value: FeedbackAnalysisResult) => { Object.assign(value, { status: 'CONFIRMED' }) },
    (value: FeedbackAnalysisResult) => { Object.assign(value, { contract_version: 'ai.v2' }) },
    (value: FeedbackAnalysisResult) => { Object.assign(value, { fixture_version: 'fixture.v2' }) },
    (value: FeedbackAnalysisResult) => { Object.assign(value, { proposal_id: otherId }) },
    (value: FeedbackAnalysisResult) => { Object.assign(value, { created_tasks: { item_1: otherId } }) },
    (value: FeedbackAnalysisResult) => { Object.assign(value, { raw_feedback: 'SYNTHETIC_PRIVATE_TEXT' }) },
    (value: FeedbackAnalysisResult) => { Object.assign(value.usage, { input_tokens: 12 }) },
    (value: FeedbackAnalysisResult) => { Object.assign(value.usage, { billable_output_tokens: 12 }) },
    (value: FeedbackAnalysisResult) => { Object.assign(value.usage, { cost_usd: '0.10' }) },
    (value: FeedbackAnalysisResult) => { Object.assign(value.usage, { status: 'charged' }) },
    (value: FeedbackAnalysisResult) => { Object.assign(value.usage, { provider_request: 'private' }) },
    (value: FeedbackAnalysisResult) => { value.sources.reverse() },
    (value: FeedbackAnalysisResult) => { at(value.sources).id = otherId },
    (value: FeedbackAnalysisResult) => { at(value.sources).kind = 'comment' },
    (value: FeedbackAnalysisResult) => { at(value.sources).ref = 'S99' },
    (value: FeedbackAnalysisResult) => { at(value.sources, 1).ref = 'S1' },
    (value: FeedbackAnalysisResult) => { Object.assign(at(value.sources), { content: 'private' }) },
    (value: FeedbackAnalysisResult) => { value.sources.pop() },
    (value: FeedbackAnalysisResult) => { Object.assign(value.payload, { contract_version: 'ai.task-plan.v1' }) },
    (value: FeedbackAnalysisResult) => { Object.assign(value.payload, { confidence: 99 }) },
    (value: FeedbackAnalysisResult) => { value.payload.summary = '' },
    (value: FeedbackAnalysisResult) => { value.payload.summary = ' ' },
    (value: FeedbackAnalysisResult) => { value.payload.summary = 'x'.repeat(1601) },
    (value: FeedbackAnalysisResult) => { value.payload.summary = 'bad\0text' },
    (value: FeedbackAnalysisResult) => { value.payload.summary = '\uD800' },
    (value: FeedbackAnalysisResult) => { value.payload.uncertainty = 'x'.repeat(601) },
    (value: FeedbackAnalysisResult) => { value.payload.warnings = ['x'.repeat(301)] },
    (value: FeedbackAnalysisResult) => { value.payload.warnings = Array.from({ length: 11 }, () => 'extra') },
    (value: FeedbackAnalysisResult) => { value.payload.issues = Array.from({ length: 11 }, () => ({ ...firstIssue(value) })) },
    (value: FeedbackAnalysisResult) => { firstIssue(value).description = ' ' },
    (value: FeedbackAnalysisResult) => { firstIssue(value).description = 'x'.repeat(501) },
    (value: FeedbackAnalysisResult) => { Object.assign(firstIssue(value), { category: 'VIDEO_FRAMES' }) },
    (value: FeedbackAnalysisResult) => { firstIssue(value).source_refs = [] },
    (value: FeedbackAnalysisResult) => { firstIssue(value).source_refs = ['S1', 'S1'] },
    (value: FeedbackAnalysisResult) => { firstIssue(value).source_refs = ['S99'] },
    (value: FeedbackAnalysisResult) => { firstIssue(value).source_refs = Array.from({ length: 6 }, () => 'S1') },
    (value: FeedbackAnalysisResult) => { Object.assign(firstIssue(value), { timecode: '00:01' }) },
    (value: FeedbackAnalysisResult) => { firstAction(value).action = '' },
    (value: FeedbackAnalysisResult) => { firstAction(value).action = 'x'.repeat(501) },
    (value: FeedbackAnalysisResult) => { firstAction(value).rationale = 'x'.repeat(301) },
    (value: FeedbackAnalysisResult) => { firstAction(value).source_refs = ['unknown'] },
    (value: FeedbackAnalysisResult) => { Object.assign(firstAction(value), { priority: 'CRITICAL' }) },
    (value: FeedbackAnalysisResult) => { value.payload.suggested_actions = Array.from({ length: 11 }, () => ({ ...firstAction(value) })) },
  ])('fails closed for malformed provenance, citations, fields or bounds %s', (mutate) => {
    const value = result(); mutate(value)
    expect(() => validateFeedbackAnalysis(value, selected)).toThrow(ApiError)
  })
  it('allows empty advisory issue/action lists and escaped text without executing it', () => {
    const value = result(); value.payload.issues = []; value.payload.suggested_actions = []
    value.payload.summary = '<script>synthetic text, not executable HTML</script>'
    expect(validateFeedbackAnalysis(value, selected)).toEqual(value)
  })
  it.each([null, [], true, 1, 'raw'])('rejects non-object response %j', (value) => {
    expect(() => validateFeedbackAnalysis(value, selected)).toThrow(ApiError)
  })
  it('rejects cyclic/non-JSON and oversized byte payloads without throwing raw internals', () => {
    const cycle = result(); Object.assign(cycle, { cycle })
    expect(() => validateFeedbackAnalysis(cycle, selected)).toThrow(ApiError)
    const value = result()
    value.payload.summary = '😀'.repeat(1600)
    value.payload.issues = Array.from({ length: 10 }, () => ({ category: 'CONTENT', description: '😀'.repeat(500), source_refs: ['S1'] }))
    value.payload.suggested_actions = Array.from({ length: 10 }, () => ({ action: '😀'.repeat(500), priority: 'HIGH', rationale: '😀'.repeat(300), source_refs: ['S1'] }))
    value.payload.uncertainty = '😀'.repeat(600); value.payload.warnings = Array.from({ length: 10 }, () => '😀'.repeat(300))
    expect(new TextEncoder().encode(JSON.stringify(value)).byteLength).toBeGreaterThan(65536)
    expect(() => validateFeedbackAnalysis(value, selected)).toThrow(ApiError)
  })
  it('keeps User/Profile/Workspace/Task correlation keys distinct without a result history key', () => {
    const key = feedbackAnalysisKeys.scope(profileId, profileId, workspaceId, taskId)
    expect(key).not.toEqual(feedbackAnalysisKeys.scope(otherId, profileId, workspaceId, taskId))
    expect(key).not.toEqual(feedbackAnalysisKeys.scope(profileId, otherId, workspaceId, taskId))
    expect(key).not.toEqual(feedbackAnalysisKeys.scope(profileId, profileId, otherId, taskId))
    expect(key).not.toEqual(feedbackAnalysisKeys.scope(profileId, profileId, workspaceId, otherId))
  })
})

describe('existing API client stateless analysis transport', () => {
  it('uses actual nested POST/CSRF/session contract without idempotency or mutation fallback', async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(json({ csrf_token: 'a'.repeat(64) })).mockResolvedValueOnce(json(result()))
    vi.stubGlobal('fetch', fetchMock)
    const controller = new AbortController()
    await expect(feedbackAnalysisApi.analyze(profileId, workspaceId, taskId, { sources: selected, focus: 'Synthetic focus.' }, controller.signal)).resolves.toEqual(result())
    expect(fetchMock).toHaveBeenCalledTimes(2)
    expect(fetchMock.mock.calls[0]?.[0]).toBe('/api/auth/csrf/')
    const [url, options] = fetchMock.mock.calls[1] as [string, RequestInit]
    expect(url).toBe(path)
    expect(options.method).toBe('POST')
    expect(options.credentials).toBe('same-origin')
    expect(options.cache).toBe('no-store')
    expect(options.signal).toBe(controller.signal)
    expect(options.headers).toMatchObject({ 'X-CSRFToken': 'a'.repeat(64), 'Content-Type': 'application/json' })
    expect(options.headers).not.toHaveProperty('Idempotency-Key')
    expect(JSON.parse(String(options.body))).toEqual({ sources: selected, focus: 'Synthetic focus.' })
    expect(url).not.toMatch(/confirm|ai\/task-proposals/)
  })
  it('freezes the sent selection while CSRF bootstrap is pending', async () => {
    let resolveCsrf!: (value: Response) => void
    const waiting = new Promise<Response>((resolve) => { resolveCsrf = resolve })
    const fetchMock = vi.fn().mockReturnValueOnce(waiting).mockResolvedValueOnce(json(result()))
    vi.stubGlobal('fetch', fetchMock)
    const input = { sources: selected.map((source) => ({ ...source })) }
    const pending = feedbackAnalysisApi.analyze(profileId, workspaceId, taskId, input)
    input.sources.reverse(); at(input.sources).id = otherId
    resolveCsrf(json({ csrf_token: 'a'.repeat(64) }))
    await pending
    expect(JSON.parse(String(fetchMock.mock.calls[1]?.[1].body))).toEqual({ sources: selected })
  })
  it('repeated stateless requests each POST and re-run quota checks; no automatic retry', async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(json({ csrf_token: 'a'.repeat(64) })).mockImplementation(async () => json(result()))
    vi.stubGlobal('fetch', fetchMock)
    await feedbackAnalysisApi.analyze(profileId, workspaceId, taskId, { sources: selected })
    await feedbackAnalysisApi.analyze(profileId, workspaceId, taskId, { sources: selected })
    expect(fetchMock.mock.calls.filter(([, options]) => options.method === 'POST')).toHaveLength(2)
    expect(fetchMock.mock.calls.every(([, options]) => !('Idempotency-Key' in options.headers))).toBe(true)
  })
  it.each([
    ['STALE_CONTEXT', 409], ['AI_DISABLED', 503], ['NOT_FOUND', 404], ['PERMISSION_DENIED', 403],
    ['RATE_LIMITED', 429], ['INVALID_PROVIDER_RESPONSE', 502], ['PROVIDER_TIMEOUT', 504],
  ] as const)('retains safe backend %s/%i without leaking provider/source text', async (code, status) => {
    const fetchMock = vi.fn().mockResolvedValueOnce(json({ csrf_token: 'a'.repeat(64) }))
      .mockResolvedValueOnce(json({ code, detail: 'SYNTHETIC_PRIVATE_PROVIDER_DETAIL' }, status, { 'retry-after': '30' }))
    vi.stubGlobal('fetch', fetchMock)
    const failure = await feedbackAnalysisApi.analyze(profileId, workspaceId, taskId, { sources: selected }).catch((error: unknown) => error)
    expect(failure).toBeInstanceOf(ApiError)
    expect(failure).toMatchObject({ status, code })
    expect(String(failure)).not.toContain('SYNTHETIC_PRIVATE_PROVIDER_DETAIL')
    if (status === 429) expect((failure as ApiError).retryAfterSeconds).toBe(30)
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })
  it('uses existing protected-request revalidation on permission denial', async () => {
    const forbidden = vi.fn()
    apiClient.setForbiddenHandler(forbidden)
    vi.stubGlobal('fetch', vi.fn().mockResolvedValueOnce(json({ csrf_token: 'a'.repeat(64) })).mockResolvedValueOnce(json({ code: 'PERMISSION_DENIED' }, 403)))
    await expect(feedbackAnalysisApi.analyze(profileId, workspaceId, taskId, { sources: selected })).rejects.toMatchObject({ status: 403 })
    expect(forbidden).toHaveBeenCalledOnce()
  })
  it('maps only safe source/focus field errors and never reflects backend feedback text', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValueOnce(json({ csrf_token: 'a'.repeat(64) })).mockResolvedValueOnce(json({
      code: 'VALIDATION_ERROR', fields: { sources: ['SYNTHETIC_PRIVATE_FEEDBACK'], focus: ['SYNTHETIC_PRIVATE_FOCUS'], actor: ['SYNTHETIC_PRIVATE_ID'] },
    }, 400)))
    const failure = await feedbackAnalysisApi.analyze(profileId, workspaceId, taskId, { sources: selected }).catch((error: unknown) => error)
    expect(failure).toMatchObject({ status: 400, code: 'VALIDATION_ERROR', fieldErrors: {
      sources: 'Chọn từ 1 đến 20 nguồn phản hồi hợp lệ thuộc công việc hiện tại.',
      focus: 'Nhập trọng tâm tối đa 1.000 ký tự Unicode hợp lệ, không chứa ký tự NUL.',
    } })
    expect((failure as ApiError).fieldErrors).not.toHaveProperty('actor')
    expect(JSON.stringify(failure)).not.toContain('SYNTHETIC_PRIVATE')
  })
  it('does not refresh/retry unsafe analysis after CSRF denial', async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(json({ csrf_token: 'a'.repeat(64) }))
      .mockResolvedValueOnce(new Response('CSRF failed', { status: 403, headers: { 'content-type': 'text/html' } }))
    vi.stubGlobal('fetch', fetchMock)
    await expect(feedbackAnalysisApi.analyze(profileId, workspaceId, taskId, { sources: selected })).rejects.toMatchObject({ status: 403, kind: 'csrf' })
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })
  it('network failure is one attempt and never a durable-success claim', async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(json({ csrf_token: 'a'.repeat(64) })).mockRejectedValueOnce(new TypeError('SYNTHETIC_PRIVATE_NETWORK'))
    vi.stubGlobal('fetch', fetchMock)
    await expect(feedbackAnalysisApi.analyze(profileId, workspaceId, taskId, { sources: selected })).rejects.toMatchObject({ kind: 'network' })
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })
  it('rejects mismatched response IDs instead of showing another source result', async () => {
    const foreign = result(); at(foreign.sources).id = otherId
    vi.stubGlobal('fetch', vi.fn().mockResolvedValueOnce(json({ csrf_token: 'a'.repeat(64) })).mockResolvedValueOnce(json(foreign)))
    await expect(feedbackAnalysisApi.analyze(profileId, workspaceId, taskId, { sources: selected })).rejects.toMatchObject({ kind: 'invalid-response' })
  })
  it('rejects invalid scope or selection before any fetch', async () => {
    const fetchMock = vi.fn(); vi.stubGlobal('fetch', fetchMock)
    await expect(feedbackAnalysisApi.analyze('../foreign', workspaceId, taskId, { sources: selected })).rejects.toMatchObject({ status: 404 })
    await expect(feedbackAnalysisApi.analyze(profileId, workspaceId, taskId, { sources: [] })).rejects.toMatchObject({ status: 400 })
    expect(fetchMock).not.toHaveBeenCalled()
  })
  it('aborts before CSRF/bootstrap without returning a response', async () => {
    const fetchMock = vi.fn(); vi.stubGlobal('fetch', fetchMock)
    const controller = new AbortController(); controller.abort()
    await expect(feedbackAnalysisApi.analyze(profileId, workspaceId, taskId, { sources: selected }, controller.signal)).rejects.toMatchObject({ name: 'AbortError' })
    expect(fetchMock).not.toHaveBeenCalled()
  })
})
