import type { TrashItem } from '../services/api/trash'

export const trashIds = {
  user: '00000000-0000-4000-8000-000000000901',
  profile: '00000000-0000-4000-8000-000000000902',
  workspace: '00000000-0000-4000-8000-000000000903',
  task: '00000000-0000-4000-8000-000000000904',
}
export function trashItem(changes: Partial<TrashItem> = {}): TrashItem {
  return {
    id: trashIds.task, object_type: 'TASK', title: 'Công việc trong Thùng rác', profile_id: trashIds.profile,
    workspace_id: trashIds.workspace, parent_id: null, deleted_by: { display_name: 'Quản lý kiểm thử' },
    deleted_at: '2026-10-01T10:00:00Z', purge_after: '2026-10-31T10:00:00Z', days_remaining: 5,
    parent_deleted: false, affected_counts: { tasks: 1, assignments: 1, reviews: 0 }, can_restore: true, can_purge: false,
    restore_blocker: null, purge_blockers: [{ code: 'RETENTION_NOT_ELAPSED', message: 'Chưa đủ thời hạn lưu giữ.' }], ...changes,
  }
}
