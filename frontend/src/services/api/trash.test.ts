import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { apiClient } from './client'
import { parseTrashItem, trashApi, trashKeys } from './trash'
import type { TrashObjectType } from './trash'
import { trashIds, trashItem } from '../../test/trash-fixtures'

const json = (value: unknown, status = 200) => new Response(JSON.stringify(value), { status, headers: { 'Content-Type': 'application/json' } })
const page = (results = [trashItem()]) => ({ count: results.length, next: null, previous: null, results })
function requestAt(mock: ReturnType<typeof vi.fn>, index: number) {
  const args = mock.mock.calls[index]
  if (!args) throw new Error('Expected request was not made.')
  return { url: String(args[0]), options: args[1] as RequestInit }
}
beforeEach(() => { apiClient.clearCsrf(); apiClient.setForbiddenHandler(null) })
afterEach(() => { vi.unstubAllGlobals(); apiClient.clearCsrf(); apiClient.setForbiddenHandler(null) })

describe('Trash DTO and request boundaries', () => {
  it('parses safe Task, Workspace and Profile identity contexts', () => {
    expect(parseTrashItem(trashItem()).object_type).toBe('TASK')
    expect(parseTrashItem(trashItem({ id: trashIds.workspace, object_type: 'WORKSPACE' })).object_type).toBe('WORKSPACE')
    expect(parseTrashItem(trashItem({ id: trashIds.profile, object_type: 'PROFILE', workspace_id: null })).object_type).toBe('PROFILE')
  })
  it.each([
    { object_type: 'USER' }, { id: 'not-a-reference' }, { profile_id: null }, { deleted_at: 'invalid' },
    { purge_after: '2020-01-01T00:00:00Z' }, { days_remaining: -1 }, { can_restore: 'true' },
    { can_purge: 1 }, { parent_deleted: 'false' }, { affected_counts: { tasks: -1 } },
    { deleted_by: 'someone' }, { purge_blockers: [{ code: 'OTHER', message: 1 }] }, { workspace_id: null },
  ])('rejects malformed or permission-ambiguous DTO %j', (change) => {
    expect(() => parseTrashItem({ ...trashItem(), ...change })).toThrow()
  })
  it('rejects a Profile or Workspace returned under another identity', () => {
    expect(() => parseTrashItem(trashItem({ object_type: 'PROFILE' }))).toThrow()
    expect(() => parseTrashItem(trashItem({ object_type: 'WORKSPACE' }))).toThrow()
  })
  it('builds local paginated server-search URLs and never follows server pagination links', async () => {
    const fetch = vi.fn().mockResolvedValue(json({ ...page(), next: 'https://untrusted.example.test/elsewhere' }))
    vi.stubGlobal('fetch', fetch)
    await trashApi.list({ object_type: 'TASK', search: 'công việc & thử', profile_id: trashIds.profile }, 2)
    const target = new URL(requestAt(fetch, 0).url, 'http://localhost')
    expect(target.pathname).toBe('/api/v1/trash/')
    expect(target.searchParams.get('object_type')).toBe('TASK')
    expect(target.searchParams.get('search')).toBe('công việc & thử')
    expect(target.searchParams.get('profile_id')).toBe(trashIds.profile)
    expect(target.searchParams.get('page')).toBe('2')
    expect(requestAt(fetch, 0).options).toMatchObject({ method: 'GET', credentials: 'same-origin', cache: 'no-store', redirect: 'error' })
    expect(fetch).toHaveBeenCalledTimes(1)
  })
  it('rejects a list containing another requested Profile or object type', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(json(page())))
    await expect(trashApi.list({ profile_id: trashIds.user })).rejects.toMatchObject({ kind: 'invalid-response' })
    await expect(trashApi.list({ object_type: 'PROFILE' })).rejects.toMatchObject({ kind: 'invalid-response' })
  })
  it.each([0, -1, Number.NaN, 1.5])('does not request invalid page %s', async (value) => {
    const fetch = vi.fn(); vi.stubGlobal('fetch', fetch)
    await expect(trashApi.list({}, value)).rejects.toThrow()
    expect(fetch).not.toHaveBeenCalled()
  })
  it('rejects invalid search/type before network access', async () => {
    const fetch = vi.fn(); vi.stubGlobal('fetch', fetch)
    await expect(trashApi.list({ search: 'a'.repeat(101) })).rejects.toThrow()
    await expect(trashApi.list({ search: `bad${String.fromCharCode(0)}` })).rejects.toThrow()
    await expect(trashApi.list({ object_type: 'USER' as TrashObjectType })).rejects.toThrow()
    expect(fetch).not.toHaveBeenCalled()
  })
  it.each([0x7F, 0x80, 0x9F, 0xD800, 0xFFFD])('rejects invalid Unicode search U+%s before network access', async (point) => {
    const fetch = vi.fn(); vi.stubGlobal('fetch', fetch)
    await expect(trashApi.list({ search: `bad${String.fromCodePoint(point)}` })).rejects.toThrow()
    expect(fetch).not.toHaveBeenCalled()
  })
  it('sends authenticated-CSRF soft delete and checks the returned target', async () => {
    const fetch = vi.fn().mockResolvedValueOnce(json({ csrf_token: 'a'.repeat(64) })).mockResolvedValueOnce(json(trashItem()))
    vi.stubGlobal('fetch', fetch)
    const controller = new AbortController()
    await expect(trashApi.delete('TASK', trashIds.task, controller.signal)).resolves.toMatchObject({ id: trashIds.task })
    expect(requestAt(fetch, 1).url).toBe(`/api/v1/trash/task/${trashIds.task}/delete/`)
    expect(requestAt(fetch, 1).options).toMatchObject({ method: 'POST', credentials: 'same-origin', body: '{}', signal: controller.signal })
    expect(requestAt(fetch, 1).options.headers).toMatchObject({ 'X-CSRFToken': 'a'.repeat(64), 'Content-Type': 'application/json' })
  })
  it('does not accept a mismatched soft-delete confirmation payload', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValueOnce(json({ csrf_token: 'a'.repeat(64) })).mockResolvedValueOnce(json(trashItem({ id: trashIds.user }))))
    await expect(trashApi.delete('TASK', trashIds.task)).rejects.toMatchObject({ kind: 'invalid-response' })
  })
  it('restores with an empty strict body and accepts204', async () => {
    const fetch = vi.fn().mockResolvedValueOnce(json({ csrf_token: 'a'.repeat(64) })).mockResolvedValueOnce(new Response(null, { status: 204 }))
    vi.stubGlobal('fetch', fetch)
    await trashApi.restore('TASK', trashIds.task)
    expect(requestAt(fetch, 1).url).toBe(`/api/v1/trash/task/${trashIds.task}/restore/`)
    expect(requestAt(fetch, 1).options.body).toBe('{}')
  })
  it('sends exact-name confirmation for Workspace purge', async () => {
    const fetch = vi.fn().mockResolvedValueOnce(json({ csrf_token: 'a'.repeat(64) })).mockResolvedValueOnce(new Response(null, { status: 204 }))
    vi.stubGlobal('fetch', fetch)
    await trashApi.purge({ object_type: 'WORKSPACE', id: trashIds.workspace, title: 'Không gian cần xóa' }, 'Không gian cần xóa')
    expect(requestAt(fetch, 1).url).toBe(`/api/v1/trash/workspace/${trashIds.workspace}/purge/`)
    expect(JSON.parse(String(requestAt(fetch, 1).options.body))).toEqual({ confirm: true, confirmation_name: 'Không gian cần xóa' })
  })
  it.each([400, 403, 404, 409, 429, 500])('preserves error%d and never replays an unsafe request', async (status) => {
    const fetch = vi.fn().mockResolvedValueOnce(json({ csrf_token: 'a'.repeat(64) })).mockResolvedValueOnce(json({ detail: 'Unavailable' }, status))
    vi.stubGlobal('fetch', fetch)
    await expect(trashApi.restore('TASK', trashIds.task)).rejects.toMatchObject({ status })
    expect(fetch).toHaveBeenCalledTimes(2)
  })
  it('separates query caches by User, filters and page', () => {
    expect(trashKeys.list(trashIds.user, {}, 1)).not.toEqual(trashKeys.list(trashIds.profile, {}, 1))
    expect(trashKeys.list(trashIds.user, {}, 1)).not.toEqual(trashKeys.list(trashIds.user, { object_type: 'TASK' }, 1))
    expect(trashKeys.list(trashIds.user, {}, 1)).not.toEqual(trashKeys.list(trashIds.user, {}, 2))
  })
})
