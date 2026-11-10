<template>
  <div class="p3-page">
    <div class="p3-head">
      <h1>{{ t('customField.title') }}</h1>
      <span class="sub">{{ t('customField.subtitle') }}</span>
    </div>
    <MockDataBanner :level="notice ? 'full' : 'none'" :note="notice" />
    <AsyncSection :loading="loading" :empty="false" @retry="reload" />

    <div class="p3-grid">
      <section class="p3-card">
        <h2>{{ t('customField.add') }}</h2>
        <label class="p3-label">{{ t('customField.key') }}</label>
        <input v-model="form.key" class="p3-ipt" placeholder="rack_color" />
        <label class="p3-label">{{ t('customField.labelZh') }}</label>
        <input v-model="form.label_zh" class="p3-ipt" />
        <label class="p3-label">{{ t('customField.labelEn') }}</label>
        <input v-model="form.label_en" class="p3-ipt" />
        <label class="p3-label">{{ t('customField.type') }}</label>
        <select v-model="form.type" class="p3-ipt">
          <option value="text">{{ t('customField.typeText') }}</option>
          <option value="number">{{ t('customField.typeNumber') }}</option>
          <option value="date">{{ t('customField.typeDate') }}</option>
          <option value="select">{{ t('customField.typeSelect') }}</option>
        </select>
        <label v-if="form.type === 'select'" class="p3-label">{{ t('customField.options') }}</label>
        <input
          v-if="form.type === 'select'"
          v-model="optionsText"
          class="p3-ipt"
          placeholder="black,blue"
        />
        <label class="p3-label">{{ t('customField.required') }}</label>
        <input v-model="form.required" type="checkbox" />
        <button class="p3-btn" @click="addField">{{ t('customField.add') }}</button>
        <p v-if="error" class="p3-err">{{ error }}</p>
      </section>

      <section class="p3-card">
        <h2>{{ t('customField.preview') }}</h2>
        <label class="p3-label">Equipment ID</label>
        <input v-model.number="equipmentId" class="p3-ipt" type="number" min="1" />
        <button class="p3-btn sm" @click="loadValues">{{ t('common.refresh') }}</button>
        <button class="p3-btn sm" @click="saveValues">{{ t('common.save') }}</button>
        <CustomFieldInputs v-model="values" :fields="fields" :empty-text="t('customField.empty')" />
      </section>
    </div>

    <section class="p3-card">
      <h2>{{ t('customField.title') }} ({{ fields.length }})</h2>
      <table class="p3-tbl">
        <thead>
          <tr>
            <th>Key</th>
            <th>ZH</th>
            <th>EN</th>
            <th>{{ t('customField.type') }}</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="f in fields" :key="f.id">
            <td class="p3-mono">{{ f.key }}</td>
            <td>{{ f.label_zh }}</td>
            <td>{{ f.label_en }}</td>
            <td>{{ f.type }}</td>
            <td>
              <button class="p3-btn sm danger" @click="removeField(f.id)">
                {{ t('customField.delete') }}
              </button>
            </td>
          </tr>
        </tbody>
      </table>
      <p v-if="!fields.length" class="p3-empty">{{ t('customField.empty') }}</p>
    </section>
  </div>
</template>

<script setup lang="ts">
import MockDataBanner from '@/components/common/MockDataBanner.vue'
import AsyncSection from '@/components/common/AsyncSection.vue'
import { onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import CustomFieldInputs from '@/components/common/CustomFieldInputs.vue'
import { p3Api, type CustomFieldRow } from '@/api/p3'

const { t } = useI18n()
const fields = ref<CustomFieldRow[]>([])
const values = ref<Record<string, unknown>>({})
const equipmentId = ref(1)
const optionsText = ref('')
const notice = ref('')
const error = ref('')
const loading = ref(false)
const form = reactive({
  key: '',
  label_zh: '',
  label_en: '',
  type: 'text' as CustomFieldRow['type'],
  options: [] as string[],
  required: false,
  applies_to: '*',
})

function fallback(err: unknown) {
  console.warn('[custom-fields] 后端不可达:', err)
  notice.value = t('customField.localFallback')
  if (!fields.value.length) {
    fields.value = [
      {
        id: -1,
        key: 'rack_color',
        label_zh: '机柜颜色',
        label_en: 'Rack Color',
        type: 'select',
        options: ['black', 'blue'],
        required: false,
        applies_to: '*',
      },
    ]
  }
}

async function reload() {
  loading.value = true
  try {
    fields.value = await p3Api.customFields()
    notice.value = ''
  } catch (err) {
    fallback(err)
  } finally {
    loading.value = false
  }
}

async function addField() {
  error.value = ''
  try {
    await p3Api.addCustomField({
      ...form,
      options:
        form.type === 'select'
          ? optionsText.value
              .split(',')
              .map((x) => x.trim())
              .filter(Boolean)
          : [],
    })
    await reload()
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  }
}

async function removeField(id: number) {
  if (id < 0) {
    fields.value = fields.value.filter((f) => f.id !== id)
    return
  }
  try {
    await p3Api.delCustomField(id)
    await reload()
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  }
}

async function loadValues() {
  try {
    const res = await p3Api.customValues(equipmentId.value)
    values.value = res.values
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  }
}

async function saveValues() {
  try {
    await p3Api.saveCustomValues(equipmentId.value, values.value)
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  }
}

onMounted(reload)
</script>
