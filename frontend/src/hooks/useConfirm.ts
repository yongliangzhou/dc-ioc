import { type App, createApp } from 'vue'
import ConfirmDialog from '@/components/ui/ConfirmDialog.vue'
import { extractError } from '@/hooks/useAsyncTask'

// ConfirmDialog 组件实例对外暴露的命令式方法
interface ConfirmDialogInstance {
  open: (opts: ConfirmOptions) => Promise<boolean>
  setLoading: (v: boolean) => void
  setError: (msg: string) => void
  close: () => void
}

let instance: ConfirmDialogInstance | null = null

/** 懒加载单例 ConfirmDialog 到 body */
function ensureInstance(): Promise<ConfirmDialogInstance> {
  if (instance) return Promise.resolve(instance)
  return new Promise((resolve) => {
    const el = document.createElement('div')
    document.body.appendChild(el)
    const app: App = createApp(ConfirmDialog)
    const comp = app.mount(el) as unknown as ConfirmDialogInstance
    instance = comp
    resolve(comp)
  })
}

export interface ConfirmOptions {
  title?: string
  message: string
  detail?: string
  confirmText?: string
  cancelText?: string
  loadingText?: string
  danger?: boolean
  /** 传入异步任务：点击确定后执行，自动接管 loading/error；失败不关闭 */
  onConfirm?: () => Promise<void>
}

/**
 * 统一确认弹窗。返回 Promise<boolean>。
 *
 * 简单用法：
 *   if (await useConfirm({ message: "确认删除？", danger: true })) { ... }
 *
 * 带异步任务（自动 loading + 错误回显，失败保持打开）：
 *   await useConfirm({ message, danger: true, onConfirm: async () => { await delApi() } });
 */
export async function useConfirm(opts: ConfirmOptions): Promise<boolean> {
  const comp = await ensureInstance()
  const ok = await comp.open(opts)
  if (ok && opts.onConfirm) {
    comp.setLoading(true)
    comp.setError('')
    try {
      await opts.onConfirm()
      comp.close()
      return true
    } catch (e: unknown) {
      comp.setLoading(false)
      comp.setError(extractError(e))
      return false
    }
  }
  return ok
}
