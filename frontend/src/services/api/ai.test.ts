/** Mocked transport/contract tests; real fixture/UI acceptance runs in isolated PostgreSQL. */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { ApiClient, ApiError, apiClient } from './client'
import type { AiErrorCode } from './client'
import { aiApi, aiKeys, isAiDateTime, validateAiAvailability, validateAiBrief, validateAiPlan, validateAiProposal } from './ai'
import type { AiAvailability, AiProposal, AiTaskNode, AiTaskPlan } from './ai'

const profileId = '00000000-0000-4000-8000-000000000401'
const workspaceId = '00000000-0000-4000-8000-000000000402'
const proposalId = '00000000-0000-4000-8000-000000000403'
const otherId = '00000000-0000-4000-8000-000000000404'
const key = '00000000-0000-4000-8000-000000000405'
const timestamp = '2026-11-02T00:00:00Z'
const base = `v1/profiles/${profileId}/workspaces/${workspaceId}/ai/task-proposals/`
const plan = (): AiTaskPlan => ({
  contract_version: 'ai.task-plan.v1',
  tasks: [
    { local_ref: 'item_1', parent_ref: null, title: 'Synthetic root', description: 'Human review required.', priority: 'MEDIUM', proposed_deadline: null, notes: 'Not live AI.' },
    { local_ref: 'item_2', parent_ref: 'item_1', title: 'Synthetic child', description: '', priority: 'LOW', proposed_deadline: '2027-01-01T12:00:00+07:00', notes: '' },
  ],
  assumptions: [], warnings: ['Synthetic fixture; not AI analysis.'],
})
const proposal = (): AiProposal => ({
  contract_version: 'ai.v1', proposal_id: proposalId, revision: 1, scenario_id: 'task-tree-v1',
  status: 'AVAILABLE', mode: 'fixture_demo', generated_by_ai: false, persisted: true,
  created_at: timestamp, expires_at: '2026-11-02T00:30:00Z', payload_expires_at: '2026-11-09T00:30:00Z',
  confirmed_at: null, recovery_expires_at: null, payload: plan(), created_tasks: null,
  usage: { input_tokens: 0, billable_output_tokens: 0, cost_usd: '0.000000', status: 'fixture_zero' },
})
const confirmed = (): AiProposal => ({
  ...proposal(), status: 'CONFIRMED', payload: null, created_tasks: { item_1: otherId, item_2: key },
  confirmed_at: '2026-11-02T00:05:00Z', recovery_expires_at: '2026-12-02T00:05:00Z',
})
const availability = (): AiAvailability => ({
  contract_version: 'ai.v1', enabled: true, mode: 'fixture_demo', generated_by_ai: false,
  scenarios: [{ id: 'subtitle-check-v1', label: 'Phụ đề giả lập', brief: 'Ví dụ synthetic kiểm tra phụ đề.' },
    { id: 'task-tree-v1', label: 'Công việc con giả lập', brief: 'Ví dụ synthetic Task và Subtask.' }],
  limits: { max_brief_chars: 6000, max_tasks: 20, max_depth: 3, max_request_bytes: 32768 },
})
const json = (body: unknown, status = 200) => new Response(JSON.stringify(body), { status, headers: { 'content-type': 'application/json' } })
function node(value: AiTaskPlan, index = 0): AiTaskNode {
  const item = value.tasks[index]
  if (!item) throw new Error('Invalid synthetic test fixture.')
  return item
}
function scenarioAt(value: AiAvailability, index: number) {
  const item = value.scenarios[index]
  if (!item) throw new Error('Invalid synthetic test fixture.')
  return item
}

beforeEach(() => { apiClient.clearCsrf(); apiClient.setForbiddenHandler(null) })
afterEach(() => { apiClient.clearCsrf(); apiClient.setForbiddenHandler(null); vi.unstubAllGlobals() })

