// Prints a page's Slovenian dictionary as JSON (the `SL` object, or `T.sl` on the welcome page).
// Usage: node tools/extract_dict.js contractor/index.html
const fs = require('fs');
const s = fs.readFileSync(process.argv[2], 'utf8');
const scripts = (s.match(/<script>([\s\S]*?)<\/script>/g) || []).map((x) => x.replace(/<\/?script>/g, '')).join('\n');
function grab(name) {
  const i = scripts.search(new RegExp('(const|let|var)\\s+' + name + '\\s*=\\s*\\{'));
  if (i < 0) return null;
  let j = scripts.indexOf('{', i), d = 0, k = j, q = null;
  for (; k < scripts.length; k++) {
    const c = scripts[k];
    if (q) { if (c === '\\') { k++; continue; } if (c === q) q = null; continue; }
    if (c === '"' || c === "'" || c === '`') { q = c; continue; }
    if (c === '{') d++; else if (c === '}') { d--; if (!d) break; }
  }
  return scripts.slice(j, k + 1);
}
const src = grab('SL');
const obj = src ? Function('return ' + src)() : Function('return ' + grab('T'))().sl;
process.stdout.write(JSON.stringify(obj));
