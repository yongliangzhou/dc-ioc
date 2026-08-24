<template>
  <div class="quick-control">
    <span class="qc-label">{{ label }}</span>
    <div class="qc-actions">
      <!-- 开关按钮 -->
      <button
        v-if="showPower"
        class="qc-btn"
        :class="{ on: powerOn }"
        @click="$emit('togglePower')"
      >
        <span class="qc-icon">{{ powerOn ? '⏻' : '⏻' }}</span>
        {{ powerOn ? '关机' : '开机' }}
      </button>

      <!-- 启停按钮 -->
      <button
        v-if="showStartStop"
        class="qc-btn"
        :class="{ on: running }"
        @click="$emit('toggleStartStop')"
      >
        {{ running ? '停止' : '启动' }}
      </button>

      <!-- 模式切换下拉 -->
      <select
        v-if="modes?.length"
        class="qc-select"
        :value="activeMode"
        @change="$emit('modeChange', ($event.target as HTMLSelectElement).value)"
      >
        <option v-for="m in modes" :key="m" :value="m">{{ m }}</option>
      </select>

      <!-- 数值设定 -->
      <label v-if="showTemp" class="qc-slider">
        <span>{{ tempLabel }}</span>
        <input
          type="range"
          :min="tempMin"
          :max="tempMax"
          :step="tempStep"
          :value="tempValue"
          @input="onTempChange"
        />
        <span class="qc-temp-val">{{ tempValue }}{{ tempUnit }}</span>
      </label>

      <!-- 自定义操作 -->
      <slot />
    </div>
  </div>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    label?: string

    // 开关控制
    showPower?: boolean
    powerOn?: boolean

    // 启停控制
    showStartStop?: boolean
    running?: boolean

    // 模式切换
    modes?: string[]
    activeMode?: string

    // 温度/参数设定
    showTemp?: boolean
    tempLabel?: string
    tempValue?: number
    tempMin?: number
    tempMax?: number
    tempStep?: number
    tempUnit?: string
  }>(),
  {
    label: '远程控制',
    tempMin: 16,
    tempMax: 32,
    tempStep: 0.5,
    tempUnit: '℃',
  },
)

const emit = defineEmits<{
  togglePower: []
  toggleStartStop: []
  modeChange: [value: string]
  tempChange: [value: number]
}>()

function onTempChange(e: Event) {
  const val = parseFloat((e.target as HTMLInputElement).value)
  emit('tempChange', val)
}
</script>

<style scoped>
.quick-control {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}
.qc-label {
  font-size: 11px;
  color: var(--txt3);
  margin-right: 4px;
}
.qc-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}
.qc-btn {
  border: 1px solid var(--line);
  background: transparent;
  color: var(--txt);
  font-size: 11px;
  padding: 4px 12px;
  border-radius: 5px;
  cursor: pointer;
  transition: all 0.15s;
  display: flex;
  align-items: center;
  gap: 4px;
}
.qc-btn:hover {
  border-color: var(--cyan);
  color: var(--cyan);
}
.qc-btn.on {
  background: rgba(239, 68, 68, 0.12);
  border-color: var(--red);
  color: var(--red);
}
.qc-icon {
  font-size: 14px;
}
.qc-select {
  background: var(--bg);
  border: 1px solid var(--line);
  color: var(--txt);
  font-size: 11px;
  padding: 4px 8px;
  border-radius: 5px;
  cursor: pointer;
}
.qc-slider {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: var(--txt3);
}
.qc-slider input[type='range'] {
  width: 60px;
  accent-color: var(--cyan);
}
.qc-temp-val {
  font-weight: 700;
  color: var(--txt);
  min-width: 36px;
}
</style>
