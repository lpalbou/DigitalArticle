import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    strictPort: true, // Fail if port 3000 is not available instead of trying other ports
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        timeout: 0, // No timeout - allow operations to run as long as needed
        proxyTimeout: 0, // No proxy timeout
      },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: true,
  },
})
