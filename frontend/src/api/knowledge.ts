import request from './request'
import type { KnowledgeItem } from '@/types'

// ===== Knowledge 知识库 =====

export interface KnowledgeListResp {
  items: KnowledgeItem[]
  total: number
  page: number
  page_size: number
}

export interface KnowledgeCategoriesResp {
  categories: { name: string; count: number }[]
  total: number
}

export function getKnowledgeItems(params?: {
  page?: number
  page_size?: number
  category?: string
  q?: string
}): Promise<KnowledgeListResp> {
  return request.get('/api/ops/knowledge', { params }).then((r: any) => r)
}

// 后端已补 GET /api/ops/knowledge/categories 端点, 返回 { categories: [{name, count}], total }
export function getKnowledgeCategories(): Promise<KnowledgeCategoriesResp> {
  return request.get('/api/ops/knowledge/categories').then((r: any) => r)
}

export function getKnowledgeItem(id: number): Promise<KnowledgeItem> {
  return request.get(`/api/ops/knowledge/${id}`).then((r: any) => r)
}

export function createKnowledgeItem(data: Partial<KnowledgeItem>): Promise<KnowledgeItem> {
  return request.post('/api/ops/knowledge', data).then((r: any) => r)
}

export function updateKnowledgeItem(id: number, data: Partial<KnowledgeItem>): Promise<KnowledgeItem> {
  return request.put(`/api/ops/knowledge/${id}`, data).then((r: any) => r)
}

export function deleteKnowledgeItem(id: number): Promise<void> {
  return request.delete(`/api/ops/knowledge/${id}`)
}

export function importKnowledge(file: File): Promise<{ imported: number; items: KnowledgeItem[] }> {
  const formData = new FormData()
  formData.append('file', file)
  return request.post('/api/ops/knowledge/import', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 300000,
  }).then((r: any) => r)
}
