import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const target = env.DJANGO_API_TARGET || 'http://127.0.0.1:8000'
  const url = new URL(target)
  if (!['127.0.0.1', 'localhost', '[::1]'].includes(url.hostname) || url.protocol !== 'http:' || url.username || url.password || url.pathname !== '/' || url.search || url.hash) {
    throw new Error('DJANGO_API_TARGET must be an HTTP loopback origin without credentials or path.')
  }
  return {
    plugins: [react(), tailwindcss()],
    server: {
      host: '127.0.0.1', port: 5173, strictPort: true,
      proxy: { '/api': { target, changeOrigin: false } },
      fs: { strict: true, allow: [process.cwd()] },
    },
    preview: { host: '127.0.0.1', port: 4173, strictPort: true },
    build: { target: 'es2022', sourcemap: false },
  }
})
