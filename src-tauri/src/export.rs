use std::fs;
use std::io::Write;
use std::path::{PathBuf};
use anyhow::Result;

use crate::db::{pending_grouped_by_product};

fn ensure_dir(path: &PathBuf) -> PathBuf {
    if !path.exists() {
        let _ = fs::create_dir_all(path);
    }
    path.clone()
}

fn today_filename(prefix: &str) -> String {
    let now = chrono::Local::now();
    format!("{}_{}.txt", prefix, now.format("%d.%m.%y"))
}

/// Экспорт TXT для МКЛ: группы по product. Кодировка UTF-8.
pub fn export_mkl_txt(export_dir: PathBuf) -> Result<PathBuf> {
    let dir = ensure_dir(&export_dir);
    let filename = today_filename("MKL");
    let filepath = dir.join(filename);

    let mut file = fs::File::create(&filepath)?;
    let groups = pending_grouped_by_product()?;

    for (product, items) in groups {
        // Заголовок — название товара
        writeln!(file, "{}", product)?;
        for it in items {
            // Строка из непустых частей: Sph, Cyl, Ax, BC, Количество
            let mut parts: Vec<String> = Vec::new();
            if let Some(sph) = it.sph.as_ref().filter(|s| !s.trim().is_empty()) {
                parts.push(format!("Sph: {}", sph));
            }
            if let Some(cyl) = it.cyl.as_ref().filter(|s| !s.trim().is_empty()) {
                parts.push(format!("Cyl: {}", cyl));
            }
            if let Some(ax) = it.ax {
                parts.push(format!("Ax: {}", ax));
            }
            if let Some(bc) = it.bc {
                parts.push(format!("BC: {}", bc));
            }
            parts.push(format!("Количество: {}", it.qty));
            writeln!(file, "{}", parts.join(" "))?;
        }
        writeln!(file)?; // пустая строка после группы
    }

    Ok(filepath)
}

/// Открыть файл в системном приложении (Windows: start)
pub fn open_file_crossplatform(path: &PathBuf) -> Result<()> {
    #[cfg(target_os = "windows")]
    {
        // cmd /C start "" "<path>"
        let p = path.to_string_lossy().to_string();
        std::process::Command::new("cmd")
            .args(["/C", "start", "", &p])
            .spawn()?;
    }
    #[cfg(target_os = "macos")]
    {
        std::process::Command::new("open")
            .arg(path)
            .spawn()?;
    }
    #[cfg(target_os = "linux")]
    {
        std::process::Command::new("xdg-open")
            .arg(path)
            .spawn()?;
    }
    Ok(())
}