# УссурОчки.рф — Desktop (Windows) на Tauri (Rust + React + Fluent)

Это репозиторий приложения по вашему ТЗ на стеке Tauri (Rust backend) + React + Fluent UI. Ниже — инструкции по запуску в режиме разработки и сборке установщика.

## Требования окружения (Windows)

1) Rust:
- Установите rustup: https://rustup.rs
- Во время установки выберите MSVC (Visual Studio) toolchain.
- Проверьте: `rustup default stable` и `rustup target add x86_64-pc-windows-msvc`

2) Инструменты сборки:
- Установите Microsoft Visual C++ Build Tools (MSVC) и Windows 10/11 SDK:
  https://visualstudio.microsoft.com/ru/visual-cpp-build-tools/

3) Node.js (LTS):
- https://nodejs.org/en — будет нужен для фронтенда и CLI Tauri

4) WebView2 Runtime:
- Обычно уже установлен на Windows 10/11.
- Если нет: https://developer.microsoft.com/en-us/microsoft-edge/webview2/

## Запуск проекта (dev)

```bash
# в корне проекта
npm install
npm run tauri dev
```

Откроется окно приложения. Изменения в UI (React) подхватываются автоматически.

## Сборка (release)

```bash
npm run tauri build
```

Готовые файлы появятся в:
```
src-tauri/target/release/bundle/
```
Там будут exe/msi/msix (в зависимости от конфигурации Tauri).

## Стек

- Backend: Rust + Tauri (system tray, файловая система, доступ к реестру, запуск файлов).
- UI: React + Fluent UI (современный дизайн), Vite для сборки.
- БД: SQLite (rusqlite с feature "bundled"), файл `data.db` рядом с приложением.
- Настройки: `settings.json` (атомарная запись), создаётся автоматически.
- Трей: SystemTray (включен), placeholder-иконка при отсутствии ассетов.

## Что реализовано в этом шаге

- Каркас проекта Tauri + React + Fluent.
- Главное окно с переходами (пока заглушки).
- Системный трей с пунктами: «Открыть», «Автозапуск: Вкл/Выкл» (заглушка), «Выход».
- Автосоздание settings.json с дефолтами.
- Заготовки для БД (rusqlite подключён, создание файла БД — последующий шаг).

Дальше я добавлю:
- Экраны «Заказы МКЛ», «Заказы Меридиан», «Клиенты», «Товары», «Настройки».
- CRUD в Rust (SQLite) + вызовы из UI.
- Экспорт TXT, уведомления, звук (Windows API), автозапуск (реестр HKCU\Run).

Если что-то не запускается — напишите, помогу с установкой зависимостей.