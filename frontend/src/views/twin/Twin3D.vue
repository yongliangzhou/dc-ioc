<template>
  <div class="twin3d" ref="root">
    <!-- 控制条 -->
    <div class="ctrl-bar">
      <div class="cb-title">{{ tl('twin3d') }}</div>
      <button class="btn-sm" @click="resetView">{{ tl('twin.resetView') }}</button>
      <div class="cb-sep" />
      <label class="cb-chk"><input type="checkbox" v-model="layers.idc" @change="applyLayers" /> {{ tl('twin.layerIdc') }}</label>
      <label class="cb-chk"><input type="checkbox" v-model="layers.room" @change="applyLayers" /> {{ tl('twin.layerRoom') }}</label>
      <label class="cb-chk"><input type="checkbox" v-model="layers.cabinet" @change="applyLayers" /> {{ tl('twin.layerCabinet') }}</label>
      <label class="cb-chk"><input type="checkbox" v-model="layers.device" @change="applyLayers" /> {{ tl('twin.layerDevice') }}</label>
      <div class="cb-sep" />
      <label class="cb-chk"><input type="checkbox" v-model="realtime" /> {{ tl('twin.realtime') }}</label>
    </div>

    <!-- 图例 -->
    <div class="legend">
      <span class="lg"><i class="dot online" /> {{ tl('common.online') }}</span>
      <span class="lg"><i class="dot off" /> {{ tl('common.offline') }}</span>
      <span class="lg"><i class="dot hot" /> {{ tl('twin.hot') }}</span>
    </div>

    <!-- 设备信息卡 -->
    <div class="info-card" v-if="selected">
      <button class="x" @click="selected = null">✕</button>
      <div class="ic-name">{{ selected.name || selected.device_id }}</div>
      <div class="ic-row"><span>{{ tl('twin.category') }}</span><b>{{ selected.category || '—' }}</b></div>
      <div class="ic-row"><span>{{ tl('twin.location') }}</span><b>{{ selected.location || '—' }}</b></div>
      <div class="ic-row"><span>{{ tl('common.status') }}</span>
        <b :class="selected.online ? 'on' : 'off'">{{ selected.online ? tl('common.online') : tl('common.offline') }}</b>
      </div>
      <div class="ic-row"><span>{{ tl('twin.temp') }}</span><b>{{ tempOf(selected).toFixed(1) }} ℃</b></div>
    </div>

    <div class="canvas-host" ref="host"></div>
    <div class="loading" v-if="loading">{{ tl('common.loading') }}</div>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { fetchTwinDevices, type TwinDevice } from '@/api/twin'
import { useDatacenterStore } from '@/stores/datacenter'

const { t: tl } = useI18n()
const dcStore = useDatacenterStore()

const root = ref<HTMLElement | null>(null)
const host = ref<HTMLElement | null>(null)
const loading = ref(true)
const realtime = ref(true)
const selected = ref<TwinDevice | null>(null)
const devices = ref<TwinDevice[]>([])
const layers = reactive({ idc: true, room: true, cabinet: true, device: true })

// three 资源
let renderer: THREE.WebGLRenderer | null = null
let scene: THREE.Scene | null = null
let camera: THREE.PerspectiveCamera | null = null
let controls: OrbitControls | null = null
let raf = 0
const groups: Record<string, THREE.Group> = {}
const meshDev: { mesh: THREE.Mesh; device: TwinDevice }[] = []
let raycaster = new THREE.Raycaster()
let pointer = new THREE.Vector2()
let presets: Record<string, { center: THREE.Vector3; cam: THREE.Vector3 }> = {}

const COL_ONLINE = new THREE.Color('#22d3ee')
const COL_OFFLINE = new THREE.Color('#475569')
const COL_HOT = new THREE.Color('#ef4444')
const COL_COLD = new THREE.Color('#3b82f6')

function tempOf(d: TwinDevice): number {
  // 由 device_id 派生确定性温度 (演示实时映射), 在线设备偏高
  const h = [...d.device_id].reduce((a, c) => a + c.charCodeAt(0), 0)
  const base = 18 + (h % 14)
  return d.online ? base + 6 : base - 4
}

function colorFor(d: TwinDevice): THREE.Color {
  const t = tempOf(d)
  if (!d.online) return COL_OFFLINE
  if (t >= 34) return COL_HOT
  return COL_COLD.clone().lerp(COL_ONLINE, (t - 18) / 20)
}

function disposeObj(o: THREE.Object3D) {
  o.traverse((c) => {
    const m = c as THREE.Mesh
    if (m.geometry) m.geometry.dispose()
    if (m.material) {
      const mat = m.material as THREE.Material | THREE.Material[]
      if (Array.isArray(mat)) mat.forEach((x) => x.dispose())
      else mat.dispose()
    }
  })
}

