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
    },
    // API 프록시 설정 - 백엔드 서버로 API 요청 전달
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
        // 프록시 로깅 활성화 (디버깅용)
        configure: (proxy, options) => {
          proxy.on('proxyReq', (proxyReq, req, res) => {
            console.log('🔄 API 프록시:', req.method, req.url, '→', options.target + req.url);
          });
          proxy.on('error', (err, req, res) => {
            console.error('❌ 프록시 오류:', err.message);
          });
        }
      },
      // WebSocket 프록시 (필요시)
      '/ws': {
        target: 'ws://localhost:8000',
        ws: true
      }
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
