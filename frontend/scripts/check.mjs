import { readFileSync, readdirSync, statSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const VIEWS = join(__dirname, "..", "src", "views");

function walk(dir, out) {
  for (const e of readdirSync(dir)) {
    const p = join(dir, e);
    const st = statSync(p);
    if (st.isDirectory()) walk(p, out);
    else if (e.endsWith(".vue")) out.push(p);
  }
  return out;
}

let problems = 0;
for (const f of walk(VIEWS, [])) {
  const c = readFileSync(f, "utf8");
  const rel = f.replace(join(__dirname, ".."), "");
  const issues = [];
  if (!c.includes("</script>")) issues.push("MISSING </script> (truncated?)");
  if (!c.includes("</template>") && c.includes("<template>")) issues.push("MISSING </template>");
  // corruption signature
  if (c.includes("=> ( ts:") || /=> \( [^({]/.test(c)) issues.push("possible => ( corruption");
  // template brace balance
  const tpl = c.match(/<template>([\s\S]*?)<\/template>/);
  if (tpl) {
    const s = tpl[1];
    let bal = 0;
    for (const ch of s) {
      if (ch === "{") bal++;
      else if (ch === "}") bal--;
      if (bal < 0) { issues.push("template brace imbalance (extra })"); break; }
    }
    if (bal !== 0) issues.push(`template brace balance = ${bal}`);
  }
  if (issues.length) {
    problems++;
    console.log(rel, "->", issues.join("; "));
  }
}
console.log(problems === 0 ? "ALL OK" : `\n${problems} file(s) with issues`);
