<template>
  <div class="p3-page">
    <div class="p3-head">
      <h1>{{ t('assetBusiness.title') }}</h1>
      <span class="sub">{{ t('assetBusiness.subtitle') }}</span>
    </div>
    <MockDataBanner :level="notice ? 'full' : 'none'" :note="notice" />
    <AsyncSection :loading="loading" :empty="false" @retry="reload" />

    <div class="p3-tabs">
      <button :class="{ active: tab === 'Orders' }" @click="tab = 'Orders'">
        {{ t('assetBusiness.tabOrders') }}
      </button>
      <button :class="{ active: tab === 'Stocktake' }" @click="tab = 'Stocktake'">
        {{ t('assetBusiness.tabStocktake') }}
      </button>
    </div>

    <!-- 采购合同 -->
    <section v-if="tab === 'Orders'" class="p3-card">
      <div class="p3-grid">
        <div>
          <label class="p3-label">{{ t('assetBusiness.orderNo') }}</label>
          <input v-model="order.order_no" class="p3-ipt" />
          <label class="p3-label">{{ t('assetBusiness.vendor') }}</label>
          <input v-model="order.vendor" class="p3-ipt" />
          <label class="p3-label">{{ t('assetBusiness.amount') }}</label>
          <input v-model.number="order.amount" class="p3-ipt" type="number" />
          <label class="p3-label">{{ t('assetBusiness.warrantyUntil') }}</label>
          <input v-model="order.warranty_until" class="p3-ipt" type="date" />
          <button class="p3-btn" @click="addOrder">{{ t('assetBusiness.add') }}</button>
          <p v-if="expiring.length" class="p3-notice" style="margin-top: 14px">
            {{ t('assetBusiness.expiringSoon') }}: {{ expiring.length }}
          </p>
        </div>
        <div>
          <table class="p3-tbl">
            <thead>
              <tr>
                <th>{{ t('assetBusiness.orderNo') }}</th>
                <th>{{ t('assetBusiness.vendor') }}</th>
                <th>{{ t('assetBusiness.amount') }}</th>
                <th>{{ t('assetBusiness.warrantyUntil') }}</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="o in orders" :key="o.id">
                <td class="p3-mono">{{ o.order_no }}</td>
                <td>{{ o.vendor }}</td>
                <td>{{ o.amount }}</td>
                <td class="p3-mono">{{ o.warranty_until }}</td>
                <td>
                  <button class="p3-btn sm danger" @click="delOrder(o.id)">
                    {{ t('common.delete') }}
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>

    <!-- 盘点 -->
    <section v-else class="p3-card">
      <div class="p3-grid">
        <div>
          <label class="p3-label">{{ t('assetBusiness.taskName') }}</label>
          <input v-model="task.name" class="p3-ipt" />
          <label class="p3-label">{{ t('assetBusiness.scope') }}</label>
          <input v-model="task.scope" class="p3-ipt" />
          <button class="p3-btn" @click="addTask">{{ t('assetBusiness.add') }}</button>
          <label class="p3-label" style="margin-top: 18px">{{ t('assetBusiness.assetCi') }}</label>
          <input v-model="item.asset_ci" class="p3-ipt" placeholder="equipment:12" />
          <select v-model="item.result" class="p3-ipt">
            <option value="matched">{{ t('assetBusiness.matched') }}</option>
            <option value="missing">{{ t('assetBusiness.missing') }}</option>
            <option value="unexpected">{{ t('assetBusiness.unexpected') }}</option>
          </select>
          <button class="p3-btn" :disabled="!currentTask" @click="addItem">
            {{ t('assetBusiness.mark') }}
          </button>
          <button
            class="p3-btn sm"
            style="margin-left: 8px"
            :disabled="!currentTask"
            @click="loadReport"
          >
            {{ t('assetBusiness.report') }}
          </button>
          <div v-if="report" class="p3-card" style="margin-top: 14px">
            <h2>{{ t('assetBusiness.report') }}</h2>
            <p class="p3-mono">
              matched: {{ report.matched }} / expected: {{ report.expected_total }}
            </p>
            <p class="p3-mono">coverage: {{ report.coverage_pct }}%</p>
            <p class="p3-mono">missing: {{ String(report.missing) }}</p>
            <p class="p3-mono">unexpected: {{ String(report.unexpected) }}</p>
          </div>
        </div>
        <div>
          <table class="p3-tbl">
            <thead>
              <tr>
                <th>ID</th>
                <th>{{ t('assetBusiness.taskName') }}</th>
                <th>{{ t('assetBusiness.scope') }}</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="x in tasks" :key="x.id" @click="selectTask(x.id)" style="cursor: pointer">
                <td class="p3-mono">{{ x.id }}</td>
                <td>{{ x.name }}</td>
                <td>{{ x.scope }}</td>
              </tr>
            </tbody>
          </table>
          <p v-if="currentTask" class="p3-mono" style="font-size: 11px; color: var(--txt2)">
            selected: #{{ currentTask }}
          </p>
        </div>
      </div>
      <p v-if="error" class="p3-err">{{ error }}</p>
    </section>

    <p v-if="!orders.length && !tasks.length" class="p3-empty">{{ t('assetBusiness.empty') }}</p>
  </div>
</template>

<script setup lang="ts">
import MockDataBanner from '@/components/common/MockDataBanner.vue'
import AsyncSection from '@/components/common/AsyncSection.vue'
import { onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { p3Api, type P3Row } from '@/api/p3'

const { t } = useI18n()
const tab = ref('Orders')
const orders = ref<P3Row[]>([])
const tasks = ref<P3Row[]>([])
const expiring = ref<P3Row[]>([])
const report = ref<Record<string, unknown> | null>(null)
const currentTask = ref<number | null>(null)
const notice = ref('')
const error = ref('')
const loading = ref(false)
const order = reactive({
  order_no: '',
  vendor: '',
  amount: 0,
  warranty_until: '',
  purchase_date: '',
  contract_no: '',
})
const task = reactive({ name: '', scope: '' })
const item = reactive({ asset_ci: '', result: 'matched' })

function fallback(err: unknown) {
  console.warn('[asset-business] 后端不可达:', err)
  notice.value = t('assetBusiness.localFallback')
  if (!orders.value.length) {
    orders.value = [
      {
        id: -1,
        order_no: 'PO-DEMO-001',
        vendor: 'ACME',
        amount: 128000,
        warranty_until: '2026-12-31',
        contract_no: 'CT-001',
      },
    ]
  }
}

async function reload() {
  loading.value = true
  try {
    ;[orders.value, tasks.value, expiring.value] = await Promise.all([
      p3Api.orders(),
      p3Api.tasks(),
      p3Api.expiring(30),
    ])
    notice.value = ''
    if (!currentTask.value && tasks.value.length) currentTask.value = Number(tasks.value[0].id)
  } catch (err) {
    fallback(err)
  } finally {
    loading.value = false
  }
}

async function action(fn: () => Promise<unknown>) {
  error.value = ''
  try {
    await fn()
    await reload()
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  }
}

const addOrder = () => action(() => p3Api.addOrder({ ...order }))
const delOrder = (id: number) => action(() => p3Api.delOrder(id))
const addTask = () => action(() => p3Api.addTask({ ...task }))
const addItem = () =>
  currentTask.value
    ? action(() => p3Api.addItem(currentTask.value as number, { ...item }))
    : Promise.resolve()
const selectTask = (id: number) => {
  currentTask.value = Number(id)
  report.value = null
}
async function loadReport() {
  if (!currentTask.value) return
  try {
    report.value = await p3Api.report(currentTask.value)
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  }
}

onMounted(reload)
</script>
