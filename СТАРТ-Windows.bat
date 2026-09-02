@echo off
chcp 65001 >nul
cd /d "%~dp0"
where node >/dev/null 2>nul
if errorlevel 1 (
  echo Сначала установите Node.js с сайта https://nodejs.org — зелёная кнопка LTS.
  echo После установки запустите этот файл ещё раз.
  pause
  exit /b 1
)
if not exist node_modules (
  echo Первый запуск: устанавливаю зависимости, это займёт 1-2 минуты...
  call npm install
)
start "" http://localhost:3000
echo Сервер запущен. Не закрывайте это окно, пока пользуетесь дашбордом.
node server\index.js
pause
