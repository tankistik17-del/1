// Builds a self-contained file that works offline without Claude: template + parser + SheetJS inlined.
// Usage: node build-standalone.cjs <path to xlsx.full.min.js> <output.html>
const fs = require('fs');
const [lib, out] = process.argv.slice(2);
const tpl = fs.readFileSync(__dirname + '/app.tpl.html', 'utf8');
const parser = fs.readFileSync(__dirname + '/parser.js', 'utf8');
const sheetjs = fs.readFileSync(lib, 'utf8');
for (const [name, src] of [['parser', parser], ['SheetJS', sheetjs]]) if (/<\/script|<script/i.test(src)) throw new Error(name + ' contains a script tag');
const CDN = '<script src="https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js"></script>';
if (!tpl.includes(CDN)) throw new Error('SheetJS script tag not found in template');
const page = tpl.replace(CDN, () => '<script>\n/* SheetJS Community Edition 0.18.5, Apache-2.0, https://sheetjs.com */\n' + sheetjs + '\n</script>').replace('/*__PARSER__*/', () => parser);
const cut = page.indexOf('<div class="wrap">');
const head = page.slice(0, cut).trim(), body = page.slice(cut);
fs.writeFileSync(out, `<!doctype html>\n<html lang="ru">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width,initial-scale=1">\n${head}\n</head>\n<body>\n${body}</body>\n</html>\n`);
console.log('built', out, fs.statSync(out).size);
