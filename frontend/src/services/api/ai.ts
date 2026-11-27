/** AI wire contracts. Scope, permission and confirmation stay server-owned. */
import { ApiError, apiClient, invalidResponse } from './client'
import type { TaskPriority } from './work-management'
import { isEstimatedHours, parseEstimatedHoursInput } from '../../features/tasks/estimated-hours'

export const aiPriorities = ['LOW', 'MEDIUM', 'HIGH', 'URGENT'] as const
export const aiScenarioIds = ['subtitle-check-v1', 'task-tree-v1'] as const
export type AiScenarioId = typeof aiScenarioIds[number]
const liveProviders = {
  openai_live: { provider: 'openai', scenario: 'openai-live-v1', label: 'OpenAI' },
  groq_live: { provider: 'groq', scenario: 'groq-live-v1', label: 'Groq' },
} as const
export type LiveAiMode = keyof typeof liveProviders
export type AiMode = 'fixture_demo' | LiveAiMode
export type AiProvider = typeof liveProviders[LiveAiMode]['provider']
export const isLiveAiMode = (mode: unknown): mode is LiveAiMode => mode === 'openai_live' || mode === 'groq_live'
export const aiProvider = (mode: LiveAiMode) => liveProviders[mode].provider
export const aiProviderLabel = (mode: AiMode | undefined): string => isLiveAiMode(mode) ? liveProviders[mode].label : 'AI'
export type AiUnavailableReason = 'AI_NOT_CONFIGURED' | 'AI_MIGRATION_REQUIRED' | 'AI_DISABLED' | 'PROVIDER_UNAVAILABLE'
export type AiUsage = { input_tokens: number | null; billable_output_tokens: number | null; cost_usd: string | null; status: 'fixture_zero' | 'provider_reported' }
export interface AiTaskNode<Hours = number> {
  local_ref: string
  parent_ref: string | null
  title: string
  description: string
  priority: TaskPriority
  proposed_deadline: string | null
  notes: string
  estimated_hours?: Hours | null
}
export interface AiTaskPlan<Hours = number> {
  contract_version: 'ai.task-plan.v1'
  tasks: AiTaskNode<Hours>[]
  assumptions: string[]
  warnings: string[]
}
export interface AiProposal {
  contract_version: 'ai.v1'
  proposal_id: string
  revision: number
  scenario_id: AiScenarioId | typeof liveProviders[LiveAiMode]['scenario']
  status: 'AVAILABLE' | 'EXPIRED' | 'CONFIRMED' | 'REJECTED'
  mode: AiMode
  generated_by_ai: boolean
  provider?: AiProvider
  model?: string
  persisted: true
  created_at: string
  expires_at: string
  payload_expires_at: string
  confirmed_at: string | null
  recovery_expires_at: string | null
  payload: AiTaskPlan | null
  created_tasks: Record<string, string> | null
  usage: AiUsage
}
export interface AiAvailability {
  contract_version: 'ai.v1'
  enabled: boolean
  mode: AiMode
  generated_by_ai: boolean
  reason?: AiUnavailableReason | null
  scenarios: { id: AiScenarioId; label: string; brief: string }[]
  limits: { max_brief_chars: 6000; max_tasks: 20; max_depth: 0 | 3; max_request_bytes: 32768 }
}
export type AiGenerateInput = { readonly scenario_id: AiScenarioId; readonly brief?: string } |
  { readonly brief: string; readonly task_count?: number; readonly target_deadline?: string | null }
export interface AiConfirmInput { readonly proposal_revision: number; readonly confirmed: true; readonly payload: AiTaskPlan<string | number> }

const record = (value: unknown): value is Record<string, unknown> =>
  value !== null && typeof value === 'object' && !Array.isArray(value)
const uuidPattern = /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i
const refPattern = /^item_[1-9][0-9]{0,2}$/
const uuid = (value: unknown): value is string => typeof value === 'string' && uuidPattern.test(value)
const ref = (value: unknown): value is string => typeof value === 'string' && refPattern.test(value)
const exact = (value: Record<string, unknown>, fields: readonly string[]) =>
  Object.keys(value).length === fields.length && fields.every((key) => Object.hasOwn(value, key))
