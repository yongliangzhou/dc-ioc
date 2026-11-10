<template>
  <div class="p3-page">
    <div class="p3-head">
      <h1>{{ t('ipam.title') }}</h1>
      <span class="sub">{{ t('ipam.subtitle') }}</span>
    </div>
    <MockDataBanner :level="notice ? 'full' : 'none'" :note="notice" />
    <AsyncSection :loading="loading" :empty="false" @retry="reload" />

    <div class="p3-tabs">
      <button
        v-for="tab in tabs"
        :key="tab"
        :class="{ active: active === tab }"
        @click="active = tab"
      >
        {{ t('ipam.tab' + tab) }}
      </button>
    </div>

    <!-- VLAN -->
    <section v-if="active === 'Vlan'" class="p3-card">
      <div class="p3-grid">
        <div>
          <label class="p3-label">VLAN ID</label>
          <input v-model.number="vlan.vlan_id" class="p3-ipt" type="number" min="1" max="4094" />
          <label class="p3-label">Name</label>
          <input v-model="vlan.name" class="p3-ipt" />
          <button class="p3-btn" @click="addVlan">{{ t('ipam.add') }}</button>
        </div>
        <div>
          <table class="p3-tbl">
            <thead>
              <tr>
                <th>VLAN</th>
                <th>Name</th>
                <th>Site</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="v in vlans" :key="v.id">
                <td class="p3-mono">{{ v.vlan_id }}</td>
                <td>{{ v.name }}</td>
                <td>{{ v.site }}</td>
                <td>
                  <button class="p3-btn sm danger" @click="delVlan(v.id)">
                    {{ t('ipam.delete') }}
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>

    <!-- 子网 -->
    <section v-if="active === 'Subnet'" class="p3-card">
      <div class="p3-grid">
        <div>
          <label class="p3-label">{{ t('ipam.cidr') }}</label>
          <input v-model="subnet.cidr" class="p3-ipt" placeholder="192.168.10.0/24" />
          <label class="p3-label">VLAN ID</label>
          <input v-model.number="subnet.vlan_id" class="p3-ipt" type="number" />
          <label class="p3-label">{{ t('ipam.gateway') }}</label>
          <input v-model="subnet.gateway" class="p3-ipt" />
          <button class="p3-btn" @click="addSubnet">{{ t('ipam.add') }}</button>
          <p v-if="error" class="p3-err">{{ error }}</p>
        </div>
        <div>
          <table class="p3-tbl">
            <thead>
              <tr>
                <th>CIDR</th>
                <th>{{ t('ipam.utilization') }}</th>
                <th>Used</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="s in subnets" :key="s.id">
                <td class="p3-mono">{{ s.cidr }}</td>
                <td>
                  <div class="p3-bar"><i :style="{ width: s.utilization_pct + '%' }"></i></div>
                  {{ s.utilization_pct }}%
                </td>
                <td>{{ s.used }} / {{ s.total }}</td>
                <td>
                  <button class="p3-btn sm" @click="allocate(s.id)">
                    {{ t('ipam.allocate') }}
                  </button>
                  <button class="p3-btn sm danger" @click="delSubnet(s.id)">
                    {{ t('ipam.delete') }}
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>

    <!-- IP 地址 -->
    <section v-if="active === 'Address'" class="p3-card">
      <div class="p3-grid">
        <div>
          <label class="p3-label">IP</label>
          <input v-model="address.address" class="p3-ipt" placeholder="192.168.10.10" />
          <label class="p3-label">Device CI</label>
          <input v-model="address.device_ci" class="p3-ipt" placeholder="equipment:12" />
          <button class="p3-btn" @click="addAddress">{{ t('ipam.add') }}</button>
        </div>
        <div>
          <table class="p3-tbl">
            <thead>
              <tr>
                <th>IP</th>
                <th>{{ t('ipam.status') }}</th>
                <th>Device CI</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="a in addresses" :key="a.id">
                <td class="p3-mono">{{ a.address }}</td>
                <td>
                  <span class="p3-tag">{{ a.status }}</span>
                </td>
                <td class="p3-mono">{{ a.device_ci }}</td>
                <td>
                  <button class="p3-btn sm danger" @click="delAddress(a.id)">
                    {{ t('ipam.delete') }}
                  </button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>

    <p v-if="!vlans.length && !subnets.length && !addresses.length" class="p3-empty">
      {{ t('ipam.empty') }}
    </p>
  </div>
</template>

<script setup lang="ts">
import MockDataBanner from '@/components/common/MockDataBanner.vue'
import AsyncSection from '@/components/common/AsyncSection.vue'
import { onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { p3Api, type P3Row, type SubnetRow } from '@/api/p3'

const { t } = useI18n()
const tabs = ['Vlan', 'Subnet', 'Address']
const active = ref('Vlan')
const vlans = ref<P3Row[]>([])
const subnets = ref<SubnetRow[]>([])
const addresses = ref<P3Row[]>([])
const notice = ref('')
const error = ref('')
const loading = ref(false)
const vlan = reactive({ vlan_id: 100, name: '', site: '' })
const subnet = reactive({ cidr: '192.168.10.0/24', vlan_id: 100, gateway: '' })
const address = reactive({ address: '', device_ci: '' })

function fallback(err: unknown) {
  console.warn('[ipam] 后端不可达:', err)
  notice.value = t('ipam.localFallback')
  if (!subnets.value.length) {
    subnets.value = [
      {
        id: -1,
        cidr: '192.168.10.0/24',
        vlan_id: 100,
        gateway: '192.168.10.1',
        total: 254,
        used: 12,
        available: 242,
        utilization_pct: 4.72,
      },
    ]
  }
}

async function reload() {
  loading.value = true
  try {
    ;[vlans.value, subnets.value, addresses.value] = await Promise.all([
      p3Api.vlans(),
      p3Api.subnets(),
      p3Api.addresses(),
    ])
    notice.value = ''
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

const addVlan = () => action(() => p3Api.addVlan({ ...vlan }))
const delVlan = (id: number) => action(() => p3Api.delVlan(id))
const addSubnet = () => action(() => p3Api.addSubnet({ ...subnet }))
const delSubnet = (id: number) => action(() => p3Api.delSubnet(id))
const addAddress = () => action(() => p3Api.addAddress({ ...address }))
const delAddress = (id: number) => action(() => p3Api.delAddress(id))
const allocate = (id: number) => action(() => p3Api.allocate(id, 'equipment:1'))

onMounted(reload)
</script>
