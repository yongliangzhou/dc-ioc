import { computed } from "vue";
import { useAuthStore } from "@/stores/modules/auth";

export type PermAction = "admin" | "write";

/**
 * 页面内按钮级权限判断。
 * - admin: 仅管理员可执行（删除 / 配置 / 静默 / 注册设备等）
 * - write: 非访客即可（编辑 / 派发 / 确认等）
 */
export function usePermission() {
  const auth = useAuthStore();

  const isViewer = computed(() => auth.user?.roles?.includes("viewer") ?? false);

  const can = (action: PermAction): boolean => {
    if (action === "admin") return auth.isAdmin ?? false;
    // write: 任何已登录且非 viewer 的角色
    return !isViewer.value;
  };

  /** 禁用态的提示文案 */
  const denyTip = (action: PermAction): string => {
    if (action === "admin") return auth.isLoggedIn ? "需要管理员权限" : "请先登录";
    return "当前账号无操作权限";
  };

  return { can, denyTip };
}