const safeText = (value: unknown, maximum: number, required = false): value is string =>
  typeof value === 'string' && Array.from(value).length <= maximum && !value.includes('\0') &&
  !/[\uD800-\uDFFF]/u.test(value) && (!required || value.trim().length > 0)
const scenario = (value: unknown): value is AiScenarioId => aiScenarioIds.some((id) => id === value)
const unavailableReasons = ['AI_NOT_CONFIGURED', 'AI_MIGRATION_REQUIRED', 'AI_DISABLED', 'PROVIDER_UNAVAILABLE'] as const
export function aiUnavailableMessage(reason: string | null | undefined): string {
  if (reason === 'AI_NOT_CONFIGURED') return 'AI chưa được cấu hình. Hãy liên hệ quản trị viên để kiểm tra nhà cung cấp AI.'
  if (reason === 'AI_MIGRATION_REQUIRED') return 'AI đang chờ cập nhật cơ sở dữ liệu. Hãy liên hệ quản trị viên.'
  if (reason === 'PROVIDER_UNAVAILABLE') return 'Dịch vụ AI đang gián đoạn. Hãy thử lại sau.'
  return 'Chức năng AI đang tắt trong môi trường này.'
}

export function validAiUsage(value: unknown, mode: AiMode): value is AiUsage {
  if (!record(value) || !exact(value, ['input_tokens', 'billable_output_tokens', 'cost_usd', 'status'])) return false
  if (mode === 'fixture_demo') return value.input_tokens === 0 && value.billable_output_tokens === 0 && value.cost_usd === '0.000000' && value.status === 'fixture_zero'
  const tokens = (count: unknown) => count === null || (typeof count === 'number' && Number.isSafeInteger(count) && count >= 0)
  return value.status === 'provider_reported' && tokens(value.input_tokens) && tokens(value.billable_output_tokens) &&
    (value.cost_usd === null || (typeof value.cost_usd === 'string' && /^\d{1,12}\.\d{6,8}$/.test(value.cost_usd)))
}

/** Python parser-equivalent bounded datetime, without Date.parse's silent date rollover. */
export function isAiDateTime(value: unknown): value is string {
  if (typeof value !== 'string') return false
  const match = /^(\d{4})-(\d\d)-(\d\d)T(\d\d):(\d\d):(\d\d)(?:\.\d{1,6})?(Z|[+-]\d\d:\d\d)$/.exec(value)
  if (!match) return false
  const year = Number(match[1]), month = Number(match[2]), day = Number(match[3])
  const hour = Number(match[4]), minute = Number(match[5]), second = Number(match[6])
  if (year < 1 || month < 1 || month > 12 || day < 1 || hour > 23 || minute > 59 || second > 59) return false
  const leap = year % 400 === 0 || (year % 4 === 0 && year % 100 !== 0)
  const days = [31, leap ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1] ?? 0
  const offset = match[7]
  if (!offset || day > days || (offset !== 'Z' && (Number(offset.slice(1, 3)) > 23 || Number(offset.slice(4, 6)) > 59))) return false
  return Number.isFinite(Date.parse(value))
}
const nullableDate = (value: unknown): value is string | null => value === null || isAiDateTime(value)
function sizeWithin(value: unknown, maximum: number): boolean {
  try {
    const text = JSON.stringify(value)
    return typeof text === 'string' && text.length <= maximum && new TextEncoder().encode(text).byteLength <= maximum
  } catch { return false }
}
function strings(value: unknown): value is string[] {
  return Array.isArray(value) && value.length <= 10 && value.every((item) => safeText(item, 300))
}
export function validateAiBrief(value: string): boolean { return safeText(value, 6000, true) }

