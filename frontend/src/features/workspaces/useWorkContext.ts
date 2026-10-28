import { useQuery, useQueryClient } from '@tanstack/react-query'
import { queryKeys, tenantApi } from '../../services/api/queries'
import { workApi, workKeys } from '../../services/api/work-management'

export function useWorkContext(profileId: string, workspaceId?: string) {
  const client = useQueryClient()
  const profile = useQuery({ queryKey: queryKeys.profile(profileId), queryFn: ({ signal }) => tenantApi.profile(profileId, signal) })
  const workspace = useQuery({ queryKey: queryKeys.workspace(profileId, workspaceId || ''), queryFn: ({ signal }) => tenantApi.workspace(profileId, workspaceId || '', signal), enabled: profile.isSuccess && !!workspaceId })
  const capabilities = useQuery({ queryKey: workKeys.capabilities(profileId, workspaceId), queryFn: ({ signal }) => workApi.capabilities(profileId, workspaceId, signal), enabled: profile.isSuccess && (!workspaceId || workspace.isSuccess), staleTime: 0 })
  const active = profile.isSuccess && profile.data.status === 'ACTIVE' && (!workspaceId || (workspace.isSuccess && workspace.data.status === 'ACTIVE'))
  function invalidate(workspaceChanged = false) {
    void client.invalidateQueries({ queryKey: workspaceId ? workKeys.scope(profileId, workspaceId) : workKeys.profile(profileId) })
    if (workspaceChanged) void client.invalidateQueries({ queryKey: queryKeys.profile(profileId) })
  }
  function denied() {
    // Discard stale UI hints immediately, then resolve the current scope again.
    client.setQueryData(workKeys.capabilities(profileId, workspaceId), { createWorkspace: false, manageWorkspace: false, manageLifecycle: false, manageTasks: false })
    invalidate(true)
  }
  // Background errors can retain previous data. Never expose those stale hints.
  return { profile, workspace, capabilities: { ...capabilities, data: capabilities.isSuccess ? capabilities.data : undefined }, active, invalidate, denied }
}
