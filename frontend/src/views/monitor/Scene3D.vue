<template>
  <div class="scene3d" ref="root">
    <!-- 顶部工具条 -->
    <div class="ctrl-bar">
      <div class="cb-title">{{ tl('3D 视图') }}</div>
      <div class="cb-sep" />
      <!-- 层级导航：园区 -> 楼栋 -> 机房 -> 机柜 -->
      <button
        v-for="lv in levels"
        :key="lv.key"
        class="lv-btn"
        :class="{ on: level === lv.key }"
        @click="goLevel(lv.key)"
      >
        {{ lv.label }}
      </button>
      <div class="cb-sep" />
      <!-- 2D / 3D 切换 -->
      <div class="seg">
        <button :class="{ on: mode === '3d' }" @click="setMode('3d')">3D</button>
        <button :class="{ on: mode === '2d' }" @click="setMode('2d')">2D</button>
      </div>
      <button class="btn-sm" @click="fitCurrent">{{ tl('twin.resetView') }}</button>
    </div>

    <!-- 面包屑 -->
    <div class="crumbs">
      <span
        v-for="(c, i) in crumbs"
        :key="i"
        :class="{ cur: i === crumbs.length - 1 }"
        @click="jumpCrumb(i)"
        >{{ c }}<i v-if="i < crumbs.length - 1"> / </i></span
      >
    </div>

    <!-- 图例 -->
    <div class="legend">
      <span class="lg"><i class="dot online" /> {{ tl('common.online') }}</span>
      <span class="lg"><i class="dot off" /> {{ tl('common.offline') }}</span>
      <span class="lg"><i class="dot hot" /> {{ tl('twin.hot') }}</span>
    </div>

    <!-- 信息卡 -->
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
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import * as THREE from 'three'
import { OrbitControls } from 'three/examples/jsm/controls/OrbitControls.js'
import { fetchTwinDevices, type TwinDevice } from '@/api/twin'
import { useDatacenterStore } from '@/stores/datacenter'

const { t: tl } = useI18n()
const dcStore = useDatacenterStore()

type LevelKey = 'campus' | 'building' | 'room' | 'cabinet'
const levels: { key: LevelKey; label: string }[] = [
  { key: 'campus', label: tl('园区') },
  { key: 'building', label: tl('楼栋') },
  { key: 'room', label: tl('机房') },
  { key: 'cabinet', label: tl('机柜') },
]

const root = ref<HTMLElement | null>(null)
const host = ref<HTMLElement | null>(null)
const loading = ref(true)
const mode = ref<'2d' | '3d'>('3d')
const level = ref<LevelKey>('campus')
const selectedRoom = ref<string>('')
const selected = ref<TwinDevice | null>(null)
const devices = ref<TwinDevice[]>([])

const COL_ONLINE = new THREE.Color('#22d3ee')
const COL_OFFLINE = new THREE.Color('#475569')
const COL_HOT = new THREE.Color('#ef4444')
const COL_COLD = new THREE.Color('#3b82f6')

// three 资源
let renderer: THREE.WebGLRenderer | null = null
let scene: THREE.Scene | null = null
let camera: THREE.PerspectiveCamera | null = null
let orthoCam: THREE.OrthographicCamera | null = null
let controls: OrbitControls | null = null
let raf = 0
const groups: Record<string, THREE.Group> = {}
const meshes: { mesh: THREE.Mesh; device: TwinDevice }[] = []
let raycaster = new THREE.Raycaster()
let pointer = new THREE.Vector2()
// 层级包围盒中心/半径
let levelBox: Record<string, { center: THREE.Vector3; radius: number }> = {}

function tempOf(d: TwinDevice): number {
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
  meshes.length = 0
}

