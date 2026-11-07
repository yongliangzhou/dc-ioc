<template>
  <div class="p3-page">
    <div class="p3-head">
      <h1>{{ t('discovery.title') }}</h1>
      <span class="sub">{{ t('discovery.subtitle') }}</span>
    </div>
    <p v-if="notice" class="p3-notice">{{ notice }}</p>
    <p class="p3-notice">{{ t('discovery.notice') }}</p>

    <section class="p3-card">
      <div class="p3-grid">
        <div>
          <label class="p3-label">{{ t('discovery.cidr') }}</label>
          <input v-model="form.cidr" class="p3-ipt" placeholder="192.168.1.0/30" />
          <label class="p3-label">{{ t('discovery.ports') }}</label>
          <input v-model="portsText" class="p3-ipt" placeholder="22,80,443,161,8080" />
          <button class="p3-btn" :disabled="scanning" @click="scan">
            {{ scanning ? t('discovery.scanning') : t('discovery.scan') }}
          </button>
          <p v-if="error" class="p3-err">{{ error }}</p>
        </div>
        <div>
          <h2>{{ t('discovery.pending') }} ({{ pending.length }})</h2>
          <table class="p3-tbl">
            <thead>
              <tr>
                <th>{{ t('discovery.ip') }}</th>
                <th>{{ t('discovery.openPorts') }}</th>
                <th>{{ t('discovery.status') }}</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="c in candidates" :key="c.id">
                <td class="p3-mono">{{ c.ip }}</td>
                <td class="p3-mono">{{ (c.open_ports || []).join(', ') }}</td>
                <td>
                  <span class="p3-tag">{{ t('discovery.' + c.status) }}</span>
                </td>
                <td>
                  <button
                    v-if="c.status === 'pending'"
                    class="p3-btn sm"
                    @click="decide(c.id, 'confirm')"
                  >
                    {{ t('discovery.confirm') }}
                  </button>
                  <button
                    v-if="c.status === 'pending'"
                    class="p3-btn sm danger"
                    @click="decide(c.id, 'reject')"
                  >
                    {{ t('discovery.reject') }}
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
          <p v-if="!candidates.length" class="p3-empty">{{ t('discovery.empty') }}</p>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { p3Api, type CandidateRow } from '@/api/p3'

const { t } = useI18n()
const form = ref({ cidr: '192.168.1.0/30', concurrency: 50 })
const portsText = ref('22,80,443,161,8080')
const candidates = ref<CandidateRow[]>([])
const notice = ref('')
const error = ref('')
const scanning = ref(false)
const pending = computed(() => candidates.value.filter((c) => c.status === 'pending'))

function fallback(err: unknown) {
  console.warn('[discovery] 后端不可达:', err)
  notice.value = t('discovery.localFallback')
  if (!candidates.value.length) {
    candidates.value = [
      {
        id: -1,
        ip: '192.168.1.1',
        open_ports: [80, 443],
        status: 'pending',
        matched_ci: '',
      },
    ]
  }
}

async function reload() {
  try {
    candidates.value = await p3Api.candidates()
    notice.value = ''
  } catch (err) {
    fallback(err)
  }
}

async function scan() {
  scanning.value = true
  error.value = ''
  try {
    const ports = portsText.value
      .split(',')
      .map((x) => Number(x.trim()))
      .filter((x) => x > 0)
    await p3Api.scan({ cidr: form.value.cidr, ports, concurrency: form.value.concurrency })
    await reload()
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  } finally {
    scanning.value = false
  }
}

async function decide(id: number, action: 'confirm' | 'reject') {
  if (id < 0) {
    const status: CandidateRow['status'] = action === 'confirm' ? 'confirmed' : 'rejected'
    candidates.value = candidates.value.map((c) => (c.id === id ? { ...c, status } : c))
    return
  }
  try {
    if (action === 'confirm') await p3Api.confirm(id)
    else await p3Api.reject(id)
    await reload()
  } catch (err) {
    error.value = err instanceof Error ? err.message : String(err)
  }
}

onMounted(reload)
</script>
