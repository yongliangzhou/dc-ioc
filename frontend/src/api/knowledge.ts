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

export interface KnowledgeImportResult {
  created: number
  skipped: number
  total: number
  imported: number
  items: KnowledgeItem[]
  note?: string
}

export function importKnowledge(file: File): Promise<KnowledgeImportResult> {
  const formData = new FormData()
  formData.append('file', file)
  return request.post<unknown, KnowledgeImportResult>(
    '/api/ops/knowledge/import',
    formData,
    {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: 300000,
    },
  )
}

// 人工审核工作台: 待审核列表
export function getPendingKnowledge(): Promise<{ total: number; items: KnowledgeItem[] }> {
  return request.get<unknown, { total: number; items: KnowledgeItem[] }>('/api/ops/knowledge/review/pending')
}

// 审核一条知识条目: approved 通过 / rejected 驳回
export function reviewKnowledge(
  id: number,
  status: 'approved' | 'rejected',
  note?: string,
): Promise<KnowledgeItem> {
  return request.post<unknown, KnowledgeItem>(`/api/ops/knowledge/${id}/review`, {
    status,
    note: note || '',
  })
}
