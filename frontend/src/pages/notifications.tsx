import { useOutletContext } from 'react-router'
import { PageHeader } from '../components/page'
import { PageSkeleton } from '../components/ui'
import { NotificationFeed } from '../features/notifications/NotificationHub'

export function NotificationsPage() {
  const session = useOutletContext<{ currentUserId: string } | null>()
  return <><PageHeader eyebrow="CẬP NHẬT CỦA BẠN" title="Thông báo" description="Theo dõi những thay đổi trong các công việc bạn được phép truy cập." />
    {session?.currentUserId ? <NotificationFeed userId={session.currentUserId} /> : <PageSkeleton />}
  </>
}