function buildScene() {
  if (!scene) return
  clearScene()
  const idcId = dcStore.currentIdcId || undefined
  const list = devices.value.filter((d) => !idcId || d.idc_id === idcId)

  // 分组 room -> cabinet -> devices
  const byRoom: Record<string, Record<string, TwinDevice[]>> = {}
  for (const d of list) {
    const loc = (d.location || 'R00/C00').split('/')
    const room = loc[0] || 'R00'
    const cab = loc[1] || 'C00'
    ;(byRoom[room] ||= {})
    ;(byRoom[room][cab] ||= []).push(d)
  }
  const roomKeys = Object.keys(byRoom).sort()
  const roomGap = 16
  const cabGap = 4
  const rackGeo = new THREE.BoxGeometry(2.4, 5, 2.4)
  const devGeo = new THREE.BoxGeometry(1.6, 0.6, 1.6)
  const floorGeo = new THREE.BoxGeometry(roomGap - 2, 0.4, 0)
  let rx = 0
  const roomCenters: { room: string; center: THREE.Vector3 }[] = []

  for (const room of roomKeys) {
    const gRoom = new THREE.Group()
    gRoom.name = 'room:' + room
    groups['room:' + room] = gRoom
    scene.add(gRoom)
    const cabKeys = Object.keys(byRoom[room]).sort()
    let cx = 0
    let maxY = 0
    for (const cab of cabKeys) {
      const gCab = new THREE.Group()
      gCab.name = 'cab:' + room + '/' + cab
      gCab.position.set(cx, 0, 0)
      gRoom.add(gCab)
      const mat = new THREE.MeshStandardMaterial({ color: 0x1e293b, metalness: 0.3, roughness: 0.7 })
      const rack = new THREE.Mesh(rackGeo, mat)
      rack.position.y = 2.5
      rack.userData.cab = room + '/' + cab
      gCab.add(rack)
      const dd = byRoom[room][cab]
      dd.forEach((d, i) => {
        const m = new THREE.Mesh(
          devGeo,
          new THREE.MeshStandardMaterial({ color: colorFor(d), emissive: colorFor(d).clone().multiplyScalar(0.25) }),
        )
        m.position.y = 0.8 + i * 0.9
        m.userData.device = d
        gCab.add(m)
        meshes.push({ mesh: m, device: d })
      })
      maxY = Math.max(maxY, rack.position.y)
      cx += cabGap
    }
    // 机房地板
    const fl = new THREE.Mesh(
      new THREE.BoxGeometry(Math.max(cx, 4), 0.2, 6),
      new THREE.MeshStandardMaterial({ color: 0x14233a, transparent: true, opacity: 0.5 }),
    )
    fl.position.set(cx / 2 - 2, 0.1, 0)
    gRoom.add(fl)
    gRoom.position.set(rx, 0, 0)
    roomCenters.push({ room, center: new THREE.Vector3(rx + cx / 2, maxY / 2, 0) })
    rx += cx + roomGap
  }

  // 楼栋/园区层级（用半透明包围框表达）
  const span = rx
  const building = new THREE.Group()
  building.name = 'building'
  groups['building'] = building
  scene.add(building)
  const bBox = new THREE.Mesh(
    new THREE.BoxGeometry(span + 8, 12, 16),
    new THREE.MeshStandardMaterial({ color: 0x0ea5e9, transparent: true, opacity: 0.06, wireframe: true }),
  )
  bBox.position.set(span / 2, 6, 0)
  building.add(bBox)

  const campus = new THREE.Group()
  campus.name = 'campus'
  groups['campus'] = campus
  scene.add(campus)
  const cBox = new THREE.Mesh(
    new THREE.BoxGeometry(span + 40, 40, 60),
    new THREE.MeshStandardMaterial({ color: 0x22c55e, transparent: true, opacity: 0.05, wireframe: true }),
  )
  cBox.position.set(span / 2, 20, 0)
  campus.add(cBox)

  // 计算各层级包围盒
  levelBox = {
    cabinet: { center: new THREE.Vector3(span / 2, 3, 0), radius: 18 },
    room: { center: new THREE.Vector3(span / 2, 4, 0), radius: 30 },
    building: { center: new THREE.Vector3(span / 2, 8, 0), radius: 55 },
    campus: { center: new THREE.Vector3(span / 2, 18, 0), radius: 110 },
  }
  // 若选中具体机房，cabinet 层聚焦该机房
  if (selectedRoom.value && roomCenters.length) {
    const rc = roomCenters.find((r) => r.room === selectedRoom.value)
    if (rc) levelBox.cabinet = { center: rc.center, radius: 20 }
  }
  applyVisibility()
  fitCurrent()
}

