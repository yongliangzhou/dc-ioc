import { defineConfig } from "vitest/config";
import vue from "@vitejs/plugin-vue";
import { fileURLToPath, URL } from "node:url";

export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: { "@": fileURLToPath(new URL("./src", import.meta.url)) },
  },
  test: {
    environment: "jsdom",
    globals: true,
    include: ["src/**/*.spec.ts"],
    // 避免 echarts 在 jsdom 下 canvas 缺失的告警影响输出
    silent: false,
    coverage: {
      provider: "v8",
      reporter: ["text", "html", "lcov"],
      include: [
        "src/api/power.ts",
        "src/api/request.ts",
        "src/engine/realtimeLinkage.ts",
        "src/hooks/usePermission.ts",
        "src/utils/echarts.ts",
        "src/components/common/VirtualList.vue",
        "src/composables/useFormValidation.ts",
      ],
      // [Q-03] 核心模块行覆盖率门禁
      thresholds: {
        lines: 70,
        functions: 70,
        branches: 60,
      },
    },
  },
});
