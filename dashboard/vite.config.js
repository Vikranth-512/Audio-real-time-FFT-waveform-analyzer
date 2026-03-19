import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

const backendHost =
    process.env.DOCKER === 'true'
        ? 'backend'
        : 'localhost'

export default defineConfig({
    plugins: [react()],
    server: {
        port: 3000,
        host: true,
        proxy: {
            '/api': {
                target: `http://${backendHost}:8000`,
                changeOrigin: true
            },
            '/ws': {
                target: `ws://${backendHost}:8000`,
                ws: true,
                changeOrigin: true
            }
        }
    },
    build: {
        outDir: 'dist',
        assetsDir: 'assets'
    }
})