function clearScene() {
  Object.values(groups).forEach((g) => {
    if (g.parent) g.parent.remove(g)
    disposeObj(g)
  })
  for (const k of Object.keys(groups)) delete groups[k]
  meshDev.length = 0
}

function buildScene() {
  if (!scene || !host.value) return
  clearScene()
  const list = devices.value.filter((d) => !dcStore.currentIdcId || d.idc_id === dcStore.currentIdcId)
  // 分组: room -> cabinet -> devices
  const byRoom: Record<string, Record<string, TwinDevice[]>> = {}
  for (const d of list) {
    const loc = (d.location || 'R00/C00').split('/')
    const room = loc[0] || 'R00'
    const cab = loc[1] || 'C00'
    ;(byRoom[room] ||= {})
    ;(byRoom[room][cab] ||= []).push(d)
  }
  const roomKeys = Object.keys(byRoom)
  const roomGap = 14
  const cabGap = 4
  const rackGeo = new THREE.BoxGeometry(2.4, 5, 2.4)
  const devGeo = new THREE.BoxGeometry(1.6, 0.6, 1.6)

  let rx = 0
  for (const room of roomKeys) {
    const gRoom = new THREE.Group()
    gRoom.name = 'room:' + room
    groups['room:' + room] = gRoom
    scene.add(gRoom)
    const cabKeys = Object.keys(byRoom[room])
    let cx = 0
    for (const cab of cabKeys) {
      const gCab = new THREE.Group()
      gCab.name = 'cab:' + room + '/' + cab
      gCab.position.set(cx, 0, 0)
      gRoom.add(gCab)
      const mat = new THREE.MeshStandardMaterial({ color: 0x1e293b, metalness: 0.3, roughness: 0.7 })
      const rack = new THREE.Mesh(rackGeo, mat)
      rack.position.y = 2.5
      gCab.add(rack)
      const dd = byRoom[room][cab]
      dd.forEach((d, i) => {
        const gDev = new THREE.Group()
        const m = new THREE.Mesh(
          devGeo,
          new THREE.MeshStandardMaterial({ color: colorFor(d), emissive: colorFor(d).clone().multiplyScalar(0.25) }),
        )
        m.position.y = 0.8 + i * 0.9
        gDev.add(m)
        gDev.userData.device = d
        gCab.add(gDev)
        meshDev.push({ mesh: m, device: d })
      })
      cx += cabGap
    }
    gRoom.position.set(rx, 0, 0)
    rx += cx + roomGap
  }
  applyLayers()
  fitView()
}

function applyLayers() {
  const set = (name: string, vis: boolean) => {
    if (groups[name]) groups[name].visible = vis
  }
  Object.keys(groups).forEach((k) => {
    if (k.startsWith('room:')) set(k, layers.room)
  })
  // cabinet / device 透过多级 group 控制: 简化以 room 为主开关, cabinet/device 由 devices 显隐表达
  meshDev.forEach(({ mesh }) => {
    mesh.parent && (mesh.parent.visible = layers.cabinet)
    mesh.visible = layers.device
  })
  groups['idc'] && (groups['idc'].visible = layers.idc)
}

function fitView() {
  if (!camera || !controls || !host.value) return
  const w = host.value.clientWidth || 800
  const h = host.value.clientHeight || 600
  camera.aspect = w / h
  camera.updateProjectionMatrix()
  camera.position.set(0, 22, 46)
  controls.target.set(0, 4, 0)
  controls.update()
}

function resetView() {
  fitView()
}

function onResize() {
  if (!renderer || !camera || !host.value) return
  const w = host.value.clientWidth
  const h = host.value.clientHeight
  renderer.setSize(w, h)
  camera.aspect = w / h
  camera.updateProjectionMatrix()
}

function onPick(ev: PointerEvent) {
  if (!renderer || !camera || !host.value) return
  const rect = renderer.domElement.getBoundingClientRect()
  pointer.x = ((ev.clientX - rect.left) / rect.width) * 2 - 1
  pointer.y = -((ev.clientY - rect.top) / rect.height) * 2 + 1
  raycaster.setFromCamera(pointer, camera)
  const hits = raycaster.intersectObjects(meshDev.map((m) => m.mesh), false)
  if (hits.length) {
    const hit = meshDev.find((m) => m.mesh === hits[0].object)
    if (hit) selected.value = hit.device
  }
}

function paintRealtime() {
  for (const { mesh, device } of meshDev) {
    const c = colorFor(device)
    const mat = mesh.material as THREE.MeshStandardMaterial
    mat.color.copy(c)
    mat.emissive.copy(c.clone().multiplyScalar(0.25))
  }
}

