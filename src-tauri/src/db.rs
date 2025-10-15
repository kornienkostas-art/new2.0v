use std::path::PathBuf;
use rusqlite::{Connection, params};

fn app_dir() -> PathBuf {
    std::env::current_dir().unwrap_or_else(|_| PathBuf::from("."))
}

fn db_file() -> PathBuf {
    app_dir().join("data.db")
}

pub fn init_db() -> anyhow::Result<()> {
    let conn = Connection::open(db_file())?;

    // Таблица МКЛ (минимально необходимая для первого экрана)
    conn.execute_batch(
        r#"
        CREATE TABLE IF NOT EXISTS mkl_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fio TEXT NOT NULL,
            phone TEXT NOT NULL,            -- хранится только цифрами
            product TEXT NOT NULL,
            sph TEXT,                       -- храним как строку для гибкости шага/знака
            cyl TEXT,
            ax INTEGER,
            bc REAL,
            qty INTEGER NOT NULL,
            status TEXT NOT NULL,           -- 'Не заказан' | 'Заказан' | 'Прозвонен' | 'Вручен'
            date TEXT NOT NULL,             -- YYYY-MM-DD HH:MM
            comment TEXT DEFAULT ''
        );
        "#,
    )?;

    // Вставим демо-данные, если таблица пуста
    let count: i64 = conn.query_row("SELECT COUNT(*) FROM mkl_orders", [], |row| row.get(0))?;
    if count == 0 {
        let now = chrono::Local::now().format("%Y-%m-%d %H:%M").to_string();
        conn.execute(
            "INSERT INTO mkl_orders (fio, phone, product, sph, cyl, ax, bc, qty, status, date, comment)
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11)",
            params![
                "Иванов Иван Иванович",
                "89123456789",
                "Air Optix Aqua",
                "-1.25",
                "-0.75",
                80i64,
                8.6f64,
                2i64,
                "Не заказан",
                now,
                ""
            ],
        )?;
        conn.execute(
            "INSERT INTO mkl_orders (fio, phone, product, sph, cyl, ax, bc, qty, status, date, comment)
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8, ?9, ?10, ?11)",
            params![
                "Петров Петр Петрович",
                "71234567890",
                "Air Optix Aqua",
                "-1.25",
                "",
                rusqlite::types::Null, // ax пусто
                8.6f64,
                1i64,
                "Заказан",
                now,
                "Позвонить завтра"
            ],
        )?;
    }

    Ok(())
}

#[derive(serde::Serialize)]
pub struct MklOrder {
    pub id: i64,
    pub fio: String,
    pub phone: String,
    pub product: String,
    pub sph: Option<String>,
    pub cyl: Option<String>,
    pub ax: Option<i64>,
    pub bc: Option<f64>,
    pub qty: i64,
    pub status: String,
    pub date: String,
    pub comment: String,
}

pub fn list_mkl_orders(limit: i64) -> anyhow::Result<Vec<MklOrder>> {
    let conn = Connection::open(db_file())?;
    let mut stmt = conn.prepare(
        "SELECT id, fio, phone, product, sph, cyl, ax, bc, qty, status, date, comment
         FROM mkl_orders
         ORDER BY id DESC
         LIMIT ?1",
    )?;
    let rows = stmt.query_map(params![limit], |row| {
        Ok(MklOrder {
            id: row.get(0)?,
            fio: row.get(1)?,
            phone: row.get(2)?,
            product: row.get(3)?,
            sph: row.get::<_, Option<String>>(4)?,
            cyl: row.get::<_, Option<String>>(5)?,
            ax: row.get::<_, Option<i64>>(6)?,
            bc: row.get::<_, Option<f64>>(7)?,
            qty: row.get(8)?,
            status: row.get(9)?,
            date: row.get(10)?,
            comment: row.get(11)?,
        })
    })?;

    let mut out = Vec::new();
    for r in rows {
        out.push(r?);
    }
    Ok(out)
}