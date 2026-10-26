import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router'
import { ArrowRightIcon, BuildingsIcon, ShieldCheckIcon, CalendarDotsIcon, ArrowUpRightIcon } from '@phosphor-icons/react'
import { Badge, Card, EmptyState, ErrorState, PageSkeleton } from '../components/ui'
import { PageHeader } from '../components/page'
import { useAuth } from '../features/auth/AuthProvider'
import { queryKeys, tenantApi } from '../services/api/queries'

export function DashboardPage() {
  const { user } = useAuth()
  const profiles = useQuery({ queryKey: queryKeys.profiles(), queryFn: ({ signal }) => tenantApi.profiles(1, signal) })
  const name = user?.first_name || user?.username || 'bạn'
  return <>
    <PageHeader eyebrow="KHÔNG GIAN CỦA BẠN" title={`Xin chào, ${name}.`} description="Một ngày mới. Một nơi để cả nhóm cùng tiến về phía trước." action={<time className="today" dateTime={new Date().toISOString().slice(0, 10)}><CalendarDotsIcon aria-hidden="true" />{new Intl.DateTimeFormat('vi-VN', { weekday: 'short', day: 'numeric', month: 'long' }).format(new Date())}</time>} />
    <section className="welcome-grid" aria-label="Bắt đầu cùng nhóm">
      <div className="welcome-card"><span className="welcome-card__tag"><span aria-hidden="true" />CÙNG NHAU LÀM NÊN ĐIỀU TỐT HƠN</span><h2>Không gian tốt.<br />Cộng tác <em>hiệu quả.</em></h2><p>Tìm tổ chức của bạn, chọn không gian theo tháng<br className="desktop-break" /> và bắt đầu từ đúng nơi cả nhóm đang làm việc.</p><Link className="button button--light" to="/profiles">Khám phá tổ chức<ArrowUpRightIcon aria-hidden="true" /></Link><div className="welcome-shapes" aria-hidden="true"><span /><span /><span /></div></div>
      <Card className="focus-card"><div className="focus-card__icon"><ShieldCheckIcon aria-hidden="true" /></div><p className="eyebrow">ĐÚNG NHÓM, ĐÚNG NGỮ CẢNH</p><h2>Mỗi nhóm có<br />không gian riêng.</h2><p>Bạn chỉ nhìn thấy các tổ chức và không gian mình được cấp quyền truy cập.</p><span className="text-note">Tập trung vào điều quan trọng.</span></Card>
    </section>
    <section className="section-block" aria-labelledby="your-profiles"><div className="section-heading"><div><p className="eyebrow">KẾT NỐI VỚI NHÓM</p><h2 id="your-profiles">Tổ chức của bạn{profiles.data && <span className="count-badge">{profiles.data.count}</span>}</h2></div><Link className="text-link" to="/profiles">Xem tất cả<ArrowRightIcon aria-hidden="true" /></Link></div>
      {profiles.isPending ? <PageSkeleton label="Đang tải tổ chức…" /> : profiles.isError ? <ErrorState error={profiles.error} onRetry={() => void profiles.refetch()} /> : profiles.data.results.length === 0 ? <EmptyState title="Chưa có tổ chức nào" description="Khi bạn tham gia một tổ chức, không gian của nhóm sẽ xuất hiện tại đây. Liên hệ người quản trị để được mời tham gia." /> : <div className="profile-grid">{profiles.data.results.slice(0, 3).map((profile, index) => <Link key={profile.id} className="profile-card" to={`/profiles/${profile.id}`}><div className="profile-card__top"><span className={`organization-icon organization-icon--${index % 3}`}><BuildingsIcon aria-hidden="true" /></span><Badge status={profile.status} /></div><h3>{profile.name}</h3><p>Xem thông tin và không gian của nhóm</p><span className="profile-card__bottom">Đi đến tổ chức<ArrowUpRightIcon aria-hidden="true" /></span></Link>)}</div>}
    </section>
    <div className="workspace-note"><CalendarDotsIcon aria-hidden="true" /><div><strong>Một tháng, một nhịp làm việc.</strong><p>Không gian theo tháng giúp cả nhóm giữ được ngữ cảnh và lịch sử cộng tác.</p></div><span className="workspace-note__line" aria-hidden="true" /></div>
  </>
}
