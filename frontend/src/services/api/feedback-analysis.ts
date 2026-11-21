/** Advisory analysis. Suggestions cannot confer authority or trigger domain writes. */
import { ApiError, apiClient, invalidResponse } from './client'
import { aiPriorities, validAiUsage } from './ai'
import type { AiMode, AiUsage } from './ai'

export const feedbackSourceKinds = ['review', 'comment'] as const
export const feedbackIssueCategories = ['CLARITY', 'TECHNICAL', 'CONTENT', 'PROCESS', 'OTHER'] as const
export interface FeedbackSelection { kind: typeof feedbackSourceKinds[number]; id: string }
export interface FeedbackAnalysisInput { sources: FeedbackSelection[]; focus?: string; feedback_text?: string }
export type FeedbackEvidence = { source_ref: string; quote: string }
export interface FeedbackAnalysisPayload {
  contract_version: 'ai.feedback.v1' | 'ai.feedback.v2'
  summary: string
  issues: { category: typeof feedbackIssueCategories[number]; description: string; source_refs: string[]; severity?: typeof aiPriorities[number]; evidence?: FeedbackEvidence[] }[]
  suggested_actions: { action: string; priority: typeof aiPriorities[number]; rationale: string; source_refs: string[] }[]
  uncertainty: string
  warnings: string[]
}
export interface FeedbackAnalysisResult {
  contract_version: 'ai.v1'
  status: 'READY'
  mode: AiMode
  generated_by_ai: boolean
  persisted: false
  fixture_version: 'fixture.v1' | null
  provider?: 'openai'
  model?: string
  sources: ((FeedbackSelection & { ref: string }) | { ref: string; kind: 'manual'; id: null })[]
  payload: FeedbackAnalysisPayload
  usage: AiUsage
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
function validSelections(value: unknown, manual = false): value is FeedbackSelection[] {
  if (!Array.isArray(value) || value.length < (manual ? 0 : 1) || value.length > (manual ? 19 : 20)) return false
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
export function validateManualFeedback(value: unknown): value is string { return text(value, 4000, true) }

/** Reject unknown/mutation fields and return a plain immutable-in-flight wire snapshot. */
export function validateFeedbackInput(value: unknown, mode: AiMode = 'fixture_demo'): FeedbackAnalysisInput {
  if (!record(value) || Object.keys(value).some((field) => field !== 'sources' && field !== 'focus' && (mode !== 'openai_live' || field !== 'feedback_text'))) {
    throw new ApiError(400, 'validation', 'Yêu cầu phân tích không hợp lệ.')
  }
  const manual = value.feedback_text !== undefined
  if (manual && !validateManualFeedback(value.feedback_text)) {
    throw new ApiError(400, 'validation', 'Nội dung phản hồi chưa hợp lệ.', { feedback_text: 'Nhập phản hồi từ 1 đến 4.000 ký tự hợp lệ.' })
  }
  if (!validSelections(value.sources, manual)) {
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
    ...(typeof value.feedback_text === 'string' ? { feedback_text: value.feedback_text } : {}),
  }
  if (!sizeWithin(input, 32768)) throw new ApiError(400, 'validation', 'Yêu cầu vượt giới hạn 32 KiB.')
  return input
}

function citations(value: unknown, allowed: ReadonlySet<string>): value is string[] {
  return Array.isArray(value) && value.length >= 1 && value.length <= 5 &&
    value.every((ref) => typeof ref === 'string' && allowed.has(ref)) && new Set(value).size === value.length
}
function validEvidence(value: unknown, allowed: ReadonlySet<string>): boolean {
  return Array.isArray(value) && value.length === allowed.size && value.length >= 1 && value.length <= 3 &&
    value.every((item) => record(item) && exact(item, ['source_ref', 'quote']) &&
      typeof item.source_ref === 'string' && allowed.has(item.source_ref) && text(item.quote, 300, true)) &&
    new Set(value.map((item) => item.source_ref)).size === allowed.size
}

function payload(value: unknown, allowed: ReadonlySet<string>, live: boolean): value is FeedbackAnalysisPayload {
  if (!record(value) || !exact(value, ['contract_version', 'summary', 'issues', 'suggested_actions', 'uncertainty', 'warnings']) ||
      value.contract_version !== (live ? 'ai.feedback.v2' : 'ai.feedback.v1') || !text(value.summary, 1600, true) ||
      !text(value.uncertainty, 600) || !Array.isArray(value.warnings) || value.warnings.length > 10 ||
      !value.warnings.every((warning) => text(warning, 300)) ||
      !Array.isArray(value.issues) || value.issues.length > 10 ||
      !Array.isArray(value.suggested_actions) || value.suggested_actions.length > 10) return false
  return value.issues.every((item) => record(item) && exact(item, ['category', 'description', 'source_refs', ...(live ? ['severity', 'evidence'] : [])]) &&
    feedbackIssueCategories.some((category) => category === item.category) && text(item.description, 500, true) && citations(item.source_refs, allowed) &&
    (!live || (aiPriorities.some((priority) => priority === item.severity) && validEvidence(item.evidence, new Set(item.source_refs))))) &&
    value.suggested_actions.every((item) => record(item) && exact(item, ['action', 'priority', 'rationale', 'source_refs']) &&
      text(item.action, 500, true) && aiPriorities.some((priority) => priority === item.priority) &&
      text(item.rationale, 300) && citations(item.source_refs, allowed))
}

/** Match the response to the frozen request, rather than trusting model-provided IDs. */
export function validateFeedbackAnalysis(value: unknown, expectedSources: readonly FeedbackSelection[], mode: AiMode = 'fixture_demo', manual = false): FeedbackAnalysisResult {
  const live = mode === 'openai_live'
  if (!validSelections(expectedSources, manual) || !record(value) || (manual && !live) ||
      !exact(value, ['contract_version', 'status', 'mode', 'generated_by_ai', 'persisted', 'fixture_version', 'sources', 'payload', 'usage', ...(live ? ['provider', 'model'] : [])]) ||
      !sizeWithin(value, 65536) || value.contract_version !== 'ai.v1' || value.status !== 'READY' ||
      value.mode !== mode || value.generated_by_ai !== live || value.persisted !== false ||
      (live ? value.fixture_version !== null || value.provider !== 'openai' || !text(value.model, 120, true) : value.fixture_version !== 'fixture.v1') ||
      !Array.isArray(value.sources) || value.sources.length !== expectedSources.length + Number(manual) || !validAiUsage(value.usage, mode)) throw invalidResponse()
  const allowed = new Set<string>()
  for (const [index, item] of value.sources.entries()) {
    if (!record(item) || !exact(item, ['ref', 'kind', 'id']) || item.ref !== `S${index + 1}`) throw invalidResponse()
    const expected = expectedSources[index]
    if (expected ? (!kind(item.kind) || !uuid(item.id) || item.kind !== expected.kind || item.id.toLowerCase() !== expected.id.toLowerCase())
      : (!manual || item.kind !== 'manual' || item.id !== null)) throw invalidResponse()
    allowed.add(item.ref)
  }
  if (!payload(value.payload, allowed, live)) throw invalidResponse()
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
  async analyze(profileId: string, workspaceId: string, taskId: string, input: FeedbackAnalysisInput, signal?: AbortSignal, liveKey?: string): Promise<FeedbackAnalysisResult> {
    const mode = liveKey ? 'openai_live' : 'fixture_demo'
    const body = validateFeedbackInput(input, mode)
    const path = `v1/profiles/${entityId(profileId)}/workspaces/${entityId(workspaceId)}/tasks/${entityId(taskId)}/ai/feedback-analysis/`
    return validateFeedbackAnalysis(await apiClient.request<unknown>(path, {
      method: 'POST', body, signal, protected: true, ...(liveKey ? { idempotencyKey: liveKey } : {}),
    }), body.sources, mode, body.feedback_text !== undefined)
  },
}
