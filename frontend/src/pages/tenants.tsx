import { useQuery } from '@tanstack/react-query'
import { Link, useParams, useSearchParams } from 'react-router'
import { ArrowRightIcon, ArrowUpRightIcon, BuildingsIcon, CalendarDotsIcon, StackIcon, ArrowLeftIcon } from '@phosphor-icons/react'
import { Alert, Badge, Card, EmptyState, ErrorState, PageSkeleton, Pagination } from '../components/ui'
import { PageHeader, dateLabel, periodLabel } from '../components/page'
import { queryKeys, tenantApi } from '../services/api/queries'
import type { Profile, Workspace } from '../services/api/types'
import { WorkspaceCreate } from '../features/workspaces/WorkspaceCreate'
import { WorkspaceActions } from '../features/workspaces/WorkspaceActions'
import { WorkspaceMembers } from '../features/workspaces/WorkspaceMembers'
import { useWorkContext } from '../features/workspaces/useWorkContext'
import { workApi } from '../services/api/work-management'

function usePage() {
  const [search, setSearch] = useSearchParams()
  const value = Number(search.get('page') || '1')
  const page = Number.isSafeInteger(value) && value > 0 ? value : 1
  return { page, setPage: (next: number) => setSearch(next === 1 ? {} : { page: String(next) }) }
}

function ProfileCard({ profile }: { profile: Profile }) {
  return <Link to={`/profiles/${profile.id}`} className="profile-card"><div className="profile-card__top"><span className="organization-icon"><BuildingsIcon aria-hidden="true" /></span><Badge status={profile.status} /></div><h2>{profile.name}</h2><p>Tạo ngày {dateLabel(profile.created_at)}</p><span className="profile-card__bottom">Khám phá không gian<ArrowUpRightIcon aria-hidden="true" /></span></Link>
}

export function ProfilesPage() {
  const { page, setPage } = usePage()
  const query = useQuery({ queryKey: queryKeys.profiles(page), queryFn: ({ signal }) => tenantApi.profiles(page, signal) })
  return <><PageHeader eyebrow="NHÓM CỦA BẠN" title="Tổ chức" description="Những người cùng mục tiêu. Những không gian cùng làm việc." />
    <div className="list-toolbar"><p>{query.data ? <><strong>{query.data.count}</strong> tổ chức bạn có thể truy cập</> : 'Danh sách tổ chức'}</p><span className="subtle-label"><ShieldLabel />Chỉ dữ liệu được cấp quyền</span></div>
    {query.isPending ? <PageSkeleton label="Đang tải tổ chức…" /> : query.isError ? <ErrorState error={query.error} onRetry={() => void query.refetch()} /> : query.data.results.length === 0 ? <EmptyState title="Chưa có tổ chức nào" description="Bạn chưa có quyền truy cập tổ chức nào. Hãy liên hệ người quản trị để được mời tham gia nhóm." /> : <><div className="profile-grid">{query.data.results.map((profile) => <ProfileCard key={profile.id} profile={profile} />)}</div><Pagination page={page} count={query.data.count} onPageChange={setPage} /></>}
  </>
}

function ShieldLabel() { return <span className="status-dot" aria-hidden="true" /> }

function WorkspaceRows({ workspaces }: { workspaces: Workspace[] }) {
  return <ul className="workspace-list" aria-label="Không gian làm việc">{workspaces.map((workspace) => <li key={workspace.id}><Link className="workspace-row" to={`/profiles/${workspace.profile_id}/workspaces/${workspace.id}`}><span className="workspace-row__icon"><CalendarDotsIcon aria-hidden="true" /></span><div className="workspace-row__main"><span className="workspace-row__period">{periodLabel(workspace.period)}</span><h3>{workspace.name}</h3><p>{workspace.description || 'Không gian cộng tác của nhóm.'}</p></div><Badge status={workspace.status} /><ArrowUpRightIcon className="workspace-row__arrow" aria-hidden="true" /></Link></li>)}</ul>
}

