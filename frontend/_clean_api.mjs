import fs from "node:fs";
import path from "node:path";

const srcDir = path.resolve("src");
const apiFile = path.join(srcDir, "api", "index.ts");
let apiSrc = fs.readFileSync(apiFile, "utf8");

// ---- compute dead set (functions + types) ----
const exported = [];
const reConst = /^export (?:const|function)\s+([A-Za-z_$][\w$]*)/gm;
const reType = /^export (?:interface|type)\s+([A-Za-z_$][\w$]*)/gm;
let m;
while ((m = reConst.exec(apiSrc))) exported.push({ name: m[1], kind: "fn" });
while ((m = reType.exec(apiSrc))) exported.push({ name: m[1], kind: "type" });

const exts = [".ts", ".vue", ".js", ".mjs"];
const files = [];
(function walk(d){ for(const e of fs.readdirSync(d,{withFileTypes:true})){ const p=path.join(d,e.name); if(e.isDirectory()) walk(p); else if(exts.includes(path.extname(e.name))) files.push(p);} })(srcDir);
const others = files.filter(f=>f!==apiFile);
const used = new Set();
for (const { name } of exported) {
  const rx = new RegExp("(?<![\\w$.])"+name+"(?![\\w$])","g");
  for (const f of others){ if(rx.test(fs.readFileSync(f,"utf8"))){ used.add(name); rx.lastIndex=0; break; } }
}
const dead = exported.filter(e=>!used.has(e.name));
const deadNames = new Set(dead.map(d=>d.name));
console.log("dead count:", dead.length, "->", [...deadNames].sort().join(", "));

// ---- remove dead export blocks ----
const lines = apiSrc.split("\n");
const starts = [];
for (let i=0;i<lines.length;i++){ if (lines[i].trim().startsWith("export ")) starts.push(i); }
// blocks: [0..starts[0]-1] preamble, then [starts[k]..starts[k+1]-1]
const blocks = [];
let prev = 0;
for (const s of starts){ blocks.push({start:prev, end:s-1, exportLine:s}); prev = s; }
blocks.push({start:prev, end:lines.length-1, exportLine:null}); // last block

function nameOf(block){
  if (block.exportLine===null) return null;
  const ln = lines[block.exportLine];
  const mm = ln.match(/export\s+(?:const|function|interface|type)\s+([A-Za-z_$][\w$]*)/);
  return mm ? mm[1] : null;
}

const kept = [];
let removed = 0;
for (const b of blocks){
  const nm = nameOf(b);
  if (nm && deadNames.has(nm)){ removed++; continue; } // drop this block
  // keep: collect lines start..end (inclusive), trimming trailing blank lines later
  const seg = lines.slice(b.start, b.end+1);
  kept.push(seg);
}
// join kept blocks; drop fully-empty leading/trailing and collapse multiple blank lines between
let out = [];
for (const seg of kept){
  // trim trailing blank lines in segment
  let end = seg.length;
  while (end>0 && seg[end-1].trim()==="") end--;
  if (end===0) continue; // empty segment (e.g., preamble became empty) - but keep preamble if non-empty
  out.push(...seg.slice(0,end));
  out.push(""); // blank line separator
}
while (out.length && out[out.length-1].trim()==="") out.pop();
// ensure preamble (block0) preserved: if out starts with blank, it's fine

const newSrc = out.join("\n") + "\n";
fs.writeFileSync(apiFile, newSrc, "utf8");
console.log("removed blocks:", removed, "kept lines:", out.length);
console.log("remaining exported:", (newSrc.match(/^export /gm)||[]).length);
