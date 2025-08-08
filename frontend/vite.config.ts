import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // HMR WebSocket 설정
    hmr: {
      port: 5173,
      host: 'localhost',
      // WSL2 환경에서 안정성 향상
      clientPort: 5173
    },
    // 서버 설정
    host: true, // 모든 네트워크 인터페이스에서 접근 허용
    port: 5173,
    strictPort: true, // 포트가 사용 중이면 오류 발생
    // 개발 서버 안정성 향상
    watch: {
      usePolling: false, // 성능상 polling 비활성화
      interval: 100
    }
  },
  // 빌드 최적화
  build: {
    sourcemap: true,
    rollupOptions: {
      output: {
        manualChunks: {
          vendor: ['react', 'react-dom'],
          ui: ['lucide-react', '@tanstack/react-query']
        }
      }
    }
  }
})
