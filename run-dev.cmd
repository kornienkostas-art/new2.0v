@echo off
setlocal

REM Скрипт запуска dev-режима Tauri (Windows), без проблем с PowerShell policy.
REM 1) Устанавливает зависимости
REM 2) Запускает локальный tauri CLI

REM Перейти в папку скрипта (корень проекта)
pushd %~dp0

echo === Установка зависимостей (npm install) ===
call npm.cmd install
if errorlevel 1 (
  echo [Ошибка] npm install завершился с ошибкой.
  pause
  exit /b 1
)

echo === Запуск Tauri dev ===
call .\node_modules\.bin\tauri.cmd dev
if errorlevel 1 (
  echo [Ошибка] Запуск Tauri dev завершился с ошибкой.
  pause
  exit /b 1
)

popd
endlocal