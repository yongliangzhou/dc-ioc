<template>
  <p v-if="level !== 'none'" class="mock-banner" :class="`mb-${level}`" role="status">
    <AlertTriangle :size="14" class="mb-icon" />
    <span class="mb-text">
      <template v-if="note">⚠ {{ note }}</template>
      <template v-else-if="level === 'full'">
        ⚠ 当前为<b>本地模拟数据</b>：后端未返回有效数据，图中设备与读数<b>不可作为操作依据</b>。
      </template>
      <template v-else>
        ⚠ <b>部分数据为模拟数据</b>{{ reason ? `（${reason}）` : '' }}：设备主体来自实时接口，
        但标注字段由本地生成，<b>真实与模拟混排，请注意甄别</b>。
      </template>
    </span>
  </p>
</template>

<script setup lang="ts">
/**
 * MockDataBanner — 模拟数据提示条
 *
 * 与 DataBadge 的区别：
 * - DataBadge 是**小角标**，贴在某个图表/卡片旁，适合"这一块是示例曲线"
 * - MockDataBanner 是**整页横幅**，适合"这一页的数据源有问题"
 *
 * full    = 整页都是本地模拟（后端没返回任何有效数据）
 * partial = 真设备 + 模拟字段混排（更隐蔽，也更危险）
 */
import { AlertTriangle } from 'lucide-vue-next'
import type { MockLevel } from '@/composables/useAsyncPage'

withDefaults(
  defineProps<{
    level: MockLevel
    /** 补充说明"哪些字段是假的"，partial 档尤其需要 */
    reason?: string
    /**
     * 覆盖默认文案。
     * 默认文案偏"设备遥测"语境，区块级提示（如整块写死的功能卡）可换成更贴合的说法。
     */
    note?: string
  }>(),
  { reason: '', note: '' },
)
</script>

<style scoped>
.mock-banner {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  margin: 8px 0 0;
  padding: 8px 12px;
  border-radius: 8px;
  font-size: 12px;
  line-height: 1.6;
}
.mb-icon {
  flex-shrink: 0;
  margin-top: 2px;
}
.mb-text {
  min-width: 0;
}
/* 全量模拟: 琥珀 */
.mb-full {
  color: #d9a441;
  background: rgba(217, 164, 65, 0.1);
  border: 1px solid rgba(217, 164, 65, 0.35);
}
.mb-full b {
  color: #f0b27a;
}
/* 真假混排: 橙红, 比 full 更醒目——因为更不容易被发现 */
.mb-partial {
  color: #e0844a;
  background: rgba(224, 132, 74, 0.12);
  border: 1px solid rgba(224, 132, 74, 0.4);
}
.mb-partial b {
  color: #f5a97a;
}
</style>
