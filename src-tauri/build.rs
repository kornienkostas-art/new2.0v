use std::fs::{self, File};
use std::io::Write;
use std::path::PathBuf;

fn ensure_icon() {
  let manifest_dir = PathBuf::from(std::env::var("CARGO_MANIFEST_DIR").unwrap_or_else(|_| ".".into()));
  let icons_dir = manifest_dir.join("icons");
  let ico_path = icons_dir.join("icon.ico");

  if !icons_dir.exists() {
    let _ = fs::create_dir_all(&icons_dir);
  }

  if !ico_path.exists() {
    // Сгенерируем простую ICO-иконку 64x64 (сплошной цвет), чтобы tauri-build не падал.
    let size: u32 = 64;
    let mut rgba = vec![0u8; (size * size * 4) as usize];
    // Пастельный зелёный фон
    for px in rgba.chunks_exact_mut(4) {
      px[0] = 220; // R
      px[1] = 252; // G
      px[2] = 231; // B
      px[3] = 255; // A
    }

    // Используем корректный конструктор из ico crate
    let image = ico::IconImage::from_rgba_data(size, size, rgba);
    let entry = ico::IconDirEntry::encode(&image).expect("encode icon");
    let mut dir = ico::IconDir::new(ico::ResourceType::Icon);
    dir.add_entry(entry);

    let file = File::create(&ico_path).expect("create icon.ico");
    dir.write(file).expect("write icon.ico");
  }

  // Также создадим простой PNG-плейсхолдер, если нужен (не обязателен для сборки).
  let png_path = icons_dir.join("icon.png");
  if !png_path.exists() {
    // Без зависимости image создадим текстовый плейсхолдер.
    let mut f = File::create(&png_path).expect("create icon.png");
    let _ = f.write_all(b"Placeholder icon.png (not a real PNG). Provide a proper icons/icon.png for production.");
  }
}

fn main() {
  ensure_icon();
  tauri_build::build()
}