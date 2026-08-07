import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import request from '@/api/request'

export interface IdcSummary {
  id: number
  name: string
  region?: string
  status?: string
}

const CURRENT_KEY = 'dc_ioc_current_idc'

export const useDatacenterStore = defineStore('datacenter', () => {
  const currentIdcId = ref<number | null>(
    Number(localStorage.getItem(CURRENT_KEY)) || null,
  )
  const idcList = ref<IdcSummary[]>([])

  const currentIdc = computed(() =>
    idcList.value.find((i) => i.id === currentIdcId.value) || null,
  )

  function setCurrentIdc(id: number) {
    currentIdcId.value = id
    localStorage.setItem(CURRENT_KEY, String(id))
    // 预留: 持久化到后端 /api/idc/current (阶段3 后端就绪后启用)
    request
      .put(`/api/idc/current`, { idcId: id })
      .catch(() => {
        /* 后端未就绪时静默, 仅本地生效 */
      })
  }

  function setIdcList(list: IdcSummary[]) {
    idcList.value = list
    // 列表加载后若尚未选定当前中心, 默认选第一个
    if (currentIdcId.value == null && list.length) {
      setCurrentIdc(list[0].id)
    }
  }

  return { currentIdcId, idcList, currentIdc, setCurrentIdc, setIdcList }
})
