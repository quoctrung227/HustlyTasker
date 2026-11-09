import { Link } from 'react-router'
import { EmptyState } from '../../components/ui'

export function ProfileOnboarding() {
  return <EmptyState title="Bạn chưa có tổ chức nào"
    description="Tạo tổ chức đầu tiên để bắt đầu quản lý không gian làm việc và phân công công việc cho nhóm."
    action={<Link className="button button--primary" to="/profiles/new">Tạo tổ chức</Link>} />
}
