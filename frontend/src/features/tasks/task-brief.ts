/** Exact Task brief values. URLs are validated locally, never fetched. */
export const TASK_DOCUMENT_URL_MAX_LENGTH = 2048
export const MAX_ESTIMATED_COMPENSATION_VND = '999999999999999999'

export const taskDocumentFields = [
  { key: 'raw_video_url', label: 'Link video gốc (raw)', action: 'Mở video gốc' },
  { key: 'reference_video_url', label: 'Link video tham khảo', action: 'Mở video tham khảo' },
  { key: 'template_project_url', label: 'Link dự án mẫu', action: 'Mở dự án mẫu' },
  { key: 'script_url', label: 'Link kịch bản', action: 'Mở kịch bản' },
] as const
export type TaskDocumentField = typeof taskDocumentFields[number]['key']
export type TaskBrief = Partial<Record<TaskDocumentField, string | null>> & { estimated_compensation_vnd?: string | null }

export function validTaskDocumentUrl(value: unknown): value is string {
  if (typeof value !== 'string' || value.length > TASK_DOCUMENT_URL_MAX_LENGTH || value !== value.trim() || /\s|[\uD800-\uDFFF]/u.test(value) ||
    Array.from(value).some((character) => character.charCodeAt(0) <= 32 || character.charCodeAt(0) === 127)) return false
  try {
    const url = new URL(value)
    return /^https?:$/.test(url.protocol) && !!url.hostname
  } catch { return false }
}

export function parseTaskDocumentUrl(value: string): string | null {
  const trimmed = value.trim()
  if (!trimmed) return null
  if (!validTaskDocumentUrl(trimmed)) throw new TypeError('Invalid Task document URL.')
  return trimmed
}

export function validEstimatedCompensation(value: unknown): value is string {
  return typeof value === 'string' && /^(0|[1-9]\d{0,17})$/.test(value)
}

export function parseEstimatedCompensation(value: string): string | null {
  const trimmed = value.trim()
  if (!trimmed) return null
  if (!/^(?:\d+|\d{1,3}(?:\.\d{3})+)$/.test(trimmed)) throw new TypeError('Invalid estimated compensation.')
  const digits = trimmed.replaceAll('.', '').replace(/^0+(?=\d)/, '')
  if (!validEstimatedCompensation(digits)) throw new TypeError('Invalid estimated compensation.')
  return digits
}

/** No Number/float conversion, including values above JavaScript's safe integer. */
export function formatEstimatedCompensation(value: string | null | undefined): string {
  if (value === null || value === undefined) return ''
  if (!validEstimatedCompensation(value)) throw new TypeError('Invalid estimated compensation.')
  return value.replace(/\B(?=(\d{3})+(?!\d))/g, '.')
}

export function isTaskBrief(value: Record<string, unknown>): boolean {
  return taskDocumentFields.every(({ key }) => value[key] === undefined || value[key] === null || validTaskDocumentUrl(value[key])) &&
    (value.estimated_compensation_vnd === undefined || value.estimated_compensation_vnd === null || validEstimatedCompensation(value.estimated_compensation_vnd))
}

/** Null also represents server redaction; never fill it from an older Task snapshot. */
export function normalizeTaskBrief(value: TaskBrief): Required<TaskBrief> {
  return {
    raw_video_url: value.raw_video_url ?? null,
    reference_video_url: value.reference_video_url ?? null,
    template_project_url: value.template_project_url ?? null,
    script_url: value.script_url ?? null,
    estimated_compensation_vnd: value.estimated_compensation_vnd ?? null,
  }
}