function ReadOnlyNote() { return <p className="read-note"><StackIcon aria-hidden="true" />Chỉ dữ liệu trong phạm vi truy cập của bạn được hiển thị. Quyền thao tác được kiểm tra lại khi lưu.</p> }

export function ProfileDetailPage() {
  const { profileId = '' } = useParams()
  const profile = useQuery({ queryKey: queryKeys.profile(profileId), queryFn: ({ signal }) => tenantApi.profile(profileId, signal) })
  const workspaces = useQuery({ queryKey: queryKeys.workspaces(profileId), queryFn: ({ signal }) => tenantApi.workspaces(profileId, 1, signal), enabled: profile.isSuccess })
  if (profile.isPending) return <PageSkeleton label="Đang tải thông tin tổ chức…" />
  if (profile.isError) return <><PageHeader title="Nội dung không khả dụng" back={{ to: '/profiles', label: 'Tổ chức' }} /><ErrorState error={profile.error} onRetry={() => void profile.refetch()} /></>
  return <><PageHeader eyebrow="THÔNG TIN TỔ CHỨC" title={profile.data.name} description="Không gian chung cho những đóng góp của cả nhóm." back={{ to: '/profiles', label: 'Tổ chức' }} action={<Badge status={profile.data.status} />} />
    <Card className="metadata-card"><span className="organization-icon"><BuildingsIcon aria-hidden="true" /></span><dl><div><dt>Ngày tạo</dt><dd>{dateLabel(profile.data.created_at)}</dd></div><div><dt>Cập nhật lần cuối</dt><dd>{dateLabel(profile.data.updated_at)}</dd></div><div><dt>Không gian truy cập được</dt><dd>{workspaces.data?.count ?? '—'}</dd></div></dl></Card>
    <section className="section-block"><div className="section-heading"><div><p className="eyebrow">NHỊP LÀM VIỆC HẰNG THÁNG</p><h2>Không gian làm việc</h2></div><Link className="text-link" to={`/profiles/${profileId}/workspaces`}>Xem tất cả<ArrowRightIcon aria-hidden="true" /></Link></div>
      {workspaces.isPending ? <PageSkeleton label="Đang tải không gian…" /> : workspaces.isError ? <ErrorState error={workspaces.error} onRetry={() => void workspaces.refetch()} /> : workspaces.data.results.length === 0 ? <EmptyState title="Chưa có không gian làm việc" description="Các không gian bạn được cấp quyền trong tổ chức sẽ hiển thị tại đây." /> : <WorkspaceRows workspaces={workspaces.data.results.slice(0, 3)} />}
    </section><ReadOnlyNote />
  </>
}

export function WorkspacesPage() {
  const { profileId = '' } = useParams()
  const { page, setPage } = usePage()
  const context = useWorkContext(profileId)
  const profile = context.profile
  const query = useQuery({ queryKey: queryKeys.workspaces(profileId, page), queryFn: ({ signal }) => tenantApi.workspaces(profileId, page, signal), enabled: profile.isSuccess })
  return <><PageHeader eyebrow={profile.data?.name || 'TỔ CHỨC'} title="Không gian làm việc" description="Mỗi tháng là một không gian. Giữ cả nhóm trong cùng ngữ cảnh." back={{ to: `/profiles/${profileId}`, label: 'Thông tin tổ chức' }} action={<WorkspaceCreate profileId={profileId} canCreate={context.active && context.capabilities.data?.createWorkspace} onCreate={(input, signal) => workApi.createWorkspace(profileId, input, signal)} onCreated={() => context.invalidate(true)} onDenied={context.denied} />} />
    {profile.isError ? <ErrorState error={profile.error} onRetry={() => void profile.refetch()} /> : profile.isPending || query.isPending ? <PageSkeleton label="Đang tải không gian…" /> : query.isError ? <ErrorState error={query.error} onRetry={() => void query.refetch()} /> : <><div className="list-toolbar"><p><strong>{query.data.count}</strong> không gian truy cập được</p><span className="subtle-label">Bao gồm không gian đã lưu trữ</span></div>{query.data.results.length === 0 ? <EmptyState title="Chưa có không gian làm việc" description="Chưa có không gian nào trong phạm vi truy cập của bạn. Liên hệ người quản trị nếu bạn cần tham gia." /> : <WorkspaceRows workspaces={query.data.results} />}<Pagination page={page} count={query.data.count} onPageChange={setPage} /></>}
    <ReadOnlyNote /></>
}

