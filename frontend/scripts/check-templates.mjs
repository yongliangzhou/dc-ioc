/**
 * 提交前模板语法检查
 * 目的：在本地 pre-commit 阶段捕获会导致 `vite build` 失败的 Vue 模板语法错误
 *       （如多行事件绑定 @click="\n ... \n"、缺失闭合标签等），
 *       避免这类问题只能等到 CI 的 vite build 才暴露。
 * 仅做模板编译（快，通常 < 5s），不做完整构建。
 */
import { readdirSync, readFileSync, statSync } from 'node:fs'
import { join, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'
import { parse } from '@vue/compiler-sfc'

const __dirname = dirname(fileURLToPath(import.meta.url))
const root = join(__dirname, '..', 'src')

function walk(dir) {
  const out = []
  for (const name of readdirSync(dir)) {
    const p = join(dir, name)
    const st = statSync(p)
    if (st.isDirectory()) out.push(...walk(p))
    else if (name.endsWith('.vue')) out.push(p)
  }
  return out
}

let failed = 0
for (const file of walk(root)) {
  const source = readFileSync(file, 'utf8')
  const { errors } = parse(source, { filename: file })
  if (errors && errors.length) {
    failed++
    console.error(`\n✗ 模板语法错误: ${file}`)
    for (const e of errors) {
      const loc = e.loc && e.loc.start ? `(${e.loc.start.line}:${e.loc.start.column})` : ''
      console.error(`  ${loc} ${e.message}`)
    }
  }
}

if (failed > 0) {
  console.error(`\n提交被阻止：发现 ${failed} 个文件存在 Vue 模板语法错误。`)
  console.error('请修复后再提交（多为事件绑定拆成多行或标签未闭合）。')
  process.exit(1)
}

console.log('✓ Vue 模板语法检查通过')
