<template>
  <div class="lang-switcher" ref="container">
    <button class="tbtn lang-btn" @click="open = !open" title="Switch Language / 切换语言">
      <span>{{ currentLabel }}</span>
    </button>
    <div v-if="open" class="lang-drop">
      <button
        v-for="l in locales"
        :key="l.code"
        class="lang-opt"
        :class="{ sel: l.code === locale }"
        @click="switchTo(l.code)"
      >
        {{ l.label }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useI18n } from 'vue-i18n'
import { supportedLocales, switchLocale } from '@/i18n'

const { locale } = useI18n()
const open = ref(false)
const container = ref<HTMLElement | null>(null)

const locales = supportedLocales
const currentLabel = computed(
  () => locales.find((l) => l.code === locale.value)?.label ?? locale.value,
)

async function switchTo(code: string) {
  await switchLocale(code) // 懒加载语言包后再切换
  open.value = false
}

function onClickOutside(e: MouseEvent) {
  if (container.value && !container.value.contains(e.target as Node)) {
    open.value = false
  }
}

onMounted(() => document.addEventListener('click', onClickOutside))
onBeforeUnmount(() => document.removeEventListener('click', onClickOutside))
</script>

<style scoped>
.lang-switcher {
  position: relative;
}
.lang-btn {
  background: var(--panel2);
  color: var(--txt2);
  border: 1px solid var(--line);
  border-radius: 6px;
  padding: 4px 10px;
  cursor: pointer;
  font-size: 12px;
  white-space: nowrap;
  transition: all 0.15s;
}
.lang-btn:hover {
  color: var(--txt);
  border-color: var(--txt3);
}
.lang-drop {
  position: absolute;
  top: 100%;
  right: 0;
  margin-top: 4px;
  background: var(--panel);
  border: 1px solid var(--line);
  border-radius: 8px;
  overflow: hidden;
  z-index: 200;
  min-width: 100px;
}
.lang-opt {
  display: block;
  width: 100%;
  padding: 8px 14px;
  border: none;
  background: transparent;
  color: var(--txt2);
  font-size: 12.5px;
  cursor: pointer;
  text-align: left;
  transition: all 0.12s;
}
.lang-opt:hover,
.lang-opt.sel {
  background: var(--bg2);
  color: var(--txt);
}
.lang-opt.sel {
  color: var(--cyan);
  font-weight: 600;
}
</style>
