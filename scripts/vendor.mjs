// Копирует браузерные библиотеки из node_modules в public/vendor (выполняется при npm install)
import { copyFileSync, mkdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = join(dirname(fileURLToPath(import.meta.url)), '..');
mkdirSync(join(root, 'public', 'vendor'), { recursive: true });
copyFileSync(join(root, 'node_modules', 'vue', 'dist', 'vue.global.prod.js'), join(root, 'public', 'vendor', 'vue.global.prod.js'));
copyFileSync(join(root, 'node_modules', 'xlsx', 'dist', 'xlsx.full.min.js'), join(root, 'public', 'vendor', 'xlsx.full.min.js'));
console.log('[vendor] vue + xlsx скопированы в public/vendor');
