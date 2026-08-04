/**
 * 统一错误形状，用于 catch (e: unknown) 后安全读取常见字段。
 * 后端错误体通常形如 { detail, message, response: { data: { detail, message } } }。
 */
export interface ErrorLike {
  detail?: string
  message?: string
  status?: number
  response?: {
    data?: {
      detail?: string
      message?: string
    }
  }
}

export function toErrorLike(e: unknown): ErrorLike {
  if (e && typeof e === 'object') return e as ErrorLike
  return {}
}

export function errorText(e: unknown, fallback = '操作失败'): string {
  const err = toErrorLike(e)
  return err.detail || err.message || (err.response?.data?.detail ?? '') || fallback
}
