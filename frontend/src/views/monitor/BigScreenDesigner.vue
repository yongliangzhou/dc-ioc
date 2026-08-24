<template>
  <div class="designer">
    <div class="d-head">
      <h1>{{ tl('大屏定制引擎') }}</h1>
      <div class="d-actions">
        <button class="btn ghost" @click="reset">{{ tl('恢复默认') }}</button>
        <button class="btn primary" @click="save">{{ tl('保存配置') }}</button>
        <router-link to="/monitor/visual/bigscreen" class="btn preview">{{ tl('预览大屏') }} →</router-link>
      </div>
    </div>

    <div class="d-body">
      <!-- 左：基础设置 -->
      <section class="panel">
        <h3>{{ tl('基础设置') }}</h3>
        <label class="fld">
          <span>{{ tl('大屏标题') }}</span>
          <input v-model="cfg.title" type="text" maxlength="20" />
        </label>
        <label class="fld">
          <span>{{ tl('刷新间隔') }}</span>
          <select v-model.number="cfg.refreshSec">
            <option :value="5">5s</option>
            <option :value="10">10s</option>
            <option :value="30">30s</option>
            <option :value="60">60s</option>
          </select>
        </label>
        <div class="fld">
          <span>{{ tl('主题') }}</span>
          <div class="seg">
            <button :class="{ on: cfg.theme === 'dark' }" @click="cfg.theme = 'dark'">{{ tl('深色') }}</button>
            <button :class="{ on: cfg.theme === 'light' }" @click="cfg.theme = 'light'">{{ tl('浅色') }}</button>
          </div>
        </div>
        <div class="fld">
          <span>{{ tl('肤色') }}</span>
          <div class="skins">
            <button
              v-for="s in SKIN_PRESETS"
              :key="s.id"
              class="skin"
              :class="{ on: cfg.skin === s.id && !cfg.customColor }"
              :style="{ background: s.color }"
              :title="s.label"
              @click="selectSkin(s.id)"
            />
            <label class="skin custom" :style="{ background: cfg.customColor || '#fff' }" title="自定义">
              <input type="color" v-model="cfg.customColor" @input="cfg.skin = ''" />
            </label>
          </div>
        </div>
      </section>

      <!-- 右：数据源选择 -->
      <section class="panel grow">
        <h3>{{ tl('数据源') }}（{{ cfg.sourceIds.length }}）</h3>
        <p class="hint">{{ tl('勾选需在定制大屏上展示的指标卡片') }}</p>
        <div class="src-grid">
          <label
            v-for="s in SOURCE_POOL"
            :key="s.id"
            class="src"
            :class="{ on: cfg.sourceIds.includes(s.id) }"
          >
            <input type="checkbox" :value="s.id" v-model="cfg.sourceIds" />
            <span class="src-name">{{ s.label }}</span>
            <span class="src-type">{{ typeText(s.type) }}</span>
          </label>
        </div>
      </section>
    </div>

    <div class="saved" v-if="savedHint">{{ tl('配置已保存') }}</div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  SOURCE_POOL,
  SKIN_PRESETS,
  DEFAULT_CONFIG,
  loadConfig,
  saveConfig,
  type BigScreenConfig,
  type WidgetType,
} from '@/bigscreen/sources'

const { t: tl } = useI18n()
const cfg = ref<BigScreenConfig>(loadConfig())
const savedHint = ref(false)

function selectSkin(id: string) {
  cfg.value.skin = id
  cfg.value.customColor = undefined
}
function typeText(t: WidgetType) {
  return { kpi: '数值', gauge: '仪表', line: '折线', bar: '柱状' }[t]
}
function reset() {
  cfg.value = { ...DEFAULT_CONFIG, sourceIds: [...DEFAULT_CONFIG.sourceIds] }
  savedHint.value = false
}
function save() {
  saveConfig(cfg.value)
  savedHint.value = true
  setTimeout(() => (savedHint.value = false), 2000)
}
</script>

<style scoped>
.designer { padding: 16px 20px 40px; }
.d-head { display: flex; justify-content: space-between; align-items: center; }
.d-head h1 { font-size: 20px; margin: 0; color: #e2e8f0; }
.d-actions { display: flex; gap: 10px; }
.btn { border-radius: 8px; padding: 7px 14px; font-size: 13px; cursor: pointer; text-decoration: none; border: 1px solid var(--line); }
.btn.ghost { color: #cbd5e1; background: transparent; }
.btn.primary { background: var(--cyan); color: #06121f; border-color: var(--cyan); font-weight: 700; }
.btn.preview { color: var(--cyan); border-color: rgba(34,227,255,.4); }
.d-body { display: grid; grid-template-columns: 300px 1fr; gap: 16px; margin-top: 18px; align-items: start; }
.panel { background: #0f172a; border: 1px solid var(--line); border-radius: 14px; padding: 16px; }
.panel.grow { min-height: 360px; }
.panel h3 { margin: 0 0 14px; color: #cbd5e1; font-size: 14px; }
.fld { display: flex; flex-direction: column; gap: 6px; margin-bottom: 16px; font-size: 13px; color: #94a3b8; }
.fld input[type='text'], .fld select { background: #1e293b; border: 1px solid var(--line); color: #e2e8f0; border-radius: 8px; padding: 8px 10px; }
.seg { display: flex; border: 1px solid var(--line); border-radius: 8px; overflow: hidden; width: fit-content; }
.seg button { color: #94a3b8; background: transparent; border: none; padding: 6px 16px; font-size: 13px; cursor: pointer; }
.seg button.on { background: var(--cyan); color: #06121f; font-weight: 700; }
.skins { display: flex; gap: 10px; align-items: center; }
.skin { width: 30px; height: 30px; border-radius: 8px; border: 2px solid transparent; cursor: pointer; }
.skin.on { border-color: #fff; box-shadow: 0 0 0 2px rgba(255,255,255,.3); }
.skin.custom { position: relative; overflow: hidden; display: flex; align-items: center; justify-content: center; }
.skin.custom input { position: absolute; inset: 0; opacity: 0; cursor: pointer; }
.hint { color: #64748b; font-size: 12px; margin: -6px 0 12px; }
.src-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 10px; }
.src { display: flex; align-items: center; gap: 8px; padding: 10px 12px; border-radius: 10px; background: #1e293b; border: 1px solid var(--line); cursor: pointer; font-size: 13px; }
.src.on { border-color: var(--cyan); background: rgba(34,227,255,.08); }
.src-name { color: #e2e8f0; flex: 1; }
.src-type { color: #64748b; font-size: 11px; }
.saved { position: fixed; bottom: 24px; right: 24px; background: #22c55e; color: #04210f; padding: 10px 18px; border-radius: 10px; font-size: 13px; font-weight: 600; }
</style>
