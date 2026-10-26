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

  const verifyIdentity = useCallback(async (quiet = false) => {
    if (quiet && current.current.status !== 'authenticated') return
    const ticket = ++generation.current
    pending.current?.abort()
    const controller = new AbortController()
    pending.current = controller
    const previousUser = current.current.user?.id
    // No stale private screen remains visible while identity is uncertain.
    // A permission403 probes identity without remounting the denied query.
    // Otherwise a valid /me followed by a stale refetch can loop forever.
    if (!quiet) setState({ status: 'checking', user: null, error: null })
    try {
      const user = await authApi.me(controller.signal)
      if (ticket !== generation.current) return
      if (previousUser !== user.id) await clearPrivate()
      if (ticket === generation.current) setState({ status: 'authenticated', user, error: null })
    } catch (error) {
      if (ticket !== generation.current || controller.signal.aborted) return
      await clearPrivate()
      if (ticket !== generation.current) return
      const anonymous = isApiError(error) && (error.status === 401 || error.status === 403)
      setState({ status: anonymous ? 'anonymous' : 'unavailable', user: null, error })
    }
  }, [clearPrivate])

  const revalidate = useCallback(() => verifyIdentity(), [verifyIdentity])
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
      if (document.visibilityState !== 'hidden' && current.current.status !== 'unavailable') void revalidate()
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
