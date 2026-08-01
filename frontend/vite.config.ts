import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import { fileURLToPath, URL } from "node:url";
import { compression } from "vite-plugin-compression2";

// https://vite.dev/config/
export default defineConfig({
  plugins: [
    vue(),

    // Gzip + Brotli 预压缩: 构建时生成 .gz / .br 兄弟文件,
    // 由 Nginx 的 gzip_static 直接发送, 省去运行时压缩开销。
    // 使用 vite-plugin-compression2 (维护版), 在 Windows 下也能正确生成相对路径。
    compression({
      algorithms: ["gzip", "brotliCompress"],
      threshold: 1024,
      deleteOriginalAssets: false,
      logLevel: "info",
    }),
  ],

  resolve: {
    alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
  },

  build: {
    target: "es2020",
    // 单包超过该值给出警告 (echarts 较大, 已通过 manualChunks 拆分)
    chunkSizeWarningLimit: 1500,
    rollupOptions: {
      output: {
        // ===== 代码分割: 第三方大库单独成包, 利于浏览器长缓存与并行加载 =====
        manualChunks: {
          echarts: ["echarts"],
          vue: ["vue", "vue-router", "pinia"],
          axios: ["axios"],
        },
        // 文件名带 hash, 内容变更才失效, 适合 CDN/强缓存
        entryFileNames: "assets/js/[name].[hash].js",
        chunkFileNames: "assets/js/[name].[hash].js",
        assetFileNames: "assets/[ext]/[name].[hash].[ext]",
      },
    },
  },

  server: {
    host: true,
    port: 5173,
    // 预览环境通过 127.0.0.1 / localhost 访问时, 让 HMR 客户端显式连回 5173,
    // 避免出现 "WebSocket connection ... failed" 且 HMR 不生效。
    hmr: {
      clientPort: 5173,
      protocol: "ws",
    },
    proxy: {
      // Docker 开发: BACKEND_URL=http://backend:8000
      // 本地开发: 不作设置，回退到 localhost:8000
      "/api": { target: process.env.BACKEND_URL || "http://localhost:8000", changeOrigin: true },
      "/ws": { target: (process.env.BACKEND_URL || "http://localhost:8000").replace(/^http/, "ws"), ws: true },
    },
  },
});