export function WorkspaceDetailPage() {
  const { profileId = '', workspaceId = '' } = useParams()
  const context = useWorkContext(profileId, workspaceId)
  const query = context.workspace
  if (query.isError || context.profile.isError) return <><PageHeader title="Nội dung không khả dụng" back={{ to: `/profiles/${profileId}/workspaces`, label: 'Không gian làm việc' }} /><ErrorState error={query.error || context.profile.error} onRetry={() => { void query.refetch(); void context.profile.refetch() }} /></>
  if (!query.data) return <PageSkeleton label="Đang tải không gian…" />
  const workspace = query.data
  return <><PageHeader eyebrow={periodLabel(workspace.period)} title={workspace.name} description="Thông tin không gian làm việc của nhóm." back={{ to: `/profiles/${profileId}/workspaces`, label: 'Không gian làm việc' }} action={<Badge status={workspace.status} />} />
    <WorkspaceActions profileId={profileId} workspace={workspace} capabilities={{ canEdit: context.active && context.capabilities.data?.manageWorkspace, canArchive: context.profile.data?.status === 'ACTIVE' && context.capabilities.data?.manageLifecycle, canRestore: context.profile.data?.status === 'ACTIVE' && context.capabilities.data?.manageLifecycle }} onUpdate={(input, signal) => workApi.updateWorkspace(profileId, workspaceId, input, signal)} onLifecycle={(action, signal) => workApi.setWorkspaceStatus(profileId, workspaceId, action, signal)} onSaved={() => context.invalidate(true)} onDenied={context.denied} />
    {!context.active && <Alert>Không gian hoặc tổ chức đã lưu trữ. Công việc chỉ được xem theo quyền hiện tại.</Alert>}
    <Card className="workspace-task-link"><div><p className="eyebrow">CÙNG LÀM VIỆC</p><h2>Công việc của không gian</h2><p>Theo dõi công việc, công việc con, thời hạn và mức ưu tiên.</p></div><Link className="button button--primary" to={`/profiles/${profileId}/workspaces/${workspaceId}/tasks`}>Xem công việc<ArrowRightIcon aria-hidden="true" /></Link></Card>
    <div className="workspace-detail-grid"><Card className="workspace-about"><span className="organization-icon"><CalendarDotsIcon aria-hidden="true" /></span><h2>Về không gian này</h2><p className="preserve-text">{workspace.description || 'Không gian này chưa có mô tả.'}</p><Link className="text-link" to={`/profiles/${profileId}`}><ArrowLeftIcon aria-hidden="true" />Xem tổ chức</Link></Card><Card className="workspace-facts"><h2>Thông tin chung</h2><dl><div><dt>Kỳ làm việc</dt><dd>{periodLabel(workspace.period)}</dd></div><div><dt>Trạng thái</dt><dd><Badge status={workspace.status} /></dd></div><div><dt>Ngày tạo</dt><dd>{dateLabel(workspace.created_at)}</dd></div><div><dt>Cập nhật gần nhất</dt><dd>{dateLabel(workspace.updated_at)}</dd></div></dl></Card></div><ReadOnlyNote />
    <WorkspaceMembers key={`${profileId}:${workspaceId}`} profileId={profileId} workspaceId={workspaceId} allowed={context.active && context.capabilities.data?.manageWorkspace === true} />
  </>
}
