import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  // Production base: assets must be served from /static/react/assets/
  // so Flask's built-in /static/<path> handler can find them.
  // In dev mode Vite serves everything itself so this has no effect locally.
  base: '/static/react/',
  // In development, proxy /api requests to the Flask backend
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:5001',
        changeOrigin: true,
      },
    },
  },
  // Build output goes to ../static/react so Flask can serve it
  build: {
    outDir: '../static/react',
    emptyOutDir: true,
  },
})
