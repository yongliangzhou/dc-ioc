import { watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import type { Ref } from 'vue'

/**
 * 04 §6.2：筛选条件写 URL query（?status=&page=&size=）。
 *
 * - setup 期间从当前 query 恢复非空值，页面首次加载即带上筛选条件；
 * - 之后任一筛选值变化用 `router.replace` 同步，不产生浏览器历史记录；
 * - 空值从 query 移除，保持链接可读。
 *
 * 两种形态：`useFilterQuery` 用于一组 `ref`，`useReactiveFilterQuery` 用于 `reactive` 对象。
 * 页面只需声明一次绑定，无需手写 watch / router 调用。
 */
type Value = string | number

function bind(
  keys: string[],
  read: () => Record<string, Value>,
  apply: (key: string, raw: string) => void,
): void {
  const route = useRoute()
  const router = useRouter()

  for (const key of keys) {
    const raw = route.query[key]
    if (typeof raw === 'string' && raw !== '') apply(key, raw)
  }

  watch(read, (values) => {
    const next = { ...route.query }
    for (const [key, value] of Object.entries(values)) {
      if (value === '' || value === undefined || value === null) delete next[key]
      else next[key] = String(value)
    }
    void router.replace({ query: next })
  })
}

/** 一组独立的 `ref('')` / `ref(1)`。 */
export function useFilterQuery(refs: Record<string, Ref<Value>>): void {
  const entries = Object.entries(refs)
  bind(
    entries.map(([key]) => key),
    () => Object.fromEntries(entries.map(([key, r]) => [key, r.value])),
    (key, raw) => {
      const ref = refs[key]
      ref.value = typeof ref.value === 'number' ? Number(raw) || ref.value : raw
    },
  )
}

/** `reactive({...})` 形态；`extra` 用于把 page / size 一并写进链接。 */
export function useReactiveFilterQuery(
  state: Record<string, Value>,
  extra: Record<string, Ref<number>> = {},
): void {
  bind(
    [...Object.keys(state), ...Object.keys(extra)],
    () => ({
      ...state,
      ...Object.fromEntries(Object.entries(extra).map(([key, r]) => [key, r.value])),
    }),
    (key, raw) => {
      if (key in extra) extra[key].value = Number(raw) || extra[key].value
      else state[key] = raw
    },
  )
}
