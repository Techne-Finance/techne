import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'path'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 3001,
    proxy: {
      '/api': {
        target: 'https://techne-backend-t2umhhv3ia-ew.a.run.app',
        changeOrigin: true,
        secure: true,
      },
      '/ws': {
        target: 'wss://techne-backend-t2umhhv3ia-ew.a.run.app',
        ws: true,
      },
    },
  },
})
