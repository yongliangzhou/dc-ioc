/**
 * 前端合成示例数据的工具（仅用于"后端暂无时序接口"的过渡期）
 *
 * 规则：任何由本文件生成的数据都必须在 UI 上挂 <DataBadge tone="sample" />，
 * 让值班人员一眼知道这不是真实遥测。
 */

/** Lehmer 伪随机数生成器：同一 seed 永远产出同一序列 */
export function seeded(seed: number): () => number {
  let s = Math.floor(Math.abs(seed) * 1000) % 2147483647
  if (s <= 0) s += 2147483646
  return () => (s = (s * 16807) % 2147483647) / 2147483647
}

/**
 * 生成围绕 base 上下波动的示例序列。
 * 用固定种子而非 Math.random()，避免组件每次重渲染曲线都跳变。
 */
export function sampleSeries(base: number, range: number, len: number, seed: number): number[] {
  const rnd = seeded(seed)
  return Array.from({ length: len }, () => +(base + (rnd() - 0.5) * range).toFixed(2))
}