describe('bounded fixture contracts', () => {
  it('accepts nested preview, confirmed mapping and expired tombstone without inventing fields', () => {
    expect(validateAiPlan(plan())).toEqual(plan())
    expect(validateAiProposal(proposal(), proposalId.toUpperCase())).toEqual(proposal())
    expect(validateAiProposal(confirmed())).toEqual(confirmed())
    const expired = { ...proposal(), status: 'EXPIRED', payload: null }
    expect(validateAiProposal(expired)).toEqual(expired)
  })
  it('accepts explicit disabled metadata and only server-owned scenario choices', () => {
    expect(validateAiAvailability(availability())).toEqual(availability())
    expect(validateAiAvailability({ ...availability(), enabled: false }).enabled).toBe(false)
  })
  it.each(['', ' ', 'x'.repeat(6001), 'nul\0value', 'bad\uD800value'])('rejects invalid synthetic brief: %j', (brief) => {
    expect(validateAiBrief(brief)).toBe(false)
  })
  it('counts Unicode codepoints consistently with backend, not UTF16 code units', () => {
    expect(validateAiBrief('😀'.repeat(6000))).toBe(true)
    const value = plan(); node(value).title = '😀'.repeat(255)
    expect(validateAiPlan(value)).toEqual(value)
  })
  it.each([
    '2027-02-30T00:00:00Z', '2027-02-29T00:00:00Z', '0000-01-01T00:00:00Z',
    '2027-01-01T24:00:00Z', '2027-01-01T00:60:00Z', '2027-01-01T00:00:60Z',
    '2027-01-01T00:00:00', '2027-01-01', '2027-01-01T00:00:00+24:00',
    '2027-01-01T00:00:00+01:60', '2027-01-01T00:00:00.1234567Z', '999999-01-01T00:00:00Z',
  ])('rejects malformed/overflow/naive deadline: %s', (deadline) => {
    expect(isAiDateTime(deadline)).toBe(false)
    const value = plan(); node(value).proposed_deadline = deadline
    expect(() => validateAiPlan(value)).toThrow(ApiError)
  })
  it('accepts leap days, microseconds and aware offset values', () => {
    for (const value of ['2028-02-29T00:00:00Z', '2027-01-01T00:00:00.123456Z', '2027-01-01T12:00:00-05:30']) expect(isAiDateTime(value)).toBe(true)
  })
  it.each([
    (value: AiTaskPlan) => { node(value).title = ' ' },
    (value: AiTaskPlan) => { node(value).title = 'x'.repeat(256) },
    (value: AiTaskPlan) => { node(value).description = 'x'.repeat(2001) },
    (value: AiTaskPlan) => { node(value).notes = 'x'.repeat(501) },
    (value: AiTaskPlan) => { node(value).title = 'bad\0value' },
    (value: AiTaskPlan) => { node(value).title = 'bad\uD800value' },
    (value: AiTaskPlan) => { Object.assign(node(value), { priority: 'TOP' }) },
    (value: AiTaskPlan) => { Object.assign(node(value), { status: 'COMPLETED' }) },
    (value: AiTaskPlan) => { Object.assign(value, { workspace_id: otherId }) },
    (value: AiTaskPlan) => { value.warnings = ['x'.repeat(301)] },
    (value: AiTaskPlan) => { value.assumptions = Array.from({ length: 11 }, () => 'extra') },
    (value: AiTaskPlan) => { value.tasks = [] },
    (value: AiTaskPlan) => { value.tasks = Array.from({ length: 21 }, (_, index) => ({ ...node(value), local_ref: `item_${index + 1}` })) },
    (value: AiTaskPlan) => { node(value, 1).local_ref = 'item_1' },
    (value: AiTaskPlan) => { node(value, 1).parent_ref = 'item_999' },
    (value: AiTaskPlan) => { node(value).parent_ref = 'item_1' },
    (value: AiTaskPlan) => { node(value).parent_ref = 'item_2' },
    (value: AiTaskPlan) => { node(value).local_ref = '__proto__' },
  ])('fails closed for untrusted fields, limits, enum or invalid hierarchy %s', (mutate) => {
    const value = plan(); mutate(value)
    expect(() => validateAiPlan(value)).toThrow(ApiError)
  })
  it('allows max3 child edges but rejects a fourth', () => {
    const value = plan()
    for (const index of [3, 4]) value.tasks.push({ ...node(value), local_ref: `item_${index}`, parent_ref: `item_${index - 1}` })
    expect(validateAiPlan(value)).toEqual(value)
    value.tasks.push({ ...node(value), local_ref: 'item_5', parent_ref: 'item_4' })
    expect(() => validateAiPlan(value)).toThrow(ApiError)
  })
  it.each([
    (value: AiProposal) => Object.assign(value, { mode: 'live', generated_by_ai: true }),
    (value: AiProposal) => Object.assign(value, { actor_id: otherId }),
    (value: AiProposal) => Object.assign(value, { revision: 0 }),
    (value: AiProposal) => Object.assign(value, { proposal_id: 'bad' }),
    (value: AiProposal) => Object.assign(value, { scenario_id: 'provider-controlled' }),
    (value: AiProposal) => Object.assign(value, { expires_at: timestamp }),
    (value: AiProposal) => Object.assign(value, { payload_expires_at: timestamp }),
    (value: AiProposal) => Object.assign(value, { status: 'CONFIRMED' }),
    (value: AiProposal) => Object.assign(value, { status: 'EXPIRED' }),
    (value: AiProposal) => Object.assign(value.usage, { cost_usd: '10.000000' }),
    (value: AiProposal) => Object.assign(value.usage, { api_key: 'unsupported' }),
  ])('rejects malformed/misleading proposal envelope %s', (mutate) => {
    const value = proposal(); mutate(value)
    expect(() => validateAiProposal(value)).toThrow(ApiError)
  })
  it('rejects duplicate, missing or nonlocal committed mapping identities', () => {
    for (const created_tasks of [{}, { item_1: 'invalid' }, { actor_id: otherId }, { item_1: otherId, item_2: otherId }]) {
      expect(() => validateAiProposal({ ...confirmed(), created_tasks })).toThrow(ApiError)
    }
  })
  it.each([
    (value: AiAvailability) => Object.assign(value, { enabled: 'true' }),
    (value: AiAvailability) => Object.assign(value, { provider: 'live' }),
    (value: AiAvailability) => { scenarioAt(value, 1).id = scenarioAt(value, 0).id },
    (value: AiAvailability) => { scenarioAt(value, 0).brief = '' },
    (value: AiAvailability) => Object.assign(value.limits, { max_depth: 100 }),
    (value: AiAvailability) => Object.assign(value.limits, { max_tasks: 100 }),
  ])('rejects malformed feature metadata %s', (mutate) => {
    const value = availability(); mutate(value)
    expect(() => validateAiAvailability(value)).toThrow(ApiError)
  })
  it('does not render arbitrary text as HTML; validation leaves plain text for React escaping', () => {
    const value = plan(); node(value).title = '<img src=x onerror=alert(1)>'
    expect(node(validateAiPlan(value)).title).toBe(node(value).title)
  })
})