function applyVisibility() {
  // 园区/楼栋层级框仅在相应层级显示
  groups['campus'] && (groups['campus'].visible = level.value === 'campus')
  groups['building'] && (groups['building'].visible = level.value === 'building')
  const showRoom = level.value === 'room' || level.value === 'cabinet'
  Object.keys(groups).forEach((k) => {
    if (k.startsWith('room:')) {
      const room = k.split(':')[1]
      groups[k].visible = showRoom && (!selectedRoom.value || selectedRoom.value === room)
    }
  })
}

function goLevel(k: LevelKey) {
  level.value = k
  if (k === 'campus' || k === 'building') selectedRoom.value = ''
  applyVisibility()
  fitCurrent()
}

function setMode(m: '2d' | '3d') {
  mode.value = m
  applyCam()
  fitCurrent()
}

function applyCam() {
  if (!host.value || !controls) return
  if (mode.value === '2d') {
    if (!orthoCam) {
      const w = host.value.clientWidth
      const h = host.value.clientHeight
      orthoCam = new THREE.OrthographicCamera(-w / 2, w / 2, h / 2, -h / 2, 0.1, 2000)
    }
    controls.object = orthoCam
    if (camera) (camera as any).visible = false
  } else {
    if (camera) {
      controls.object = camera
      camera.visible = true
    }
    orthoCam = null
  }
  controls.update()
}

function fitCurrent() {
  if (!controls) return
  const box = levelBox[level.value] || levelBox.cabinet
  const cam = (mode.value === '2d' ? orthoCam : camera) as THREE.Camera | null
  if (!cam) return
  const r = box.radius
  if (mode.value === '2d' && orthoCam) {
    const w = host.value?.clientWidth || 800
    const h = host.value?.clientHeight || 600
    const zoom = Math.max(w, h) / (r * 2.4)
    orthoCam.zoom = zoom
    orthoCam.position.set(box.center.x, box.center.y, 200)
    orthoCam.lookAt(box.center)
    orthoCam.updateProjectionMatrix()
  } else if (camera) {
    camera.position.set(box.center.x, box.center.y + r * 0.9, box.center.z + r * 1.6)
    camera.lookAt(box.center)
  }
  controls.target.copy(box.center)
  controls.update()
}

const crumbs = computed(() => {
  const arr = [tl('园区')]
  if (level.value === 'building' || level.value === 'room' || level.value === 'cabinet') arr.push(tl('楼栋'))
  if (level.value === 'room' || level.value === 'cabinet') arr.push(tl('机房'))
  if (level.value === 'cabinet') arr.push(tl('机柜'))
  return arr
})
function jumpCrumb(i: number) {
  const map: number[] = [0, 1, 2, 3]
  const lv = (['campus', 'building', 'room', 'cabinet'] as LevelKey[])[map[i] ?? 0]
  goLevel(lv)
}

function onResize() {
  if (!renderer || !host.value) return
  const w = host.value.clientWidth
  const h = host.value.clientHeight
  renderer.setSize(w, h)
  if (camera) {
    camera.aspect = w / h
    camera.updateProjectionMatrix()
  }
  if (orthoCam) {
    orthoCam.left = -w / 2
    orthoCam.right = w / 2
    orthoCam.top = h / 2
    orthoCam.bottom = -h / 2
    orthoCam.updateProjectionMatrix()
  }
}

function onPick(ev: PointerEvent) {
  if (!renderer) return
  const rect = renderer.domElement.getBoundingClientRect()
  pointer.x = ((ev.clientX - rect.left) / rect.width) * 2 - 1
  pointer.y = -((ev.clientY - rect.top) / rect.height) * 2 + 1
  raycaster.setFromCamera(pointer, (controls?.object as THREE.Camera) || camera!)
  const hits = raycaster.intersectObjects(meshes.map((m) => m.mesh), false)
  if (hits.length) {
    const hit = meshes.find((m) => m.mesh === hits[0].object)
    if (hit) {
      selected.value = hit.device
      const loc = (hit.device.location || 'R00/C00').split('/')
      selectedRoom.value = loc[0] || 'R00'
      level.value = 'cabinet'
      applyVisibility()
      fitCurrent()
    }
  }
}

