/**
 * 统一的客户端导出工具
 *
 * 各页面的导出此前各写一份 Blob 逻辑（CSV 转义 / BOM / 释放 URL 各不相同），
 * 这里收敛为两个函数，保证 Excel 中文不乱码、换行与引号不出错。
 */

export type CsvCell = string | number | boolean | null | undefined

/** CSV 单元格转义: 含分隔符/引号/换行时加双引号, 内部引号翻倍 */
function escapeCell(v: CsvCell): string {
  if (v === null || v === undefined) return ''
  const s = String(v)
  if (/[",\r\n]/.test(s)) return `"${s.replace(/"/g, '""')}"`
  return s
}

/** 触发浏览器下载（文本） */
export function downloadText(filename: string, text: string, mime = 'text/plain;charset=utf-8') {
  const blob = new Blob([text], { type: mime })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  document.body.removeChild(a)
  // 立即 revoke 在部分浏览器会中断下载, 延迟释放更稳
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}

/**
 * 导出 CSV。
 * - 自动加 UTF-8 BOM, Excel 打开中文不乱码
 * - 单元格按 RFC 4180 转义
 */
export function downloadCsv(filename: string, headers: string[], rows: CsvCell[][]) {
  const lines = [headers.map(escapeCell).join(','), ...rows.map((r) => r.map(escapeCell).join(','))]
  downloadText(filename, `﻿${lines.join('\r\n')}`, 'text/csv;charset=utf-8')
}

/** 文件名安全化 + 时间戳, 便于归档 */
export function stampedName(prefix: string, ext = 'csv'): string {
  const d = new Date()
  const p = (n: number) => String(n).padStart(2, '0')
  const stamp = `${d.getFullYear()}${p(d.getMonth() + 1)}${p(d.getDate())}-${p(d.getHours())}${p(d.getMinutes())}${p(d.getSeconds())}`
  return `${prefix}-${stamp}.${ext}`
}