describe('scoped AI API integration', () => {
  it('discovers only permission-checked metadata through same existing route', async () => {
    const request = vi.spyOn(apiClient, 'request').mockResolvedValue({ name: 'Proposal', ai: availability() })
    expect(await aiApi.availability(profileId, workspaceId)).toEqual(availability())
    expect(request).toHaveBeenCalledExactlyOnceWith(base, { method: 'OPTIONS', signal: undefined, protected: true })
  })
  it('sends optional synthetic brief/name-owned scenario only with durable UUID key', async () => {
    const request = vi.spyOn(apiClient, 'request').mockResolvedValue(proposal())
    const controller = new AbortController()
    await aiApi.generate(profileId, workspaceId, { scenario_id: 'task-tree-v1', brief: 'Synthetic demo', owner_id: otherId } as never, key, controller.signal)
    expect(request).toHaveBeenCalledExactlyOnceWith(base, { method: 'POST', body: { scenario_id: 'task-tree-v1', brief: 'Synthetic demo' }, idempotencyKey: key, signal: controller.signal, protected: true })
  })
  it('retains scenario-only backwards-compatible generation', async () => {
    const request = vi.spyOn(apiClient, 'request').mockResolvedValue(proposal())
    await aiApi.generate(profileId, workspaceId, { scenario_id: 'task-tree-v1' }, key)
    expect(request).toHaveBeenLastCalledWith(base, expect.objectContaining({ body: { scenario_id: 'task-tree-v1' } }))
  })
  it('uses complete edited payload and explicit confirmation without ordinary Task POST', async () => {
    const edited = plan(); node(edited).title = 'Human edited title'
    const request = vi.spyOn(apiClient, 'request').mockResolvedValue(confirmed())
    await aiApi.confirm(profileId, workspaceId, proposalId, { proposal_revision: 1, confirmed: true, payload: edited }, key)
    expect(request).toHaveBeenCalledExactlyOnceWith(`${base}${proposalId}/confirm/`, {
      method: 'POST', body: { proposal_revision: 1, confirmed: true, payload: edited }, idempotencyKey: key, signal: undefined, protected: true,
    })
  })
  it('recovery GET checks returned proposal identity before exposing created IDs', async () => {
    const request = vi.spyOn(apiClient, 'request').mockResolvedValueOnce(confirmed()).mockResolvedValueOnce({ ...confirmed(), proposal_id: otherId })
    expect(await aiApi.proposal(profileId, workspaceId, proposalId)).toEqual(confirmed())
    expect(request).toHaveBeenNthCalledWith(1, `${base}${proposalId}/`, { signal: undefined, protected: true })
    await expect(aiApi.proposal(profileId, workspaceId, proposalId)).rejects.toMatchObject({ kind: 'invalid-response' })
  })
  it('does not present an unconfirmed success body as a committed confirmation', async () => {
    vi.spyOn(apiClient, 'request').mockResolvedValue(proposal())
    await expect(aiApi.confirm(profileId, workspaceId, proposalId, { proposal_revision: 1, confirmed: true, payload: plan() }, key))
      .rejects.toMatchObject({ kind: 'invalid-response' })
  })
  it('rejects invalid scope IDs and brief before starting a request', async () => {
    const request = vi.spyOn(apiClient, 'request')
    await expect(aiApi.generate('other/path', workspaceId, { scenario_id: 'task-tree-v1' }, key)).rejects.toMatchObject({ status: 404 })
    await expect(aiApi.generate(profileId, workspaceId, { scenario_id: 'task-tree-v1', brief: ' ' }, key)).rejects.toMatchObject({ status: 400 })
    expect(request).not.toHaveBeenCalled()
  })
  it('rejects oversized UTF8 confirmation body before sending, even when strings fit individual limits', async () => {
    const value = plan()
    value.tasks = Array.from({ length: 20 }, (_, index) => ({ ...node(value), local_ref: `item_${index + 1}`, description: '😀'.repeat(500) }))
    const request = vi.spyOn(apiClient, 'request')
    await expect(aiApi.confirm(profileId, workspaceId, proposalId, { proposal_revision: 1, confirmed: true, payload: value }, key)).rejects.toBeInstanceOf(ApiError)
    expect(request).not.toHaveBeenCalled()
  })
  it('uses user and both tenant dimensions for every private cache key', () => {
    expect(aiKeys.scope(otherId, profileId, workspaceId)).not.toEqual(aiKeys.scope(key, profileId, workspaceId))
    expect(aiKeys.proposal(otherId, profileId, workspaceId, proposalId)).not.toEqual(aiKeys.proposal(otherId, otherId, workspaceId, proposalId))
    expect(aiKeys.proposal(otherId, profileId, workspaceId, proposalId)).not.toEqual(aiKeys.proposal(otherId, profileId, otherId, proposalId))
    expect(aiKeys.availability(otherId, profileId, workspaceId).slice(0, 4)).toEqual(aiKeys.scope(otherId, profileId, workspaceId))
  })
})

