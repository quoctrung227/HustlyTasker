import { createContext, useCallback, useContext, useEffect, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { apiClient, isApiError } from '../../services/api/client'
import { authApi } from '../../services/api/queries'
import type { LoginInput, User } from '../../services/api/types'

type AuthStatus = 'checking' | 'authenticated' | 'anonymous' | 'unavailable'
type AuthState = { status: AuthStatus; user: User | null; error: unknown }
type AuthContextValue = AuthState & {
  signIn: (input: LoginInput) => Promise<void>
  signOut: () => Promise<void>
  revalidate: () => Promise<void>
}
const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const cache = useQueryClient()
  const [state, setState] = useState<AuthState>({ status: 'checking', user: null, error: null })
  const current = useRef(state)
  const generation = useRef(0)
  const pending = useRef<AbortController | null>(null)
  current.current = state

  const clearPrivate = useCallback(async () => {
    await cache.cancelQueries()
    cache.clear()
  }, [cache])

  const verifyIdentity = useCallback(async (quiet = false, refreshPrivate = false) => {
    if (quiet && current.current.status !== 'authenticated') return
    const ticket = ++generation.current
    pending.current?.abort()
    const controller = new AbortController()
    pending.current = controller
    const previousUser = current.current.user?.id
    // Initial/recovery checks block rendering. Routine checks keep an already
    // authenticated subtree mounted until an actual failure or identity change.
    // Replacing it with a loading screen would discard every local form draft.
    if (!quiet) setState({ status: 'checking', user: null, error: null })
    try {
      const user = await authApi.me(controller.signal)
      if (ticket !== generation.current) return
      if (previousUser !== user.id) {
        setState({ status: 'checking', user: null, error: null })
        await clearPrivate()
      }
      if (ticket === generation.current) {
        setState({ status: 'authenticated', user, error: null })
        // Refresh current tenant permissions/data without destroying local forms.
        // A permission-403 probe must NOT refetch the query that triggered it.
        if (refreshPrivate && previousUser === user.id) void cache.invalidateQueries({ refetchType: 'active' })
      }
    } catch (error) {
      if (ticket !== generation.current || controller.signal.aborted) return
      setState({ status: 'checking', user: null, error: null })
      await clearPrivate()
      if (ticket !== generation.current) return
      const anonymous = isApiError(error) && (error.status === 401 || error.status === 403)
      setState({ status: anonymous ? 'anonymous' : 'unavailable', user: null, error })
    }
  }, [cache, clearPrivate])

  const revalidate = useCallback(() => {
    const authenticated = current.current.status === 'authenticated'
    return verifyIdentity(authenticated, authenticated)
  }, [verifyIdentity])
  const verifyForbidden = useCallback(() => verifyIdentity(true), [verifyIdentity])

  const signIn = useCallback(async (input: LoginInput) => {
    const ticket = ++generation.current
    pending.current?.abort()
    const controller = new AbortController()
    pending.current = controller
    await clearPrivate()
    const user = await authApi.login(input, controller.signal)
    if (ticket === generation.current) setState({ status: 'authenticated', user, error: null })
  }, [clearPrivate])

  const signOut = useCallback(async () => {
    const ticket = ++generation.current
    pending.current?.abort()
    const controller = new AbortController()
    pending.current = controller
    setState({ status: 'checking', user: null, error: null })
    await clearPrivate()
    try {
      await authApi.logout(controller.signal)
      if (ticket === generation.current) setState({ status: 'anonymous', user: null, error: null })
    } catch (error) {
      if (ticket !== generation.current || controller.signal.aborted) return
      // A network/CSRF failure does not prove server-side logout succeeded.
      setState({ status: 'unavailable', user: null, error })
    }
  }, [clearPrivate])

  useEffect(() => {
    void revalidate()
    const check = () => {
      // Never abort an in-progress login/logout with a periodic identity probe.
      if (document.visibilityState !== 'hidden' && current.current.status === 'authenticated') void revalidate()
    }
    const visibility = () => { if (document.visibilityState === 'visible') check() }
    window.addEventListener('focus', check)
    document.addEventListener('visibilitychange', visibility)
    const interval = window.setInterval(check, 60_000)
    apiClient.setForbiddenHandler(verifyForbidden)
    return () => {
      generation.current += 1
      pending.current?.abort()
      apiClient.setForbiddenHandler(null)
      window.removeEventListener('focus', check)
      document.removeEventListener('visibilitychange', visibility)
      window.clearInterval(interval)
    }
  }, [revalidate, verifyForbidden])

  return <AuthContext.Provider value={{ ...state, signIn, signOut, revalidate }}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) throw new Error('AuthProvider is required.')
  return context
}
