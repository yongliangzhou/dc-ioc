/**
 * 修复 i18n 包裹脚本造成的字符串字面量损坏:
 *   label: "tl('变压器平均负载')"  ->  label: tl('变压器平均负载')
 * 仅匹配 JS 对象/数组上下文 ([:,({[] 后跟引号), 不会误伤模板绑定 :label="tl('…')" (前面是 =)。
 */
import { readFileSync, writeFileSync, readdirSync, statSync } from "node:fs";
import { join } from "node:path";

const SRC = join(process.cwd(), "src");
function* walk(dir) {
  for (const name of readdirSync(dir)) {
    const p = join(dir, name);
    if (statSync(p).isDirectory()) yield* walk(p);
    else if (/\.(vue|ts)$/.test(name)) yield p;
  }
}

const re = /([:,({[]\s*)"tl\('((?:[^'\\]|\\.)*)'\)"/g;
let files = 0, hits = 0;
for (const f of walk(SRC)) {
  const content = readFileSync(f, "utf8");
  const m = content.match(re);
  if (!m) continue;
  writeFileSync(f, content.replace(re, (_a, pre, key) => `${pre}tl('${key}')`), "utf8");
  files++; hits += m.length;
  console.log("fixed:", f.replace(SRC, ""), "->", m.length);
}
console.log(`\nDone: ${files} files, ${hits} corruptions`);
