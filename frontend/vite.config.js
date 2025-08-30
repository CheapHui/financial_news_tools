import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    host: true, // 允許外部訪問
    proxy: {
      // 代理 /api 請求到 Django 後端 (Docker服務名)
      '/api': {
        target: 'http://web:8000',
        changeOrigin: true,
        secure: false,
      }
    }
  },
})
