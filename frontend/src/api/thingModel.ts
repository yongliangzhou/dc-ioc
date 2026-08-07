import request from './request'

export type ItemType = 'property' | 'service' | 'event'
export type DataType = 'float' | 'int' | 'bool' | 'string' | 'enum' | 'command'

export interface ThingModelItem {
  id?: number
  thingModelId?: number
  itemType: ItemType
  identifier: string
  name: string
  dataType: DataType
  unit: string
  desc: string
  extra: Record<string, unknown>
}

export interface ThingModel {
  id: number
  modelKey: string
  name: string
  category: string
  domain: string
  protocol: string
  vendor: string
  description: string
  items: ThingModelItem[]
  createdAt?: string
  updatedAt?: string
}

export interface ThingModelCreate {
  modelKey: string
  name: string
  category: string
  domain: string
  protocol: string
  vendor: string
  description: string
  items: Omit<ThingModelItem, 'id' | 'thingModelId'>[]
}

export const listThingModels = (params: { kw?: string; category?: string; domain?: string } = {}) =>
  request.get<unknown, ThingModel[]>('/api/thing-models', { params })

export const getThingModel = (id: number) =>
  request.get<unknown, ThingModel>(`/api/thing-models/${id}`)

export const createThingModel = (data: ThingModelCreate) =>
  request.post<unknown, ThingModel>('/api/thing-models', data)

export const updateThingModel = (id: number, data: Partial<ThingModelCreate>) =>
  request.put<unknown, ThingModel>(`/api/thing-models/${id}`, data)

export const deleteThingModel = (id: number) =>
  request.delete(`/api/thing-models/${id}`)
