// Fix over-aggressive `t('` -> `tl('` substring replacement from repair-i18n.mjs.
// Real i18n calls are `tl('` preceded by a NON-word char (space, '(', ',').
// Corrupted ones are `IDENTtl('` where IDENT ends in a word char (e.g. $emit -> $emitl, lvText -> lvTextl).
// Restore corrupted ones: IDENTtl( -> IDENTt(
import { readFileSync, writeFileSync, readdirSync, statSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const SRC = join(__dirname, "..", "src");

function walk(dir, out) {
  for (const e of readdirSync(dir)) {
    const p = join(dir, e);
    const st = statSync(p);
    if (st.isDirectory()) walk(p, out);
    else if (/\.(vue|ts|tsx|js|jsx)$/.test(e)) out.push(p);
  }
  return out;
}

let changed = 0;
let totalHits = 0;
for (const f of walk(SRC, [])) {
  let content = readFileSync(f, "utf8");
  const re = /([A-Za-z0-9_])tl\(/g;
  const matches = content.match(re);
  if (!matches) continue;
  const n = matches.length;
  content = content.replace(re, (_m, pre) => `${pre}t(`);
  writeFileSync(f, content, "utf8");
  changed++;
  totalHits += n;
  console.log("fixed:", f.replace(SRC, ""), "->", n, "corruptions");
}
console.log(`\nfixed ${changed} files, ${totalHits} corruptions total`);