function animate() {
  raf = requestAnimationFrame(animate)
  if (controls) controls.update()
  if (renderer && scene && camera) renderer.render(scene, camera)
}

async function load() {
  loading.value = true
  try {
    const r = await fetchTwinDevices({ idcId: dcStore.currentIdcId || undefined })
    devices.value = r.items || []
    buildScene()
  } catch {
    // 后端不可达时以空场景呈现, 不阻塞页面
    devices.value = []
  } finally {
    loading.value = false
  }
}

let poll = 0

onMounted(() => {
  if (!host.value) return
  const w = host.value.clientWidth
  const h = host.value.clientHeight
  scene = new THREE.Scene()
  scene.background = new THREE.Color('#0a0f1c')
  scene.fog = new THREE.Fog('#0a0f1c', 60, 140)
  camera = new THREE.PerspectiveCamera(50, w / h, 0.1, 1000)
  renderer = new THREE.WebGLRenderer({ antialias: true })
  renderer.setSize(w, h)
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
  host.value.appendChild(renderer.domElement)

  const amb = new THREE.AmbientLight(0x88aabb, 0.7)
  scene.add(amb)
  const dir = new THREE.DirectionalLight(0xffffff, 0.9)
  dir.position.set(20, 40, 30)
  scene.add(dir)
  const grid = new THREE.GridHelper(160, 40, 0x1e3a5f, 0x14223a)
  scene.add(grid)

  controls = new OrbitControls(camera, renderer.domElement)
  controls.enableDamping = true
  controls.dampingFactor = 0.08
  controls.maxPolarAngle = Math.PI * 0.49

  renderer.domElement.addEventListener('pointerdown', onPick)
  window.addEventListener('resize', onResize)
  animate()
  load()
  poll = window.setInterval(() => {
    if (realtime.value) load()
  }, 8000)
})

onBeforeUnmount(() => {
  cancelAnimationFrame(raf)
  clearInterval(poll)
  window.removeEventListener('resize', onResize)
  if (renderer) {
    renderer.domElement.removeEventListener('pointerdown', onPick)
    renderer.dispose()
  }
  clearScene()
  scene = null
  camera = null
  controls = null
  renderer = null
})
</script>

<style scoped>
.twin3d { position: relative; height: 100%; width: 100%; overflow: hidden; background: #0a0f1c; }
.canvas-host { position: absolute; inset: 0; }
.ctrl-bar {
  position: absolute; top: 14px; left: 14px; z-index: 5;
  display: flex; align-items: center; gap: 10px;
  padding: 8px 12px; border-radius: 12px;
  background: rgba(17, 24, 39, 0.72); backdrop-filter: blur(8px);
  border: 1px solid rgba(34, 211, 238, 0.2);
}
.cb-title { font-weight: 700; color: var(--cyan); font-size: 13px; }
.cb-sep { width: 1px; height: 18px; background: var(--line); }
.cb-chk { font-size: 12px; color: var(--txt2); display: flex; align-items: center; gap: 4px; cursor: pointer; }
.btn-sm { color: var(--cyan); border: 1px solid rgba(34, 211, 238, 0.3); background: transparent; border-radius: 8px; padding: 4px 10px; font-size: 12px; cursor: pointer; }
.legend { position: absolute; bottom: 14px; left: 14px; z-index: 5; display: flex; gap: 14px; padding: 8px 12px; border-radius: 10px; background: rgba(17, 24, 39, 0.72); backdrop-filter: blur(8px); border: 1px solid var(--line); }
.lg { font-size: 12px; color: var(--txt2); display: flex; align-items: center; gap: 6px; }
.dot { width: 10px; height: 10px; border-radius: 50%; display: inline-block; }
.dot.online { background: #22d3ee; box-shadow: 0 0 8px #22d3ee; }
.dot.off { background: #475569; }
.dot.hot { background: #ef4444; box-shadow: 0 0 8px #ef4444; }
.info-card { position: absolute; top: 14px; right: 14px; z-index: 6; width: 220px; padding: 14px; border-radius: 12px; background: rgba(17, 24, 39, 0.88); backdrop-filter: blur(8px); border: 1px solid rgba(34, 211, 238, 0.25); color: var(--txt); }
.ic-name { font-weight: 700; color: var(--cyan); margin-bottom: 10px; word-break: break-all; }
.ic-row { display: flex; justify-content: space-between; font-size: 12px; padding: 4px 0; border-top: 1px solid var(--line); }
.ic-row b.on { color: #22c55e; }
.ic-row b.off { color: #94a3b8; }
.x { position: absolute; top: 8px; right: 10px; background: none; border: none; color: var(--muted); cursor: pointer; font-size: 14px; }
.loading { position: absolute; inset: 0; display: flex; align-items: center; justify-content: center; color: var(--muted); font-size: 14px; }
</style>
