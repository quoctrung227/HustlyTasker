/** Fixture-only AI wire contracts. Scope/permission and confirmation stay server-owned. */
import { ApiError, apiClient, invalidResponse } from './client'
import type { TaskPriority } from './work-management'

export const aiPriorities = ['LOW', 'MEDIUM', 'HIGH', 'URGENT'] as const
export const aiScenarioIds = ['subtitle-check-v1', 'task-tree-v1'] as const
export type AiScenarioId = typeof aiScenarioIds[number]
export interface AiTaskNode {
  local_ref: string
  parent_ref: string | null
  title: string
  description: string
  priority: TaskPriority
  proposed_deadline: string | null
  notes: string
}
export interface AiTaskPlan {
  contract_version: 'ai.task-plan.v1'
  tasks: AiTaskNode[]
  assumptions: string[]
  warnings: string[]
}
export interface AiProposal {
  contract_version: 'ai.v1'
  proposal_id: string
  revision: number
  scenario_id: AiScenarioId
  status: 'AVAILABLE' | 'EXPIRED' | 'CONFIRMED'
  mode: 'fixture_demo'
  generated_by_ai: false
  persisted: true
  created_at: string
  expires_at: string
  payload_expires_at: string
  confirmed_at: string | null
  recovery_expires_at: string | null
  payload: AiTaskPlan | null
  created_tasks: Record<string, string> | null
  usage: { input_tokens: 0; billable_output_tokens: 0; cost_usd: '0.000000'; status: 'fixture_zero' }
}
export interface AiAvailability {
  contract_version: 'ai.v1'
  enabled: boolean
  mode: 'fixture_demo'
  generated_by_ai: false
  scenarios: { id: AiScenarioId; label: string; brief: string }[]
  limits: { max_brief_chars: 6000; max_tasks: 20; max_depth: 3; max_request_bytes: 32768 }
}
export interface AiGenerateInput { readonly scenario_id: AiScenarioId; readonly brief?: string }
export interface AiConfirmInput { readonly proposal_revision: number; readonly confirmed: true; readonly payload: AiTaskPlan }

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
export function validateAiPlan(value: unknown): AiTaskPlan {
  if (!record(value) || !exact(value, ['contract_version', 'tasks', 'assumptions', 'warnings']) ||
      value.contract_version !== 'ai.task-plan.v1' || !Array.isArray(value.tasks) ||
      value.tasks.length < 1 || value.tasks.length > 20 || !strings(value.assumptions) || !strings(value.warnings)) throw invalidResponse()
  const nodes = new Map<string, AiTaskNode>()
  for (const item of value.tasks) {
    if (!record(item) || !exact(item, ['local_ref', 'parent_ref', 'title', 'description', 'priority', 'proposed_deadline', 'notes']) ||
        !ref(item.local_ref) || nodes.has(item.local_ref) || !(item.parent_ref === null || ref(item.parent_ref)) ||
        !safeText(item.title, 255, true) || !safeText(item.description, 2000) || !safeText(item.notes, 500) ||
        !aiPriorities.some((priority) => priority === item.priority) || !nullableDate(item.proposed_deadline)) throw invalidResponse()
    nodes.set(item.local_ref, item as unknown as AiTaskNode)
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
  return value as unknown as AiTaskPlan
}
function mapping(value: unknown): value is Record<string, string> {
  if (!record(value)) return false
  const keys = Object.keys(value), values = Object.values(value)
  return keys.length >= 1 && keys.length <= 20 && keys.every(ref) && values.every(uuid) &&
    new Set(values.map((id) => String(id).toLowerCase())).size === values.length
}
export function validateAiProposal(value: unknown, expectedId?: string): AiProposal {
  if (!record(value) || !exact(value, ['contract_version', 'proposal_id', 'revision', 'scenario_id', 'status',
      'mode', 'generated_by_ai', 'persisted', 'created_at', 'expires_at', 'payload_expires_at', 'confirmed_at',
      'recovery_expires_at', 'payload', 'created_tasks', 'usage']) || !sizeWithin(value, 65536) ||
      value.contract_version !== 'ai.v1' || !uuid(value.proposal_id) ||
      (expectedId !== undefined && value.proposal_id.toLowerCase() !== expectedId.toLowerCase()) ||
      !Number.isSafeInteger(value.revision) || Number(value.revision) < 1 || !scenario(value.scenario_id) ||
      value.mode !== 'fixture_demo' || value.generated_by_ai !== false || value.persisted !== true ||
      !isAiDateTime(value.created_at) || !isAiDateTime(value.expires_at) || !isAiDateTime(value.payload_expires_at) ||
      Date.parse(value.expires_at) <= Date.parse(value.created_at) ||
      Date.parse(value.payload_expires_at) < Date.parse(value.expires_at) ||
      !nullableDate(value.confirmed_at) || !nullableDate(value.recovery_expires_at) ||
      !record(value.usage) || !exact(value.usage, ['input_tokens', 'billable_output_tokens', 'cost_usd', 'status']) ||
      value.usage.input_tokens !== 0 || value.usage.billable_output_tokens !== 0 ||
      value.usage.cost_usd !== '0.000000' || value.usage.status !== 'fixture_zero') throw invalidResponse()
  if (value.status === 'AVAILABLE') {
    validateAiPlan(value.payload)
    if (value.created_tasks !== null || value.confirmed_at !== null || value.recovery_expires_at !== null) throw invalidResponse()
  } else if (value.status === 'EXPIRED') {
    if (value.payload !== null || value.created_tasks !== null || value.confirmed_at !== null || value.recovery_expires_at !== null) throw invalidResponse()
  } else if (value.status === 'CONFIRMED') {
    if (value.payload !== null || !mapping(value.created_tasks) || !isAiDateTime(value.confirmed_at) ||
        !isAiDateTime(value.recovery_expires_at) || Date.parse(value.confirmed_at) < Date.parse(value.created_at) ||
        Date.parse(value.recovery_expires_at) <= Date.parse(value.confirmed_at)) throw invalidResponse()
  } else throw invalidResponse()
  return value as unknown as AiProposal
}
export function validateAiAvailability(value: unknown): AiAvailability {
  if (!record(value) || !exact(value, ['contract_version', 'enabled', 'mode', 'generated_by_ai', 'scenarios', 'limits']) ||
      value.contract_version !== 'ai.v1' || typeof value.enabled !== 'boolean' ||
      value.mode !== 'fixture_demo' || value.generated_by_ai !== false || !Array.isArray(value.scenarios) ||
      value.scenarios.length !== 2 || !record(value.limits) ||
      !exact(value.limits, ['max_brief_chars', 'max_tasks', 'max_depth', 'max_request_bytes']) ||
      value.limits.max_brief_chars !== 6000 || value.limits.max_tasks !== 20 ||
      value.limits.max_depth !== 3 || value.limits.max_request_bytes !== 32768 ||
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
    if (!scenario(input.scenario_id) || (input.brief !== undefined && !validateAiBrief(input.brief))) {
      throw new ApiError(400, 'validation', 'Vui lòng chọn mẫu và nhập yêu cầu giả lập hợp lệ.', { brief: 'Nhập yêu cầu giả lập từ 1 đến 6.000 ký tự.' })
    }
    const body = { scenario_id: input.scenario_id, ...(input.brief === undefined ? {} : { brief: input.brief }) }
    requestSize(body)
    return validateAiProposal(await apiClient.request<unknown>(basePath(profileId, workspaceId), {
      method: 'POST', body, idempotencyKey: key, signal, protected: true,
    }))
  },
  async proposal(profileId: string, workspaceId: string, proposalId: string, signal?: AbortSignal): Promise<AiProposal> {
    const id = entityId(proposalId)
    return validateAiProposal(await apiClient.request<unknown>(`${basePath(profileId, workspaceId)}${id}/`, { signal, protected: true }), id)
  },
  async confirm(profileId: string, workspaceId: string, proposalId: string, input: AiConfirmInput, key: string, signal?: AbortSignal): Promise<AiProposal> {
    const id = entityId(proposalId)
    const plan = validateAiPlan(input.payload)
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
}

