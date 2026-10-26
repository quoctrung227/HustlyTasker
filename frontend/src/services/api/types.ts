/** Contracts from the existing DRF serializers; no client-side permission grants. */
export type LifecycleStatus = 'ACTIVE' | 'ARCHIVED'

export interface User {
  id: string
  email: string
  username: string
  first_name: string
  last_name: string
  created_at: string
  email_verified: boolean
}

export interface UserEnvelope {
  user: User
}

export interface LoginInput {
  email: string
  password: string
}

export interface Profile {
  id: string
  name: string
  status: LifecycleStatus
  created_at: string
  updated_at: string
}

export interface Workspace {
  id: string
  profile_id: string
  name: string
  description: string | null
  /** Canonical YYYY-MM-01 or null for existing legacy rows. */
  period: string | null
  status: LifecycleStatus
  created_at: string
  updated_at: string
}

export interface Page<T> {
  count: number
  /** Server links are metadata only. Requests are built from local page numbers. */
  next: string | null
  previous: string | null
  results: T[]
}
