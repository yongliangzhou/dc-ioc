// Repair codemod output (idempotent):
//  - strip any existing i18n lines, re-add `import { useI18n }` + `const { t: tl } = useI18n()` at top
//  - rename i18n calls t('...') -> tl('...') to avoid collisions with local `t` vars
// Skips the 8 hand-i18n'd views that already use `t` correctly.
import { readFileSync, writeFileSync, readdirSync, statSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = dirname(fileURLToPath(import.meta.url));
const VIEWS = join(__dirname, "..", "src", "views");
const DONE = new Set([
  join(VIEWS, "security", "Cctv.vue"),
  join(VIEWS, "security", "Acs.vue"),
  join(VIEWS, "security", "Ids.vue"),
  join(VIEWS, "security", "Fire.vue"),
  join(VIEWS, "network", "Switches.vue"),
  join(VIEWS, "network", "Ping.vue"),
  join(VIEWS, "network", "Bandwidth.vue"),
  join(VIEWS, "overview", "Index.vue"),
]);

function walk(dir, out) {
  for (const e of readdirSync(dir)) {
    const p = join(dir, e);
    const st = statSync(p);
    if (st.isDirectory()) walk(p, out);
    else if (e.endsWith(".vue")) out.push(p);
  }
  return out;
}

let changed = 0;
for (const f of walk(VIEWS, [])) {
  if (DONE.has(f)) continue;
  let content = readFileSync(f, "utf8");
  if (!content.includes("tl('")) continue;

  const sm = content.match(/<script[^>]*>([\s\S]*?)<\/script>/);
  if (!sm) continue;
  let s = sm[1];
  // strip existing i18n lines (any prior run)
  s = s.replace(/^\s*import\s+\{\s*useI18n\s*\}\s+from\s+["']vue-i18n["'];?\s*\n/gm, "");
  s = s.replace(/^\s*const\s*\{\s*t(?::\s*tl)?\s*\}\s*=\s*useI18n\(\);?\s*\n/gm, "");
  // re-add at top
  s = `import { useI18n } from "vue-i18n";\nconst { t: tl } = useI18n();\n` + s;
  // rename i18n calls in script
  s = s.replace(/t\('/g, "tl('");

  content = content.replace(sm[0], sm[0].replace(sm[1], s));
  // rename in template
  content = content.replace(/t\('/g, "tl('");

  writeFileSync(f, content, "utf8");
  changed++;
  console.log("repaired:", f.replace(join(__dirname, ".."), ""));
}
console.log(`\nrepaired ${changed} files`);
