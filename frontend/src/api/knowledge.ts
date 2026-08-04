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
  return request.get<unknown, KnowledgeListResp>('/api/ops/knowledge', { params })
}

// 后端已补 GET /api/ops/knowledge/categories 端点, 返回 { categories: [{name, count}], total }
export function getKnowledgeCategories(): Promise<KnowledgeCategoriesResp> {
  return request.get<unknown, KnowledgeCategoriesResp>('/api/ops/knowledge/categories')
}

export function getKnowledgeItem(id: number): Promise<KnowledgeItem> {
  return request.get<unknown, KnowledgeItem>(`/api/ops/knowledge/${id}`)
}

export function createKnowledgeItem(data: Partial<KnowledgeItem>): Promise<KnowledgeItem> {
  return request.post<unknown, KnowledgeItem>('/api/ops/knowledge', data)
}

export function updateKnowledgeItem(
  id: number,
  data: Partial<KnowledgeItem>,
): Promise<KnowledgeItem> {
  return request.put<unknown, KnowledgeItem>(`/api/ops/knowledge/${id}`, data)
}

export function deleteKnowledgeItem(id: number): Promise<void> {
  return request.delete(`/api/ops/knowledge/${id}`)
}

export function importKnowledge(file: File): Promise<{ imported: number; items: KnowledgeItem[] }> {
  const formData = new FormData()
  formData.append('file', file)
  return request.post<unknown, { imported: number; items: KnowledgeItem[] }>(
    '/api/ops/knowledge/import',
    formData,
    {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 300000,
    },
  )
}
