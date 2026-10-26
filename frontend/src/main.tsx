import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { BrowserRouter } from 'react-router'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import '@fontsource-variable/plus-jakarta-sans'
import './styles.css'
import { AppErrorBoundary, AppRoutes } from './app/App'
import { AuthProvider } from './features/auth/AuthProvider'

const queryClient = new QueryClient({ defaultOptions: { queries: {
  retry: false, staleTime: 0, gcTime: 0, refetchOnWindowFocus: false,
} } })
const root = document.getElementById('root')
if (!root) throw new Error('Root element missing.')
createRoot(root).render(<StrictMode><AppErrorBoundary><QueryClientProvider client={queryClient}><BrowserRouter><AuthProvider><AppRoutes /></AuthProvider></BrowserRouter></QueryClientProvider></AppErrorBoundary></StrictMode>)
