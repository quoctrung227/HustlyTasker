import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Card, EmptyState, ErrorState, PageSkeleton, Pagination } from '../../components/ui'
import { workApi, workKeys } from '../../services/api/work-management'

export function WorkspaceMembers({ profileId, workspaceId, allowed }: { profileId: string; workspaceId: string; allowed: boolean }) {
  const [page, setPage] = useState(1)
  const query = useQuery({ queryKey: workKeys.members(profileId, workspaceId, page), queryFn: ({ signal }) => workApi.members(profileId, workspaceId, page, signal), enabled: allowed })
  if (!allowed) return null
  return <section className="section-block" aria-labelledby="workspace-members-heading"><div className="section-heading"><div><p className="eyebrow">NHỮNG NGƯỜI CÙNG THỰC HIỆN</p><h2 id="workspace-members-heading">Thành viên không gian</h2></div></div><p className="read-note">Thành viên và vai trò trong không gian làm việc được phép quản lý.</p>
    {query.isPending ? <PageSkeleton /> : query.isError ? <ErrorState error={query.error} onRetry={() => void query.refetch()} /> : <>{query.data.results.length ? <Card><ul className="member-list">{query.data.results.map((member) => <li key={member.id}><strong>{member.display_label}</strong><span>{({ ADMIN: 'Quản lý', MEMBER: 'Editor', VIEWER: 'Chỉ xem' })[member.role]} · {member.is_active ? 'Đang hoạt động' : 'Không hoạt động'}</span></li>)}</ul></Card> : <EmptyState title="Chưa có thành viên" description="Danh sách thành viên được phép xem sẽ hiển thị tại đây." />}<Pagination page={page} count={query.data.count} onPageChange={setPage} /></>}
  </section>
}
