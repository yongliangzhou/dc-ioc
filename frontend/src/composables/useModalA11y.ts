import { onBeforeUnmount, onMounted, watch } from 'vue'
import type { Ref } from 'vue'

const FOCUSABLE =
  'a[href],button:not([disabled]),input:not([disabled]),select:not([disabled]),' +
  'textarea:not([disabled]),[tabindex]:not([tabindex="-1"])'

/**
 * 04 §6.2 遮罩无障碍：Esc 关闭 + Tab 焦点陷阱 + 关闭后焦点归还。
 *
 * 页面用法：`useModalA11y(drawerOpen, () => { drawerOpen.value = false }, rootRef)`，
 * 其中 `rootRef` 指向 `.modal` / `.modal.as-drawer` 容器（建议加 `tabindex="-1"`）。
 * 多个遮罩可各自注册；只有 `open` 为 true 的实例响应按键。
 */
export function useModalA11y(
  open: Ref<boolean>,
  close: () => void,
  container?: Ref<HTMLElement | null>,
): void {
  let previous: HTMLElement | null = null

  function focusables(): HTMLElement[] {
    const root = container?.value
    if (!root) return []
    return Array.from(root.querySelectorAll<HTMLElement>(FOCUSABLE)).filter(
      (el) => !el.hasAttribute('disabled') && el.tabIndex >= 0,
    )
  }

  function onKeydown(e: KeyboardEvent) {
    if (!open.value) return
    if (e.key === 'Escape') {
      e.preventDefault()
      close()
      return
    }
    if (e.key !== 'Tab') return
    const list = focusables()
    if (!list.length) return
    const first = list[0]
    const last = list[list.length - 1]
    if (e.shiftKey && document.activeElement === first) {
      e.preventDefault()
      last.focus()
    } else if (!e.shiftKey && document.activeElement === last) {
      e.preventDefault()
      first.focus()
    }
  }

  watch(open, (visible) => {
    if (visible) {
      previous = document.activeElement as HTMLElement | null
      requestAnimationFrame(() => {
        const list = focusables()
        if (list.length) list[0].focus()
        else container?.value?.focus()
      })
    } else if (previous) {
      previous.focus()
      previous = null
    }
  })

  onMounted(() => document.addEventListener('keydown', onKeydown))
  onBeforeUnmount(() => {
    document.removeEventListener('keydown', onKeydown)
    if (previous) previous.focus()
  })
}
