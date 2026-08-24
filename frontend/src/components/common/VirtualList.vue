<template>
  <div
    ref="scroller"
    class="virtual-list"
    :style="{ height: typeof height === 'number' ? height + 'px' : height }"
    @scroll.passive="onScroll"
  >
    <div class="vl-phantom" :style="{ height: totalHeight + 'px' }">
      <div class="vl-content" :style="{ transform: `translateY(${offset}px)` }">
        <div
          v-for="(item, i) in visibleItems"
          :key="getKey(item, startIndex + i)"
          class="vl-row"
          :style="rowStyle"
        >
          <slot :item="item" :index="startIndex + i" />
        </div>
        <div v-if="!items.length" class="vl-empty">
          <slot name="empty">{{ emptyText }}</slot>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts" generic="T">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = withDefaults(
  defineProps<{
    items: T[]
    itemHeight: number
    height: number | string
    /** 可视区上下额外渲染行数, 缓解滚动白屏 */
    buffer?: number
    /** 每行唯一键字段名 */
    keyField?: string
    /** 自定义行标识函数 (keyField 不存在时使用) */
    itemKey?: (item: T, index: number) => string | number
    emptyText?: string
  }>(),
  { buffer: 6, emptyText: '暂无数据' },
)

const scroller = ref<HTMLElement | null>(null)
const scrollTop = ref(0)
const viewport = ref(0)

const totalHeight = computed(() => props.items.length * props.itemHeight)
const visibleCount = computed(() =>
  viewport.value > 0 ? Math.ceil(viewport.value / props.itemHeight) : 0,
)
const startIndex = computed(() => {
  if (!visibleCount.value) return 0
  const raw = Math.floor(scrollTop.value / props.itemHeight) - props.buffer
  return raw < 0 ? 0 : raw
})
const endIndex = computed(() => {
  const raw = startIndex.value + visibleCount.value + props.buffer * 2
  return raw > props.items.length ? props.items.length : raw
})
const offset = computed(() => startIndex.value * props.itemHeight)
const visibleItems = computed(() => props.items.slice(startIndex.value, endIndex.value))
const rowStyle = computed(() => ({ height: props.itemHeight + 'px' }))

function getKey(item: T, index: number): string | number {
  if (props.keyField && item && typeof item === 'object' && props.keyField in item) {
    return (item as Record<string, unknown>)[props.keyField] as string | number
  }
  if (props.itemKey) return props.itemKey(item, index)
  return index
}

function onScroll(e: Event) {
  scrollTop.value = (e.target as HTMLElement).scrollTop
}

function measure() {
  if (scroller.value) viewport.value = scroller.value.clientHeight
}

let ro: ResizeObserver | null = null
onMounted(() => {
  measure()
  if (typeof ResizeObserver !== 'undefined' && scroller.value) {
    ro = new ResizeObserver(measure)
    ro.observe(scroller.value)
  }
})
onBeforeUnmount(() => ro?.disconnect())

// items 变化后若滚动位置超出新范围则夹紧
watch(
  () => props.items.length,
  () => {
    if (scrollTop.value > totalHeight.value) {
      scrollTop.value = Math.max(0, totalHeight.value - viewport.value)
      if (scroller.value) scroller.value.scrollTop = scrollTop.value
    }
  },
)
</script>

<style scoped>
.virtual-list {
  overflow-y: auto;
  position: relative;
  width: 100%;
}
.virtual-list::-webkit-scrollbar {
  width: 4px;
}
.virtual-list::-webkit-scrollbar-thumb {
  background: var(--line);
  border-radius: 3px;
}
.vl-phantom {
  position: relative;
  width: 100%;
}
.vl-content {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  will-change: transform;
}
.vl-row {
  box-sizing: border-box;
  width: 100%;
}
.vl-empty {
  position: absolute;
  top: 50%;
  left: 0;
  right: 0;
  transform: translateY(-50%);
  text-align: center;
  color: var(--txt3);
  font-size: 12px;
}
</style>