function paintRealtime() {
  for (const { mesh, device } of meshes) {
    const c = colorFor(device)
    const mat = mesh.material as THREE.MeshStandardMaterial
    mat.color.copy(c)
    mat.emissive.copy(c.clone().multiplyScalar(0.25))
  }
}

function animate() {
  raf = requestAnimationFrame(animate)
  if (controls) controls.update()
  if (renderer && scene) renderer.render(scene, (controls?.object as THREE.Camera) || camera!)
}

async function load() {
  loading.value = true
  try {
    const r = await fetchTwinDevices({ idcId: dcStore.currentIdcId || undefined })
    devices.value = r.items || []
    buildScene()
  } catch {
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
  scene.fog = new THREE.Fog('#0a0f1c', 80, 220)
  camera = new THREE.PerspectiveCamera(50, w / h, 0.1, 2000)
  renderer = new THREE.WebGLRenderer({ antialias: true })
  renderer.setSize(w, h)
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2))
  host.value.appendChild(renderer.domElement)

  const amb = new THREE.AmbientLight(0x88aabb, 0.7)
  scene.add(amb)
  const dir = new THREE.DirectionalLight(0xffffff, 0.9)
  dir.position.set(20, 40, 30)
  scene.add(dir)
  const grid = new THREE.GridHelper(220, 44, 0x1e3a5f, 0x14223a)
  scene.add(grid)

  controls = new OrbitControls(camera, renderer.domElement)
  controls.enableDamping = true
  controls.dampingFactor = 0.08
  controls.maxPolarAngle = Math.PI * 0.49
  applyCam()

  renderer.domElement.addEventListener('pointerdown', onPick)
  window.addEventListener('resize', onResize)
  animate()
  load()
  poll = window.setInterval(() => {
    if (devices.value.length) paintRealtime()
  }, 5000)
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
})
</script>

<style scoped>
.scene3d { position: relative; height: 100%; width: 100%; overflow: hidden; background: #0a0f1c; }
.canvas-host { position: absolute; inset: 0; }
.ctrl-bar {
  position: absolute; top: 14px; left: 14px; z-index: 5;
  display: flex; align-items: center; gap: 8px;
  padding: 8px 12px; border-radius: 12px;
  background: rgba(17, 24, 39, 0.72); backdrop-filter: blur(8px);
  border: 1px solid rgba(34, 211, 238, 0.2); flex-wrap: wrap;
}
.cb-title { font-weight: 700; color: var(--cyan); font-size: 13px; }
.cb-sep { width: 1px; height: 18px; background: var(--line); }
.lv-btn { color: var(--txt2); border: 1px solid var(--line); background: transparent; border-radius: 8px; padding: 4px 10px; font-size: 12px; cursor: pointer; }
.lv-btn.on { color: var(--cyan); border-color: rgba(34, 211, 238, 0.5); background: rgba(34, 211, 238, 0.1); }
.seg { display: flex; border: 1px solid var(--line); border-radius: 8px; overflow: hidden; }
.seg button { color: var(--txt2); background: transparent; border: none; padding: 4px 12px; font-size: 12px; cursor: pointer; }
.seg button.on { color: #06121f; background: var(--cyan); font-weight: 700; }
.btn-sm { color: var(--cyan); border: 1px solid rgba(34, 211, 238, 0.3); background: transparent; border-radius: 8px; padding: 4px 10px; font-size: 12px; cursor: pointer; }
.crumbs { position: absolute; top: 64px; left: 14px; z-index: 5; display: flex; gap: 2px; font-size: 12px; color: var(--txt2); padding: 6px 12px; border-radius: 10px; background: rgba(17,24,39,0.72); backdrop-filter: blur(8px); border: 1px solid var(--line); }
.crumbs span { cursor: pointer; }
.crumbs span.cur { color: var(--cyan); cursor: default; }
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
