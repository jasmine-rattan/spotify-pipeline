import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  // base defaults to '/' which works for Vercel
  // GitHub Pages deployment uses the pre-built docs/ folder (committed separately)
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
})