/** Validate full proposal output/edit payload. This returns no permissions or persisted state. */
export function validateAiPlan(value: unknown, mode?: AiMode): AiTaskPlan
export function validateAiPlan(value: unknown, mode: AiMode | undefined, edited: true): AiTaskPlan<string | number>
export function validateAiPlan(value: unknown, mode?: AiMode, edited = false): AiTaskPlan<string | number> {
  if (!record(value) || !exact(value, ['contract_version', 'tasks', 'assumptions', 'warnings']) ||
      value.contract_version !== 'ai.task-plan.v1' || !Array.isArray(value.tasks) ||
      value.tasks.length < 1 || value.tasks.length > 20 || !strings(value.assumptions) || !strings(value.warnings)) throw invalidResponse()
  const nodes = new Map<string, AiTaskNode<string | number>>()
  const live = isLiveAiMode(mode)
  for (const item of value.tasks) {
    if (!record(item)) throw invalidResponse()
    const fields = ['local_ref', 'parent_ref', 'title', 'description', 'priority', 'proposed_deadline', 'notes']
    if (live || (mode !== 'fixture_demo' && Object.hasOwn(item, 'estimated_hours'))) fields.push('estimated_hours')
    if (!exact(item, fields) ||
        !ref(item.local_ref) || nodes.has(item.local_ref) || !(item.parent_ref === null || ref(item.parent_ref)) ||
        (live && item.parent_ref !== null) ||
        (Object.hasOwn(item, 'estimated_hours') && !validAiEstimate(item.estimated_hours, edited)) ||
        !safeText(item.title, 255, true) || !safeText(item.description, 2000) || !safeText(item.notes, 500) ||
        !aiPriorities.some((priority) => priority === item.priority) || !nullableDate(item.proposed_deadline)) throw invalidResponse()
    nodes.set(item.local_ref, item as unknown as AiTaskNode<string | number>)
  }
  for (const node of nodes.values()) {
    let current = node, depth = 0
    const visited = new Set<string>([node.local_ref])
    while (current.parent_ref !== null) {
      const parent = nodes.get(current.parent_ref)
      if (!parent || visited.has(parent.local_ref) || ++depth > 3) throw invalidResponse()
      visited.add(parent.local_ref)
      current = parent
    }
  }
  if (!sizeWithin(value, 65536)) throw invalidResponse()
  return value as unknown as AiTaskPlan<string | number>
}
function validAiEstimate(value: unknown, edited: boolean): boolean {
  if (value === null) return true
  if (edited && isEstimatedHours(value)) return true
  return typeof value === 'number' && Number.isFinite(value) && value >= 0.01 && value <= 1000 &&
    (!edited || parseEstimatedHoursInput(String(value)) !== undefined)
}
function mapping(value: unknown): value is Record<string, string> {
  if (!record(value)) return false
  const keys = Object.keys(value), values = Object.values(value)
  return keys.length >= 1 && keys.length <= 20 && keys.every(ref) && values.every(uuid) &&
    new Set(values.map((id) => String(id).toLowerCase())).size === values.length
}
export function validateAiProposal(value: unknown, expectedId?: string): AiProposal {
  if (!record(value)) throw invalidResponse()
  const { mode } = value
  const live = isLiveAiMode(mode)
  if (!live && mode !== 'fixture_demo') throw invalidResponse()
  if (!exact(value, ['contract_version', 'proposal_id', 'revision', 'scenario_id', 'status',
      'mode', 'generated_by_ai', 'persisted', 'created_at', 'expires_at', 'payload_expires_at', 'confirmed_at',
      'recovery_expires_at', 'payload', 'created_tasks', 'usage', ...(live ? ['provider', 'model'] : [])]) || !sizeWithin(value, 65536) ||
      value.contract_version !== 'ai.v1' || !uuid(value.proposal_id) ||
      (expectedId !== undefined && value.proposal_id.toLowerCase() !== expectedId.toLowerCase()) ||
      !Number.isSafeInteger(value.revision) || Number(value.revision) < 1 ||
      (live ? value.scenario_id !== liveProviders[mode].scenario || value.provider !== aiProvider(mode) || !safeText(value.model, 120, true) : !scenario(value.scenario_id)) ||
      value.generated_by_ai !== live || value.persisted !== true ||
      !isAiDateTime(value.created_at) || !isAiDateTime(value.expires_at) || !isAiDateTime(value.payload_expires_at) ||
      Date.parse(value.expires_at) <= Date.parse(value.created_at) ||
      Date.parse(value.payload_expires_at) < Date.parse(value.expires_at) ||
      !nullableDate(value.confirmed_at) || !nullableDate(value.recovery_expires_at) || !validAiUsage(value.usage, mode)) throw invalidResponse()
  if (value.status === 'AVAILABLE') {
    validateAiPlan(value.payload, mode)
    if (value.created_tasks !== null || value.confirmed_at !== null || value.recovery_expires_at !== null) throw invalidResponse()
  } else if (value.status === 'EXPIRED' || (live && value.status === 'REJECTED')) {
    if (value.payload !== null || value.created_tasks !== null || value.confirmed_at !== null || value.recovery_expires_at !== null) throw invalidResponse()
  } else if (value.status === 'CONFIRMED') {
    if (value.payload !== null || !mapping(value.created_tasks) || !isAiDateTime(value.confirmed_at) ||
        !isAiDateTime(value.recovery_expires_at) || Date.parse(value.confirmed_at) < Date.parse(value.created_at) ||
        Date.parse(value.recovery_expires_at) <= Date.parse(value.confirmed_at)) throw invalidResponse()
  } else throw invalidResponse()
  return value as unknown as AiProposal
}
export function validateAiAvailability(value: unknown): AiAvailability {
  if (!record(value)) throw invalidResponse()
  const live = isLiveAiMode(value.mode)
  if (!live && value.mode !== 'fixture_demo') throw invalidResponse()
  if (!exact(value, ['contract_version', 'enabled', 'mode', 'generated_by_ai', 'scenarios', 'limits', ...(live ? ['reason'] : [])]) ||
      value.contract_version !== 'ai.v1' || typeof value.enabled !== 'boolean' ||
      value.generated_by_ai !== live || !Array.isArray(value.scenarios) ||
      value.scenarios.length !== (live ? 0 : 2) || !record(value.limits) ||
      (live && (value.enabled ? value.reason !== null : !unavailableReasons.some((reason) => reason === value.reason))) ||
      !exact(value.limits, ['max_brief_chars', 'max_tasks', 'max_depth', 'max_request_bytes']) ||
      value.limits.max_brief_chars !== 6000 || value.limits.max_tasks !== 20 ||
      value.limits.max_depth !== (live ? 0 : 3) || value.limits.max_request_bytes !== 32768 ||
      !sizeWithin(value, 65536)) throw invalidResponse()
  const ids = new Set<string>()
  for (const item of value.scenarios) {
    if (!record(item) || !exact(item, ['id', 'label', 'brief']) || !scenario(item.id) ||
        ids.has(item.id) || !safeText(item.label, 255, true) || !validateAiBrief(item.brief as string)) throw invalidResponse()
    ids.add(item.id)
  }
  return value as unknown as AiAvailability
}
function entityId(value: string): string {
  if (!uuid(value)) throw new ApiError(404, 'not-found', 'Không tìm thấy nội dung hoặc bạn không có quyền truy cập.')
  return value.toLowerCase()
}
function basePath(profileId: string, workspaceId: string) {
  return `v1/profiles/${entityId(profileId)}/workspaces/${entityId(workspaceId)}/ai/task-proposals/`
}
function requestSize(value: unknown) {
  if (!sizeWithin(value, 32768)) throw new ApiError(400, 'validation', 'Nội dung vượt quá giới hạn 32 KiB. Vui lòng rút gọn đề xuất.')
}
export const aiKeys = {
  scope: (userId: string, profileId: string, workspaceId: string) => ['ai', userId, profileId, workspaceId] as const,
  availability: (userId: string, profileId: string, workspaceId: string) => ['ai', userId, profileId, workspaceId, 'availability'] as const,
  proposal: (userId: string, profileId: string, workspaceId: string, proposalId: string) => ['ai', userId, profileId, workspaceId, 'proposal', proposalId] as const,
}
export const aiApi = {
  async availability(profileId: string, workspaceId: string, signal?: AbortSignal): Promise<AiAvailability> {
    const value = await apiClient.request<unknown>(basePath(profileId, workspaceId), { method: 'OPTIONS', signal, protected: true })
    if (!record(value)) throw invalidResponse()
    return validateAiAvailability(value.ai)
  },
  async generate(profileId: string, workspaceId: string, input: AiGenerateInput, key: string, signal?: AbortSignal): Promise<AiProposal> {
    const fixture = 'scenario_id' in input
    if (fixture ? (!scenario(input.scenario_id) || (input.brief !== undefined && !validateAiBrief(input.brief))) : !validateAiBrief(input.brief)) {
      throw new ApiError(400, 'validation', 'Mô tả yêu cầu chưa hợp lệ.', { brief: 'Nhập yêu cầu từ 1 đến 6.000 ký tự.' })
    }
    if (!fixture && input.task_count !== undefined && (!Number.isInteger(input.task_count) || input.task_count < 1 || input.task_count > 20)) {
      throw new ApiError(400, 'validation', 'Số công việc chưa hợp lệ.', { task_count: 'Nhập số nguyên từ 1 đến 20.' })
    }
    if (!fixture && input.target_deadline !== undefined && !nullableDate(input.target_deadline)) {
      throw new ApiError(400, 'validation', 'Thời hạn chung chưa hợp lệ.', { target_deadline: 'Vui lòng kiểm tra thời hạn chung.' })
    }
    const body = fixture ? { scenario_id: input.scenario_id, ...(input.brief === undefined ? {} : { brief: input.brief }) }
      : { brief: input.brief, ...(input.task_count === undefined ? {} : { task_count: input.task_count }),
        ...(input.target_deadline === undefined ? {} : { target_deadline: input.target_deadline }) }
    requestSize(body)
    const proposal = validateAiProposal(await apiClient.request<unknown>(basePath(profileId, workspaceId), {
      method: 'POST', body, idempotencyKey: key, signal, protected: true,
    }))
    if (fixture ? proposal.mode !== 'fixture_demo' : !isLiveAiMode(proposal.mode)) throw invalidResponse()
    return proposal
  },
  async proposal(profileId: string, workspaceId: string, proposalId: string, signal?: AbortSignal): Promise<AiProposal> {
    const id = entityId(proposalId)
    return validateAiProposal(await apiClient.request<unknown>(`${basePath(profileId, workspaceId)}${id}/`, { signal, protected: true }), id)
  },
  async confirm(profileId: string, workspaceId: string, proposalId: string, input: AiConfirmInput, key: string, signal?: AbortSignal): Promise<AiProposal> {
    const id = entityId(proposalId)
    const plan = validateAiPlan(input.payload, undefined, true)
    if (input.confirmed !== true || !Number.isSafeInteger(input.proposal_revision) || input.proposal_revision < 1) {
      throw new ApiError(400, 'validation', 'Cần xác nhận rõ ràng phiên bản đề xuất hiện tại.')
    }
    const body = { proposal_revision: input.proposal_revision, confirmed: true, payload: plan }
    requestSize(body)
    const proposal = validateAiProposal(await apiClient.request<unknown>(`${basePath(profileId, workspaceId)}${id}/confirm/`, {
      method: 'POST', body, idempotencyKey: key, signal, protected: true,
    }), id)
    if (proposal.status !== 'CONFIRMED') throw invalidResponse()
    return proposal
  },
  async reject(profileId: string, workspaceId: string, proposalId: string, revision: number, signal?: AbortSignal): Promise<AiProposal> {
    const id = entityId(proposalId)
    if (!Number.isSafeInteger(revision) || revision < 1) throw invalidResponse()
    const proposal = validateAiProposal(await apiClient.request<unknown>(`${basePath(profileId, workspaceId)}${id}/reject/`, {
      method: 'POST', body: { proposal_revision: revision }, signal, protected: true,
    }), id)
    if (proposal.status !== 'REJECTED' || !isLiveAiMode(proposal.mode)) throw invalidResponse()
    return proposal
  },
}

