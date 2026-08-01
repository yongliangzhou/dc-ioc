// 校验 router 懒加载组件文件是否全部存在
import { readFileSync, existsSync } from "node:fs";
import { join } from "node:path";

const SRC = join(process.cwd(), "src");
const router = readFileSync(join(SRC, "router/index.ts"), "utf8");
const re = /import\(\s*["']@\/(.+?)["']\s*\)/g;
const missing = [];
let m;
while ((m = re.exec(router))) {
  const p = join(SRC, m[1]);
  if (!existsSync(p) && !existsSync(p + ".vue") && !existsSync(p + ".ts")) missing.push(m[1]);
}
console.log("lazy imports missing:", missing.length ? missing.join(", ") : "NONE");
