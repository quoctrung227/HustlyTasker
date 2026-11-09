import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router'
import { Button } from '../../components/ui'
import { useAuth } from '../auth/AuthProvider'
import { aiApi, aiKeys } from '../../services/api/ai'

/** Read-only availability is a hint; every proposal operation reauthorizes. */
export function GeneratorEntry({ profileId, workspaceId, allowed }: { profileId: string; workspaceId: string; allowed: boolean }) {
  const { user } = useAuth()
  const availability = useQuery({ queryKey: aiKeys.availability(user?.id || '', profileId, workspaceId),
    queryFn: ({ signal }) => aiApi.availability(profileId, workspaceId, signal), enabled: allowed && !!user, retry: false })
  if (!allowed || !user) return null
  if (availability.isSuccess && availability.data.enabled) return <Link className="button button--secondary" to={`/profiles/${profileId}/workspaces/${workspaceId}/tasks/generate`}>Tạo công việc bằng AI</Link>
  return <div className="ai-entry-unavailable"><Button variant="secondary" disabled aria-describedby="ai-entry-status">Tạo công việc bằng AI</Button>
    <span className="field__hint" id="ai-entry-status">{availability.isPending ? 'Đang kiểm tra bản mô phỏng…' : availability.isError ? 'Chưa xác minh được bản mô phỏng.' : 'Bản mô phỏng đang tắt trong môi trường này.'}</span></div>
}
