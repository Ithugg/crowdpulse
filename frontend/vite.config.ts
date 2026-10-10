import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Dev only: `npm run dev` serves the UI on :5173 and proxies to the Python server on :8000.
// For the demo the built files in dist/ are served by FastAPI itself.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    port: 5173,
    proxy: {
      '/ws': { target: 'ws://127.0.0.1:8000', ws: true },
      '/api': 'http://127.0.0.1:8000',
    },
  },
})
