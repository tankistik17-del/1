#!/usr/bin/env node
// Builds dist/game.html: an artifact *fragment* of index.html.
//  - every <script src="js/..."></script> becomes an inline <script> with that file's contents
//    (any "</script" inside is escaped as "<\/script");
//  - the doctype, <html>, <head>, <body> tags (and their closing tags) and the
//    <meta charset> / <meta name="viewport"> tags are removed (the host supplies its own skeleton);
//  - a class on <body>, if any, moves to a wrapper <div>.
// Result order: <title>, fonts <link>s, <style>, markup, scripts.
// Usage: node tools/build.mjs            (paths are resolved relative to this file's repo root)

import { readFileSync, writeFileSync, mkdirSync, existsSync } from 'node:fs';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const srcPath = join(root, 'index.html');
const outDir = join(root, 'dist');
const outPath = join(outDir, 'game.html');

function fail(msg) {
  console.error('build: ' + msg);
  process.exit(1);
}

let html = readFileSync(srcPath, 'utf8');

// 1) Strip the document skeleton from the template first (before any script is inlined,
//    so script contents can never be touched by these patterns).
let bodyClass = '';
html = html
  .replace(/^﻿/, '')
  .replace(/<!doctype[^>]*>\s*/i, '')
  .replace(/<meta\s+charset\s*=\s*["']?[^"'\s>]+["']?\s*\/?>\s*/gi, '')
  .replace(/<meta\s+name\s*=\s*["']viewport["'][^>]*>\s*/gi, '')
  .replace(/<\/?html(\s[^>]*)?>\s*/gi, '')
  .replace(/<\/?head(\s[^>]*)?>\s*/gi, '')
  .replace(/<body(\s[^>]*)?>\s*/i, (m, attrs = '') => {
    const cls = /\bclass\s*=\s*["']([^"']*)["']/i.exec(attrs);
    bodyClass = cls ? cls[1].trim() : '';
    return bodyClass ? `<div class="${bodyClass}">\n` : '';
  })
  .replace(/\s*<\/body\s*>/i, bodyClass ? '\n</div>' : '');

// 2) Inline local scripts.
const inlined = [];
html = html.replace(/<script\b([^>]*?)\bsrc\s*=\s*["'](js\/[^"']+)["']([^>]*)>\s*<\/script\s*>/gi, (m, pre, file) => {
  const path = join(root, file);
  if (!existsSync(path)) fail(`missing ${file} (referenced from index.html)`);
  let code = readFileSync(path, 'utf8').replace(/^﻿/, '');
  code = code.replace(/<\/(script)/gi, '<\\/$1');
  if (/<!--/.test(code)) console.warn(`build: warning: ${file} contains "<!--", which can confuse HTML script parsing`);
  inlined.push(file);
  return `<script>\n${code.replace(/\s+$/, '')}\n</script>`;
});

// 3) Sanity checks.
if (/<script\b[^>]*\bsrc\s*=/i.test(html)) fail('an external <script src> is left in the output');
if (/<!doctype|<\/?html[\s>]|<\/?head[\s>]|<\/?body[\s>]/i.test(html.replace(/<script>[\s\S]*?<\/script>/gi, ''))) {
  fail('document skeleton tags are left in the output');
}
html = html.replace(/^\s+/, '');
if (!/^<title>/i.test(html)) fail('the fragment must start with <title>');

mkdirSync(outDir, { recursive: true });
writeFileSync(outPath, html.replace(/\s*$/, '\n'));
const kb = (Buffer.byteLength(html) / 1024).toFixed(1);
console.log(`build: wrote ${outPath} (${kb} KB; inlined ${inlined.join(', ') || 'nothing'})`);
