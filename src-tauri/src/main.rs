#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use tauri::{CustomMenuItem, Manager, SystemTray, SystemTrayEvent, SystemTrayMenu, SystemTrayMenuItem};
use std::fs;
use std::path::PathBuf;
use serde::{Deserialize, Serialize};
use once_cell::sync::Lazy;
use log::{error, info};
use env_logger;

static APP_DIR: Lazy<PathBuf> = Lazy::new(|| {
    // Папка рядом с exe: текущая рабочая директория
    std::env::current_dir().unwrap_or_else(|_| PathBuf::from("."))
});

const SETTINGS_FILE: &str = "settings.json";
const DB_FILE: &str = "data.db";

#[derive(Debug, Serialize, Deserialize, Clone)]
struct Settings {
    version: u8,
    ui_scale: f32,
    ui_font_size: u8,
    export_path: String,
    tray_enabled: bool,
    minimize_to_tray: bool,
    start_in_tray: bool,
    autostart_enabled: bool,
    tray_logo_path: String,
    notify_enabled: bool,
    notify_days: Vec<u8>,
    notify_time: String,
    mkl_notify_enabled: bool,
    mkl_notify_after_days: u8,
    mkl_notify_time: String,
    notify_sound_enabled: bool,
    notify_sound_alias: String,
    notify_sound_mode: String,
    notify_sound_file: String,
    main_geometry: String,
}

impl Default for Settings {
    fn default() -> Self {
        Self {
            version: 1,
            ui_scale: 1.25,
            ui_font_size: 17,
            export_path: default_desktop_or_cwd(),
            tray_enabled: true,
            minimize_to_tray: true,
            start_in_tray: true,
            autostart_enabled: false,
            tray_logo_path: "app/assets/logo.png".to_string(),
            notify_enabled: false,
            notify_days: vec![],
            notify_time: "09:00".to_string(),
            mkl_notify_enabled: false,
            mkl_notify_after_days: 3,
            mkl_notify_time: "09:00".to_string(),
            notify_sound_enabled: true,
            notify_sound_alias: "SystemAsterisk".to_string(),
            notify_sound_mode: "alias".to_string(),
            notify_sound_file: "".to_string(),
            main_geometry: "".to_string(),
        }
    }
}

fn default_desktop_or_cwd() -> String {
    if let Some(home) = home::home_dir() {
        let desktop = home.join("Desktop");
        if desktop.exists() {
            return desktop.to_string_lossy().to_string();
        }
    }
    APP_DIR.to_string_lossy().to_string()
}

fn settings_path() -> PathBuf {
    APP_DIR.join(SETTINGS_FILE)
}

fn db_path() -> PathBuf {
    APP_DIR.join(DB_FILE)
}

fn read_settings() -> Settings {
    let path = settings_path();
    if path.exists() {
        match fs::read_to_string(&path) {
            Ok(content) => {
                let mut s: Settings = serde_json::from_str(&content).unwrap_or_default();
                // Дополнение недостающих полей дефолтами:
                let defaults = Settings::default();
                if s.version == 0 {
                    s.version = defaults.version;
                }
                if s.ui_scale == 0.0 {
                    s.ui_scale = defaults.ui_scale;
                }
                if s.ui_font_size == 0 {
                    s.ui_font_size = defaults.ui_font_size;
                }
                if s.export_path.trim().is_empty() {
                    s.export_path = defaults.export_path;
                }
                if s.tray_logo_path.trim().is_empty() {
                    s.tray_logo_path = defaults.tray_logo_path;
                }
                if s.notify_time.trim().is_empty() {
                    s.notify_time = defaults.notify_time;
                }
                if s.mkl_notify_time.trim().is_empty() {
                    s.mkl_notify_time = defaults.mkl_notify_time;
                }
                if s.notify_sound_alias.trim().is_empty() {
                    s.notify_sound_alias = defaults.notify_sound_alias;
                }
                if s.notify_sound_mode.trim().is_empty() {
                    s.notify_sound_mode = defaults.notify_sound_mode;
                }
                s
            }
            Err(e) => {
                error!("Ошибка чтения settings.json: {}", e);
                Settings::default()
            }
        }
    } else {
        let s = Settings::default();
        let _ = write_settings_atomically(&s);
        s
    }
}

fn write_settings_atomically(s: &Settings) -> anyhow::Result<()> {
    let path = settings_path();
    let tmp = path.with_extension("json.tmp");
    let json = serde_json::to_string_pretty(s)?;
    fs::write(&tmp, json)?;
    fs::rename(&tmp, &path)?;
    Ok(())
}

#[tauri::command]
fn maximize_on_start(window: tauri::Window) {
    // Максимизируем окно, если возможно
    let _ = window.maximize();
    let _ = window.set_focus();
    let _ = window.set_always_on_top(true);
    // вернуть нормальный режим через небольшую задержку — можно делать на UI-стороне
    let _ = window.set_always_on_top(false);
}

#[tauri::command]
fn get_settings() -> Settings {
    read_settings()
}

fn ensure_db_exists() {
    let db = db_path();
    if !db.exists() {
        // пока просто создадим пустой файл; схему добавим в следующем шаге
        if let Err(e) = fs::write(&db, b"") {
            error!("Не удалось создать data.db: {}", e);
        } else {
            info!("Создан файл БД: {}", db.display());
        }
    }
}

fn build_tray() -> SystemTray {
    let open = CustomMenuItem::new("open".to_string(), "Открыть");
    let autostart = CustomMenuItem::new("autostart_toggle".to_string(), "Автозапуск: Вкл/Выкл");
    let quit = CustomMenuItem::new("quit".to_string(), "Выход");
    let menu = SystemTrayMenu::new()
        .add_item(open)
        .add_item(autostart)
        .add_native_item(SystemTrayMenuItem::Separator)
        .add_item(quit);
    SystemTray::new().with_menu(menu)
}

fn main() {
    env_logger::init();

    let settings = read_settings();
    info!("Настройки загружены: {:?}", settings);
    ensure_db_exists();

    tauri::Builder::default()
        .system_tray(build_tray())
        .on_system_tray_event(|app, event| match event {
            SystemTrayEvent::MenuItemClick { id, .. } => match id.as_str() {
                "open" => {
                    if let Some(window) = app.get_window("main") {
                        let _ = window.show();
                        let _ = window.set_focus();
                    }
                }
                "autostart_toggle" => {
                    if let Some(window) = app.get_window("main") {
                        tauri::api::dialog::message(
                            Some(&window),
                            "Автозапуск",
                            "Переключение автозапуска будет реализовано на следующем шаге.",
                        );
                    } else {
                        tauri::api::dialog::message::<tauri::Wry>(
                            None,
                            "Автозапуск",
                            "Переключение автозапуска будет реализовано на следующем шаге.",
                        );
                    }
                }
                "quit" => {
                    // Сохранить геометрию окна при выходе — реализуем позже
                    std::process::exit(0);
                }
                _ => {}
            },
            SystemTrayEvent::LeftClick { .. } => {
                if let Some(window) = app.get_window("main") {
                    let _ = window.show();
                    let _ = window.set_focus();
                }
                // Если окно недоступно — просто пропустим действие без диалога.
            }
            _ => {}
        })
        .invoke_handler(tauri::generate_handler![maximize_on_start, get_settings])
        .run(tauri::generate_context!())
        .expect("error while running tauri application");
}