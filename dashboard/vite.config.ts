import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  base: '/spotify-pipeline/',  // GitHub Pages repo name
  server: {
    proxy: {
      '/api': 'http://localhost:8000',
    },
  },
})