describe('existing transport with constrained AI metadata', () => {
  it('sends UUID key with CSRF/cookies and never arbitrary extra headers', async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(json({ csrf_token: 'a'.repeat(64) })).mockResolvedValueOnce(json(proposal(), 201))
    vi.stubGlobal('fetch', fetchMock)
    await new ApiClient().request(base, { method: 'POST', body: { scenario_id: 'task-tree-v1' }, idempotencyKey: key })
    expect(fetchMock).toHaveBeenNthCalledWith(2, `/api/${base}`, expect.objectContaining({
      credentials: 'same-origin', headers: { Accept: 'application/json', 'Content-Type': 'application/json', 'X-CSRFToken': 'a'.repeat(64), 'Idempotency-Key': key },
    }))
  })
  it.each([
    ['auth/logout/', 'POST', key], [base, 'GET', key], [base, 'OPTIONS', key],
    [base, 'POST', 'bad'], [`${base}?redirect=external`, 'POST', key],
    [base, 'POST', 'a\r\nAuthorization: override'],
  ] as const)('rejects unapproved key destination/method/input before CSRF: %s %s', async (path, method, inputKey) => {
    const fetchMock = vi.fn(); vi.stubGlobal('fetch', fetchMock)
    await expect(new ApiClient().request(path, { method, idempotencyKey: inputKey })).rejects.toBeInstanceOf(TypeError)
    expect(fetchMock).not.toHaveBeenCalled()
  })
  it.each([
    [503, 'AI_DISABLED'], [410, 'EXPIRED'], [409, 'ALREADY_CONFIRMED'],
    [409, 'IDEMPOTENCY_CONFLICT'], [410, 'RECOVERY_EXPIRED'], [429, 'RATE_LIMITED'],
  ] as const)('retains only safe machine code at HTTP%s: %s', async (status, code) => {
    const fetchMock = vi.fn().mockResolvedValue(json({ detail: 'private provider diagnostics', code, fields: {} }, status))
    vi.stubGlobal('fetch', fetchMock)
    const error = await new ApiClient().request(base).catch((value: unknown) => value)
    expect(error).toMatchObject({ status, code })
    expect(JSON.stringify(error)).not.toContain('private')
  })
  it('drops unknown/error-reflected code and localizes approved field names only', async () => {
    const fetchMock = vi.fn().mockResolvedValue(json({ code: 'private error data', detail: 'private', fields: { brief: ['private'], provider_key: ['secret'] } }, 400))
    vi.stubGlobal('fetch', fetchMock)
    await expect(new ApiClient().request(base)).rejects.toMatchObject({ code: null, fieldErrors: { brief: 'Nhập yêu cầu giả lập hợp lệ từ 1 đến 6.000 ký tự.' } })
  })
  it('keeps existing ApiError constructor shape backward compatible', () => {
    const error = new ApiError(403, 'forbidden', 'Safe')
    expect(error.code).toBeNull()
    const code: AiErrorCode = 'AI_DISABLED'
    expect(new ApiError(503, 'server', 'Safe', {}, null, code).code).toBe(code)
  })
  it('propagates CSRF rejection and never automatically replays a keyed mutation', async () => {
    const fetchMock = vi.fn().mockResolvedValueOnce(json({ csrf_token: 'a'.repeat(64) })).mockResolvedValueOnce(json({ detail: 'CSRF Failed: missing' }, 403))
    vi.stubGlobal('fetch', fetchMock)
    await expect(new ApiClient().request(base, { method: 'POST', idempotencyKey: key })).rejects.toMatchObject({ kind: 'csrf', code: null })
    expect(fetchMock).toHaveBeenCalledTimes(2)
  })
})

