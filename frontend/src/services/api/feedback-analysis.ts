/** Stateless fixture analysis. Suggestions never confer authority or trigger domain writes. */
import { ApiError, apiClient, invalidResponse } from './client'
import { aiPriorities } from './ai'

export const feedbackSourceKinds = ['review', 'comment'] as const
export const feedbackIssueCategories = ['CLARITY', 'TECHNICAL', 'CONTENT', 'PROCESS', 'OTHER'] as const
export interface FeedbackSelection { kind: typeof feedbackSourceKinds[number]; id: string }
export interface FeedbackAnalysisInput { sources: FeedbackSelection[]; focus?: string }
export interface FeedbackAnalysisPayload {
  contract_version: 'ai.feedback.v1'
  summary: string
  issues: { category: typeof feedbackIssueCategories[number]; description: string; source_refs: string[] }[]
  suggested_actions: { action: string; priority: typeof aiPriorities[number]; rationale: string; source_refs: string[] }[]
  uncertainty: string
  warnings: string[]
}
export interface FeedbackAnalysisResult {
  contract_version: 'ai.v1'
  status: 'READY'
  mode: 'fixture_demo'
  generated_by_ai: false
  persisted: false
  fixture_version: 'fixture.v1'
  sources: (FeedbackSelection & { ref: string })[]
  payload: FeedbackAnalysisPayload
  usage: { input_tokens: 0; billable_output_tokens: 0; cost_usd: '0.000000'; status: 'fixture_zero' }
}

const record = (value: unknown): value is Record<string, unknown> =>
  value !== null && typeof value === 'object' && !Array.isArray(value)
const uuid = (value: unknown): value is string =>
  typeof value === 'string' && /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(value)
const exact = (value: Record<string, unknown>, fields: readonly string[]) =>
  Object.keys(value).length === fields.length && fields.every((field) => Object.hasOwn(value, field))
const text = (value: unknown, maximum: number, required = false): value is string =>
  typeof value === 'string' && value.length <= maximum * 2 && Array.from(value).length <= maximum &&
  !value.includes('\0') && !/[\uD800-\uDFFF]/u.test(value) && (!required || !!value.trim())
const kind = (value: unknown): value is FeedbackSelection['kind'] => feedbackSourceKinds.some((item) => item === value)
function sizeWithin(value: unknown, maximum: number): boolean {
  try {
    const raw = JSON.stringify(value)
    return typeof raw === 'string' && raw.length <= maximum && new TextEncoder().encode(raw).byteLength <= maximum
  } catch { return false }
}
function validSelections(value: unknown): value is FeedbackSelection[] {
  if (!Array.isArray(value) || value.length < 1 || value.length > 20) return false
  const seen = new Set<string>()
  for (const item of value) {
    if (!record(item) || !exact(item, ['kind', 'id']) || !kind(item.kind) || !uuid(item.id)) return false
    const key = `${item.kind}:${item.id.toLowerCase()}`
    if (seen.has(key)) return false
    seen.add(key)
  }
  return true
}

export function validateFeedbackFocus(value: unknown): value is string { return text(value, 1000) }

/** Reject unknown/mutation fields and return a plain immutable-in-flight wire snapshot. */
export function validateFeedbackInput(value: unknown): FeedbackAnalysisInput {
  if (!record(value) || Object.keys(value).some((field) => field !== 'sources' && field !== 'focus') ||
      !validSelections(value.sources)) {
    throw new ApiError(400, 'validation', 'Vui lòng chọn từ 1 đến 20 nguồn phản hồi hợp lệ, không trùng lặp.',
      { sources: 'Chọn từ 1 đến 20 nhận xét thuộc công việc hiện tại.' })
  }
  if (value.focus !== undefined && !validateFeedbackFocus(value.focus)) {
    throw new ApiError(400, 'validation', 'Trọng tâm phân tích chưa hợp lệ.',
      { focus: 'Nhập tối đa 1.000 ký tự Unicode hợp lệ, không chứa ký tự NUL.' })
  }
  const input: FeedbackAnalysisInput = {
    sources: value.sources.map((item) => ({ kind: item.kind, id: item.id.toLowerCase() })),
    ...(value.focus === undefined ? {} : { focus: value.focus }),
  }
  if (!sizeWithin(input, 32768)) throw new ApiError(400, 'validation', 'Yêu cầu vượt giới hạn 32 KiB.')
  return input
}

