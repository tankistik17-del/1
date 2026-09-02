#!/bin/bash
# Запуск «Пульта удержания» на macOS: двойной клик по этому файлу.
# При первом запуске macOS может блокировать: правый клик → «Открыть».
cd "$(dirname "$0")"
if ! command -v node >/dev/null 2>&1; then
  echo "Сначала установите Node.js с сайта https://nodejs.org — зелёная кнопка LTS."
  echo "После установки запустите этот файл ещё раз."
  read -r -p "Нажмите Enter, чтобы закрыть..."
  exit 1
fi
if [ ! -d node_modules ]; then
  echo "Первый запуск: устанавливаю зависимости, это займёт 1-2 минуты..."
  npm install
fi
(sleep 2 && open http://localhost:3000) &
echo "Сервер запущен. Не закрывайте это окно, пока пользуетесь дашбордом."
node server/index.js
