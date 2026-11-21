import { Link, useOutletContext } from 'react-router'
import { PageHeader } from '../components/page'
import { PageSkeleton } from '../components/ui'
import { NotificationFeed } from '../features/notifications/NotificationHub'

export function NotificationsPage() {
  const session = useOutletContext<{ currentUserId: string } | null>()
  return <><PageHeader eyebrow="CẬP NHẬT CỦA BẠN" title="Thông báo" description="Theo dõi công việc được phép truy cập và phản hồi lời mời tổ chức dành cho bạn." action={<Link className="button button--secondary" to="/invitations">Lời mời tổ chức</Link>} />
    {session?.currentUserId ? <NotificationFeed userId={session.currentUserId} /> : <PageSkeleton />}
  </>
}