function citations(value: unknown, allowed: ReadonlySet<string>): value is string[] {
  return Array.isArray(value) && value.length >= 1 && value.length <= 5 &&
    value.every((ref) => typeof ref === 'string' && allowed.has(ref)) && new Set(value).size === value.length
}
function payload(value: unknown, allowed: ReadonlySet<string>): value is FeedbackAnalysisPayload {
  if (!record(value) || !exact(value, ['contract_version', 'summary', 'issues', 'suggested_actions', 'uncertainty', 'warnings']) ||
      value.contract_version !== 'ai.feedback.v1' || !text(value.summary, 1600, true) ||
      !text(value.uncertainty, 600) || !Array.isArray(value.warnings) || value.warnings.length > 10 ||
      !value.warnings.every((warning) => text(warning, 300)) ||
      !Array.isArray(value.issues) || value.issues.length > 10 ||
      !Array.isArray(value.suggested_actions) || value.suggested_actions.length > 10) return false
  return value.issues.every((item) => record(item) && exact(item, ['category', 'description', 'source_refs']) &&
    feedbackIssueCategories.some((category) => category === item.category) && text(item.description, 500, true) && citations(item.source_refs, allowed)) &&
    value.suggested_actions.every((item) => record(item) && exact(item, ['action', 'priority', 'rationale', 'source_refs']) &&
      text(item.action, 500, true) && aiPriorities.some((priority) => priority === item.priority) &&
      text(item.rationale, 300) && citations(item.source_refs, allowed))
}

/** Match the response to the frozen request, rather than trusting model-provided IDs. */
export function validateFeedbackAnalysis(value: unknown, expectedSources: readonly FeedbackSelection[]): FeedbackAnalysisResult {
  if (!validSelections(expectedSources) || !record(value) ||
      !exact(value, ['contract_version', 'status', 'mode', 'generated_by_ai', 'persisted', 'fixture_version', 'sources', 'payload', 'usage']) ||
      !sizeWithin(value, 65536) || value.contract_version !== 'ai.v1' || value.status !== 'READY' ||
      value.mode !== 'fixture_demo' || value.generated_by_ai !== false || value.persisted !== false ||
      value.fixture_version !== 'fixture.v1' || !Array.isArray(value.sources) || value.sources.length !== expectedSources.length ||
      !record(value.usage) || !exact(value.usage, ['input_tokens', 'billable_output_tokens', 'cost_usd', 'status']) ||
      value.usage.input_tokens !== 0 || value.usage.billable_output_tokens !== 0 ||
      value.usage.cost_usd !== '0.000000' || value.usage.status !== 'fixture_zero') throw invalidResponse()
  const allowed = new Set<string>()
  for (const [index, item] of value.sources.entries()) {
    const expected = expectedSources[index]
    if (!expected || !record(item) || !exact(item, ['ref', 'kind', 'id']) || item.ref !== `S${index + 1}` ||
        !kind(item.kind) || !uuid(item.id) || item.kind !== expected.kind || item.id.toLowerCase() !== expected.id.toLowerCase()) throw invalidResponse()
    allowed.add(item.ref)
  }
  if (!payload(value.payload, allowed)) throw invalidResponse()
  return value as unknown as FeedbackAnalysisResult
}

function entityId(value: string): string {
  if (!uuid(value)) throw new ApiError(404, 'not-found', 'Không tìm thấy nội dung hoặc bạn không có quyền truy cập.')
  return value.toLowerCase()
}
export const feedbackAnalysisKeys = {
  scope: (userId: string, profileId: string, workspaceId: string, taskId: string) =>
    ['feedback-analysis', userId, profileId, workspaceId, taskId] as const,
}
export const feedbackAnalysisApi = {
  async analyze(profileId: string, workspaceId: string, taskId: string, input: FeedbackAnalysisInput, signal?: AbortSignal): Promise<FeedbackAnalysisResult> {
    const body = validateFeedbackInput(input)
    const path = `v1/profiles/${entityId(profileId)}/workspaces/${entityId(workspaceId)}/tasks/${entityId(taskId)}/ai/feedback-analysis/`
    return validateFeedbackAnalysis(await apiClient.request<unknown>(path, {
      method: 'POST', body, signal, protected: true,
    }), body.sources)
  },
}
