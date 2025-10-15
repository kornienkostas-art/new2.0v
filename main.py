import os
import sys
import json
import sqlite3
import uuid
import platform
import traceback
from datetime import datetime, timedelta
from dataclasses import dataclass
from typing import Optional, List, Tuple, Dict

# Qt
from PySide6.QtCore import Qt, QTimer, QSize, QEvent
from PySide6.QtGui import QAction, QCloseEvent, QIcon, QPalette, QColor, QFont
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QTableWidget, QTableWidgetItem, QHeaderView,
    QLineEdit, QComboBox, QSpinBox, QDialog, QFormLayout, QDialogButtonBox,
    QSystemTrayIcon, QMenu, QFileDialog, QMessageBox, QStyledItemDelegate,
    QAbstractItemView, QSpacerItem, QSizePolicy, QCheckBox
)

# Windows sound
IS_WINDOWS = platform.system() == "Windows"
if IS_WINDOWS:
    try:
        import winsound
    except Exception:
        winsound = None


APP_TITLE = "УссурОЧки.рф — Заказ линз"
DB_FILE = "data.db"
SETTINGS_FILE = "settings.json"

STATUSES_MKL = ["Не заказан", "Заказан", "Прозвонен", "Вручен"]
STATUSES_MERIDIAN = ["Не заказан", "Заказан"]


def user_desktop_path() -> str:
    if IS_WINDOWS:
        from pathlib import Path
        return str(Path.home() / "Desktop")
    if platform.system() == "Darwin":
        from pathlib import Path
        return str(Path.home() / "Desktop")
    # Linux/other
    return os.getcwd()


DEFAULT_SETTINGS = {
    "version": 1,
    "ui_scale": 1.25,
    "ui_font_size": 17,
    "export_path": user_desktop_path(),
    "tray_enabled": True,
    "minimize_to_tray": True,
    "start_in_tray": True,
    "autostart_enabled": False,
    "tray_logo_path": "app/assets/logo.png",
    "notify_enabled": False,
    "notify_days": [],
    "notify_time": "09:00",
    "mkl_notify_enabled": False,
    "mkl_notify_after_days": 3,
    "mkl_notify_time": "09:00",
    "notify_sound_enabled": True,
    "notify_sound_alias": "SystemAsterisk",
    "notify_sound_mode": "alias",
    "notify_sound_file": "",
    "main_geometry": ""
}


def atomic_write_json(path: str, data: dict) -> None:
    tmp_path = path + ".tmp"
    with open(tmp_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, path)


def load_settings() -> dict:
    # Create file if missing
    if not os.path.exists(SETTINGS_FILE):
        atomic_write_json(SETTINGS_FILE, DEFAULT_SETTINGS)
        return DEFAULT_SETTINGS.copy()
    # Read and fill defaults
    try:
        with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        # If corrupted, rename and recreate
        backup = SETTINGS_FILE + ".bak_" + datetime.now().strftime("%Y%m%d_%H%M%S")
        try:
            os.replace(SETTINGS_FILE, backup)
        except Exception:
            pass
        atomic_write_json(SETTINGS_FILE, DEFAULT_SETTINGS)
        return DEFAULT_SETTINGS.copy()
    for k, v in DEFAULT_SETTINGS.items():
        if k not in data:
            data[k] = v
    return data


def save_settings(data: dict) -> None:
    # Atomic save
    atomic_write_json(SETTINGS_FILE, data)


# DB Layer
def ensure_db() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_FILE)
    conn.execute("PRAGMA foreign_keys = ON;")
    cur = conn.cursor()

    # Clients
    cur.execute("""
        CREATE TABLE IF NOT EXISTS clients (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fio TEXT NOT NULL,
            phone TEXT NOT NULL
        );
    """)

    # Products (MKL and Meridian)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS products_mkl (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS products_meridian (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL
        );
    """)

    # MKL orders (flat)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS mkl_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fio TEXT NOT NULL,
            phone TEXT NOT NULL,
            product TEXT NOT NULL,
            sph TEXT NOT NULL,
            cyl TEXT,
            ax INTEGER,
            bc REAL,
            qty INTEGER NOT NULL,
            status TEXT NOT NULL,
            date TEXT NOT NULL,
            comment TEXT DEFAULT ''
        );
    """)

    # Meridian: orders header + items
    cur.execute("""
        CREATE TABLE IF NOT EXISTS meridian_orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            status TEXT NOT NULL,
            date TEXT NOT NULL
        );
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS meridian_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product TEXT NOT NULL,
            sph TEXT,
            cyl TEXT,
            ax INTEGER,
            d INTEGER,
            qty INTEGER NOT NULL,
            FOREIGN KEY(order_id) REFERENCES meridian_orders(id) ON DELETE CASCADE
        );
    """)

    # Snooze fields for notifications
    cur.execute("""
        CREATE TABLE IF NOT EXISTS notify_state (
            key TEXT PRIMARY KEY,
            value TEXT
        );
    """)

    conn.commit()
    return conn


# Utilities
def only_digits(s: str) -> str:
    return "".join(ch for ch in s if ch.isdigit())


def format_phone_display(raw: str) -> str:
    digits = only_digits(raw)
    if len(digits) >= 11:
        if digits[0] == "7":
            d = digits[1:11]
            return f"+7-{d[0:3]}-{d[3:6]}-{d[6:8]}-{d[8:10]}"
        elif digits[0] == "8":
            d = digits[1:11]
            return f"8-{d[0:3]}-{d[3:6]}-{d[6:8]}-{d[8:10]}"
        else:
            d = digits[-10:]
            return f"8-{d[0:3]}-{d[3:6]}-{d[6:8]}-{d[8:10]}"
    elif len(digits) == 10:
        d = digits
        return f"8-{d[0:3]}-{d[3:6]}-{d[6:8]}-{d[8:10]}"
    else:
        return raw.strip()


def normalize_step(value: Optional[float], step: float, min_v: float, max_v: float) -> Optional[float]:
    if value is None:
        return None
    # clamp
    v = max(min_v, min(max_v, value))
    # snap to step
    snapped = round(v / step) * step
    # round to reasonable decimals
    decimals = len(str(step).split(".")[1]) if "." in str(step) else 0
    return float(f"{snapped:.{decimals}f}")


def validate_int(value: Optional[int], min_v: int, max_v: int) -> Optional[int]:
    if value is None:
        return None
    return max(min_v, min(max_v, int(value)))


# Status colors
STATUS_STYLE = {
    "Не заказан": ("#fee2e2", "#7f1d1d"),
    "Заказан": ("#fef3c7", "#7c2d12"),
    "Прозвонен": ("#dbeafe", "#1e3a8a"),
    "Вручен": ("#dcfce7", "#065f46"),
}


class StatusDelegate(QStyledItemDelegate):
    def initStyleOption(self, option, index):
        super().initStyleOption(option, index)
        if index.column() == 8:  # status column for MKL
            status = index.data()
            bg, fg = STATUS_STYLE.get(status, (None, None))
            if bg:
                option.backgroundBrush = QColor(bg)
            if fg:
                option.palette.setColor(QPalette.Text, QColor(fg))


# Dialogs
class MKLOrderDialog(QDialog):
    def __init__(self, parent, data: Optional[dict] = None, products: List[str] = None):
        super().__init__(parent)
        self.setWindowTitle("Карточка заказа МКЛ")
        self.setModal(True)
        layout = QFormLayout(self)

        self.fio = QLineEdit()
        self.phone = QLineEdit()
        self.product = QComboBox()
        self.product.setEditable(True)
        products = products or []
        self.product.addItems(products)

        self.sph = QLineEdit()
        self.cyl = QLineEdit()
        self.ax = QLineEdit()
        self.bc = QLineEdit()
        self.qty = QSpinBox()
        self.qty.setRange(1, 20)

        self.comment = QLineEdit()

        layout.addRow("ФИО", self.fio)
        layout.addRow("Телефон", self.phone)
        layout.addRow("Товар", self.product)
        layout.addRow("Sph", self.sph)
        layout.addRow("Cyl", self.cyl)
        layout.addRow("Ax", self.ax)
        layout.addRow("BC", self.bc)
        layout.addRow("Количество", self.qty)
        layout.addRow("Комментарий", self.comment)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

        if data:
            self.fio.setText(data.get("fio", ""))
            self.phone.setText(data.get("phone", ""))
            # set current product
            p = data.get("product", "")
            if p and p not in products:
                self.product.insertItem(0, p)
            self.product.setCurrentText(p)
            self.sph.setText(data.get("sph", ""))
            self.cyl.setText(data.get("cyl", ""))
            self.ax.setText("" if data.get("ax") is None else str(data.get("ax")))
            self.bc.setText("" if data.get("bc") is None else str(data.get("bc")))
            self.qty.setValue(int(data.get("qty", 1)))
            self.comment.setText(data.get("comment", ""))

    def get_data(self) -> Optional[dict]:
        fio = self.fio.text().strip()
        phone_digits = only_digits(self.phone.text())
        product = self.product.currentText().strip()
        if not fio or not phone_digits or not product:
            QMessageBox.warning(self, "Ошибка", "ФИО, Телефон и Товар обязательны.")
            return None

        def parse_optional_float(s: str) -> Optional[float]:
            s = s.strip().replace(",", ".")
            if not s:
                return None
            try:
                return float(s)
            except Exception:
                return None

        def parse_optional_int(s: str) -> Optional[int]:
            s = s.strip()
            if not s:
                return None
            try:
                return int(s)
            except Exception:
                return None

        sph = parse_optional_float(self.sph.text())
        if sph is None:
            QMessageBox.warning(self, "Ошибка", "Поле Sph обязательно.")
            return None
        sph = normalize_step(sph, 0.25, -30.0, 30.0)

        cyl = parse_optional_float(self.cyl.text())
        if cyl is not None:
            cyl = normalize_step(cyl, 0.25, -10.0, 10.0)

        ax = parse_optional_int(self.ax.text())
        if ax is not None:
            ax = validate_int(ax, 0, 180)

        bc = parse_optional_float(self.bc.text())
        if bc is not None:
            bc = normalize_step(bc, 0.1, 8.0, 9.0)

        qty = self.qty.value()
        comment = self.comment.text().strip()

        return {
            "fio": fio,
            "phone": phone_digits,
            "product": product or "(Без названия)",
            "sph": f"{sph:.2f}",
            "cyl": "" if cyl is None else f"{cyl:.2f}",
            "ax": None if ax is None else int(ax),
            "bc": None if bc is None else float(f"{bc:.1f}"),
            "qty": int(qty),
            "comment": comment
        }


class StatusDialog(QDialog):
    def __init__(self, parent, statuses: List[str], current: Optional[str] = None):
        super().__init__(parent)
        self.setWindowTitle("Сменить статус")
        self.setModal(True)
        layout = QVBoxLayout(self)
        self.combo = QComboBox()
        self.combo.addItems(statuses)
        if current:
            idx = self.combo.findText(current)
            if idx >= 0:
                self.combo.setCurrentIndex(idx)
        layout.addWidget(self.combo)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def selected(self) -> Optional[str]:
        return self.combo.currentText()


# Notifications dialog
class NotifyDialog(QDialog):
    def __init__(self, parent, title: str, rows: List[Tuple[str, str]], actions: Dict[str, callable]):
        super().__init__(parent)
        self.setWindowTitle(title)
        self.setModal(True)
        self.resize(640, 400)
        layout = QVBoxLayout(self)

        table = QTableWidget()
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels(["Название", "Статус/Дата"])
        table.horizontalHeader().setStretchLastSection(True)
        table.verticalHeader().setVisible(False)
        table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectRows)
        table.setSelectionMode(QAbstractItemView.SingleSelection)
        table.setRowCount(min(10, len(rows)))
        for i, (name, status_date) in enumerate(rows[:10]):
            table.setItem(i, 0, QTableWidgetItem(name))
            table.setItem(i, 1, QTableWidgetItem(status_date))
        layout.addWidget(table)

        btns_layout = QHBoxLayout()
        for label, func in actions.items():
            b = QPushButton(label)
            b.clicked.connect(lambda checked=False, f=func: (f(), self.accept()))
            btns_layout.addWidget(b)
        layout.addLayout(btns_layout)

        cancel = QPushButton("Отмена")
        cancel.clicked.connect(self.reject)
        layout.addWidget(cancel)


# Views
class MainMenu(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app
        layout = QVBoxLayout(self)
        title = QLabel("УссурОЧки.рф — Заказ линз")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("font-weight: 600; font-size: 24px; margin: 16px;")
        layout.addWidget(title)

        btn_mkl = QPushButton("Заказы МКЛ")
        btn_mer = QPushButton("Заказы Меридиан")
        btn_settings = QPushButton("Настройки…")

        for b in (btn_mkl, btn_mer, btn_settings):
            b.setMinimumHeight(52)
            b.setStyleSheet("font-weight: 600;")

        btn_mkl.clicked.connect(lambda: self.app.show_mkl())
        btn_mer.clicked.connect(lambda: self.app.show_meridian())
        btn_settings.clicked.connect(lambda: self.app.show_settings())

        buttons = QVBoxLayout()
        buttons.addWidget(btn_mkl)
        buttons.addWidget(btn_mer)
        buttons.addWidget(btn_settings)
        layout.addLayout(buttons)
        layout.addStretch(1)


class MKLOrdersView(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.conn = app.conn

        root = QVBoxLayout(self)

        header = QHBoxLayout()
        back = QPushButton("← Главное меню")
        new = QPushButton("Новый заказ")
        edit = QPushButton("Редактировать")
        delete = QPushButton("Удалить")
        change_status = QPushButton("Сменить статус")
        clients = QPushButton("Клиенты")
        products = QPushButton("Товары")
        export_txt = QPushButton("Экспорт TXT")

        for b in (back, new, edit, delete, change_status, clients, products, export_txt):
            b.setMinimumHeight(36)
            b.setStyleSheet("font-weight: 600;")

        back.clicked.connect(self.app.show_main)
        new.clicked.connect(self.on_new)
        edit.clicked.connect(self.on_edit)
        delete.clicked.connect(self.on_delete)
        change_status.clicked.connect(self.on_change_status)
        clients.clicked.connect(self.app.show_clients)
        products.clicked.connect(lambda: self.app.show_products("mkl"))
        export_txt.clicked.connect(self.on_export)

        for w in (back, new, edit, delete, change_status, clients, products, export_txt):
            header.addWidget(w)
        root.addLayout(header)

        root.addWidget(QLabel("Заказ МКЛ • Таблица данных"))
        root.addWidget(QLabel("Поля: ФИО, Телефон, Товар, Sph, Cyl, Ax, BC, Количество, Статус, Дата, Комментарий"))

        self.table = QTableWidget()
        self.table.setColumnCount(11)
        self.table.setHorizontalHeaderLabels(["ФИО", "Телефон", "Товар", "Sph", "Cyl", "Ax", "BC", "Количество", "Статус", "Дата", "Комментарий"])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.setItemDelegate(StatusDelegate())
        self.table.itemDoubleClicked.connect(lambda _: self.on_edit())

        root.addWidget(self.table)

        self.refresh()

    def _load_products_mkl(self) -> List[str]:
        cur = self.conn.cursor()
        cur.execute("SELECT name FROM products_mkl ORDER BY name COLLATE NOCASE ASC;")
        return [r[0] for r in cur.fetchall()]

    def refresh(self):
        cur = self.conn.cursor()
        cur.execute("SELECT id,fio,phone,product,sph,cyl,ax,bc,qty,status,date,comment FROM mkl_orders ORDER BY id DESC;")
        rows = cur.fetchall()
        self.table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            rid, fio, phone, product, sph, cyl, ax, bc, qty, status, date, comment = row
            self.table.setItem(i, 0, QTableWidgetItem(fio))
            self.table.setItem(i, 1, QTableWidgetItem(format_phone_display(phone)))
            self.table.setItem(i, 2, QTableWidgetItem(product))
            self.table.setItem(i, 3, QTableWidgetItem(sph))
            self.table.setItem(i, 4, QTableWidgetItem("" if cyl is None else str(cyl)))
            self.table.setItem(i, 5, QTableWidgetItem("" if ax is None else str(ax)))
            self.table.setItem(i, 6, QTableWidgetItem("" if bc is None else str(bc)))
            self.table.setItem(i, 7, QTableWidgetItem(str(qty)))
            self.table.setItem(i, 8, QTableWidgetItem(status))
            self.table.setItem(i, 9, QTableWidgetItem(date))
            self.table.setItem(i, 10, QTableWidgetItem("ЕСТЬ" if comment else "НЕТ"))
            # store id in row for operations
            self.table.setVerticalHeaderItem(i, QTableWidgetItem(str(rid)))

        # Auto-select first row
        if rows:
            self.table.selectRow(0)

    def _selected_id(self) -> Optional[int]:
        idx = self.table.currentRow()
        if idx < 0:
            return None
        item = self.table.verticalHeaderItem(idx)
        if not item:
            return None
        try:
            return int(item.text())
        except Exception:
            return None

    def on_new(self):
        dlg = MKLOrderDialog(self, products=self._load_products_mkl())
        if dlg.exec() == QDialog.Accepted:
            data = dlg.get_data()
            if not data:
                return
            now = datetime.now().strftime("%Y-%m-%d %H:%M")
            cur = self.conn.cursor()
            cur.execute("""
                INSERT INTO mkl_orders (fio,phone,product,sph,cyl,ax,bc,qty,status,date,comment)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """, (data["fio"], data["phone"], data["product"], data["sph"], data["cyl"] or None,
                  data["ax"], data["bc"], data["qty"], "Не заказан", now, data["comment"]))
            self.conn.commit()
            self.refresh()

    def on_edit(self):
        rid = self._selected_id()
        if rid is None:
            return
        cur = self.conn.cursor()
        cur.execute("SELECT id,fio,phone,product,sph,cyl,ax,bc,qty,status,date,comment FROM mkl_orders WHERE id=?;", (rid,))
        row = cur.fetchone()
        if not row:
            return
        _, fio, phone, product, sph, cyl, ax, bc, qty, status, date, comment = row
        dlg = MKLOrderDialog(self, data={
            "fio": fio, "phone": phone, "product": product, "sph": sph, "cyl": cyl or "",
            "ax": ax, "bc": bc, "qty": qty, "comment": comment or ""
        }, products=self._load_products_mkl())
        if dlg.exec() == QDialog.Accepted:
            data = dlg.get_data()
            if not data:
                return
            cur.execute("""
                UPDATE mkl_orders SET fio=?,phone=?,product=?,sph=?,cyl=?,ax=?,bc=?,qty=?,comment=?
                WHERE id=?
            """, (data["fio"], data["phone"], data["product"], data["sph"], data["cyl"] or None,
                  data["ax"], data["bc"], data["qty"], data["comment"], rid))
            self.conn.commit()
            self.refresh()

    def on_delete(self):
        rid = self._selected_id()
        if rid is None:
            return
        if QMessageBox.question(self, "Удалить", "Удалить выбранный заказ?") == QMessageBox.Yes:
            cur = self.conn.cursor()
            cur.execute("DELETE FROM mkl_orders WHERE id=?;", (rid,))
            self.conn.commit()
            self.refresh()

    def on_change_status(self):
        rid = self._selected_id()
        if rid is None:
            return
        cur = self.conn.cursor()
        cur.execute("SELECT status FROM mkl_orders WHERE id=?;", (rid,))
        row = cur.fetchone()
        if not row:
            return
        current = row[0]
        dlg = StatusDialog(self, STATUSES_MKL, current=current)
        if dlg.exec() == QDialog.Accepted:
            new_status = dlg.selected()
            now = datetime.now().strftime("%Y-%m-%d %H:%M")
            cur.execute("UPDATE mkl_orders SET status=?, date=? WHERE id=?;", (new_status, now, rid))
            self.conn.commit()
            self.refresh()

    def on_export(self):
        try:
            export_path = self.app.settings.get("export_path") or user_desktop_path()
            if not os.path.isdir(export_path):
                export_path = os.getcwd()
            filename = f"MKL_{datetime.now().strftime('%d.%m.%y')}.txt"
            full = os.path.join(export_path, filename)

            cur = self.conn.cursor()
            cur.execute("""
                SELECT product, sph, cyl, ax, bc, qty
                FROM mkl_orders
                WHERE status='Не заказан'
                ORDER BY product COLLATE NOCASE ASC;
            """)
            rows = cur.fetchall()

            # Group by product
            groups: Dict[str, List[Tuple[str, Optional[str], Optional[int], Optional[float], int]]] = {}
            for product, sph, cyl, ax, bc, qty in rows:
                key = (product or "").strip() or "(Без названия)"
                groups.setdefault(key, []).append((sph, cyl, ax, bc, qty))

            lines: List[str] = []
            for product, items in groups.items():
                lines.append(product)
                for sph, cyl, ax, bc, qty in items:
                    parts = []
                    if sph:
                        parts.append(f"Sph: {sph}")
                    if cyl:
                        parts.append(f"Cyl: {cyl}")
                    if ax is not None:
                        parts.append(f"Ax: {ax}")
                    if bc is not None:
                        parts.append(f"BC: {bc}")
                    parts.append(f"Количество: {qty}")
                    lines.append(" ".join(parts))
                lines.append("")

            with open(full, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))

            # Open file
            if IS_WINDOWS:
                try:
                    os.startfile(full)  # type: ignore
                except Exception:
                    pass
            elif platform.system() == "Darwin":
                os.system(f"open \"{full}\"")
            else:
                os.system(f"xdg-open \"{full}\"")

            QMessageBox.information(self, "Экспорт", f"Файл создан: {full}")
        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(self, "Ошибка экспорта", str(e))


class MeridianOrdersView(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.conn = app.conn

        root = QVBoxLayout(self)

        header = QHBoxLayout()
        back = QPushButton("← Главное меню")
        new = QPushButton("Новый заказ")
        edit = QPushButton("Редактировать")
        delete = QPushButton("Удалить")
        change_status = QPushButton("Сменить статус")
        products = QPushButton("Товары")
        export_txt = QPushButton("Экспорт TXT")

        for b in (back, new, edit, delete, change_status, products, export_txt):
            b.setMinimumHeight(36)
            b.setStyleSheet("font-weight: 600;")

        back.clicked.connect(self.app.show_main)
        new.clicked.connect(self.on_new)
        edit.clicked.connect(self.on_edit)
        delete.clicked.connect(self.on_delete)
        change_status.clicked.connect(self.on_change_status)
        products.clicked.connect(lambda: self.app.show_products("meridian"))
        export_txt.clicked.connect(self.on_export)

        for w in (back, new, edit, delete, change_status, products, export_txt):
            header.addWidget(w)
        root.addLayout(header)

        root.addWidget(QLabel("Заказ Меридиан • Список заказов"))
        root.addWidget(QLabel("Каждый заказ может содержать несколько позиций товара"))

        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Название заказа", "Позиций", "Статус", "Дата"])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.itemDoubleClicked.connect(lambda _: self.on_edit())

        root.addWidget(self.table)

        self.refresh()

    def refresh(self):
        cur = self.conn.cursor()
        cur.execute("""
            SELECT o.id, o.title, o.status, o.date, COUNT(i.id)
            FROM meridian_orders o
            LEFT JOIN meridian_items i ON i.order_id = o.id
            GROUP BY o.id
            ORDER BY o.id DESC;
        """)
        rows = cur.fetchall()
        self.table.setRowCount(len(rows))
        for i, (oid, title, status, date, count) in enumerate(rows):
            self.table.setItem(i, 0, QTableWidgetItem(title))
            self.table.setItem(i, 1, QTableWidgetItem(str(count)))
            self.table.setItem(i, 2, QTableWidgetItem(status))
            self.table.setItem(i, 3, QTableWidgetItem(date))
            self.table.setVerticalHeaderItem(i, QTableWidgetItem(str(oid)))
        if rows:
            self.table.selectRow(0)

    def _selected_id(self) -> Optional[int]:
        idx = self.table.currentRow()
        if idx < 0:
            return None
        item = self.table.verticalHeaderItem(idx)
        if not item:
            return None
        try:
            return int(item.text())
        except Exception:
            return None

    def _next_title(self) -> str:
        cur = self.conn.cursor()
        cur.execute("SELECT MAX(id) FROM meridian_orders;")
        mx = cur.fetchone()[0]
        n = (mx or 0) + 1
        return f"Заказ Меридиан #{n}"

    def on_new(self):
        title = self._next_title()
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        cur = self.conn.cursor()
        cur.execute("INSERT INTO meridian_orders (title,status,date) VALUES (?,?,?);", (title, "Не заказан", now))
        self.conn.commit()
        self.refresh()

    def on_edit(self):
        oid = self._selected_id()
        if oid is None:
            return
        dlg = MeridianEditDialog(self, self.conn, oid)
        dlg.exec()
        self.refresh()

    def on_delete(self):
        oid = self._selected_id()
        if oid is None:
            return
        if QMessageBox.question(self, "Удалить", "Удалить выбранный заказ?") == QMessageBox.Yes:
            cur = self.conn.cursor()
            cur.execute("DELETE FROM meridian_orders WHERE id=?;", (oid,))
            self.conn.commit()
            self.refresh()

    def on_change_status(self):
        oid = self._selected_id()
        if oid is None:
            return
        cur = self.conn.cursor()
        cur.execute("SELECT status FROM meridian_orders WHERE id=?;", (oid,))
        row = cur.fetchone()
        if not row:
            return
        current = row[0]
        dlg = StatusDialog(self, STATUSES_MERIDIAN, current=current)
        if dlg.exec() == QDialog.Accepted:
            new_status = dlg.selected()
            now = datetime.now().strftime("%Y-%m-%d %H:%M")
            cur.execute("UPDATE meridian_orders SET status=?, date=? WHERE id=?;", (new_status, now, oid))
            self.conn.commit()
            self.refresh()

    def on_export(self):
        try:
            export_path = self.app.settings.get("export_path") or user_desktop_path()
            if not os.path.isdir(export_path):
                export_path = os.getcwd()
            filename = f"MERIDIAN_{datetime.now().strftime('%d.%m.%y')}.txt"
            full = os.path.join(export_path, filename)

            cur = self.conn.cursor()
            cur.execute("""
                SELECT i.product, i.sph, i.cyl, i.ax, i.d, i.qty
                FROM meridian_items i
                JOIN meridian_orders o ON o.id = i.order_id
                WHERE o.status='Не заказан'
                ORDER BY i.product COLLATE NOCASE ASC;
            """)
            rows = cur.fetchall()

            # Group by product
            groups: Dict[str, List[Tuple[Optional[str], Optional[str], Optional[int], Optional[int], int]]] = {}
            for product, sph, cyl, ax, d, qty in rows:
                key = (product or "").strip() or "(Без названия)"
                groups.setdefault(key, []).append((sph, cyl, ax, d, qty))

            lines: List[str] = []
            for product, items in groups.items():
                lines.append(product)
                for sph, cyl, ax, d, qty in items:
                    parts = []
                    if sph:
                        parts.append(f"Sph: {sph}")
                    if cyl:
                        parts.append(f"Cyl: {cyl}")
                    if ax is not None:
                        parts.append(f"Ax: {ax}")
                    if d is not None:
                        parts.append(f"D:{d}мм")
                    parts.append(f"Количество: {qty}")
                    lines.append(" ".join(parts))
                lines.append("")

            with open(full, "w", encoding="utf-8") as f:
                f.write("\n".join(lines))

            # Open file
            if IS_WINDOWS:
                try:
                    os.startfile(full)  # type: ignore
                except Exception:
                    pass
            elif platform.system() == "Darwin":
                os.system(f"open \"{full}\"")
            else:
                os.system(f"xdg-open \"{full}\"")

            QMessageBox.information(self, "Экспорт", f"Файл создан: {full}")
        except Exception as e:
            traceback.print_exc()
            QMessageBox.critical(self, "Ошибка экспорта", str(e))


class MeridianEditDialog(QDialog):
    def __init__(self, parent, conn: sqlite3.Connection, order_id: int):
        super().__init__(parent)
        self.conn = conn
        self.order_id = order_id
        self.setWindowTitle("Редактирование заказа Меридиан")
        self.resize(720, 480)

        layout = QVBoxLayout(self)

        # Status combobox
        status_row = QHBoxLayout()
        status_row.addWidget(QLabel("Статус"))
        self.status_combo = QComboBox()
        self.status_combo.addItems(STATUSES_MERIDIAN)
        status_row.addWidget(self.status_combo)
        layout.addLayout(status_row)

        # Items table
        self.table = QTableWidget()
        self.table.setColumnCount(6)
        self.table.setHorizontalHeaderLabels(["Product", "Sph", "Cyl", "Ax", "D", "Количество"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        layout.addWidget(self.table)

        # Buttons
        btns = QHBoxLayout()
        add_item = QPushButton("Добавить позицию")
        edit_item = QPushButton("Редактировать позицию")
        del_item = QPushButton("Удалить позицию")
        for b in (add_item, edit_item, del_item):
            b.setMinimumHeight(36)
            b.setStyleSheet("font-weight: 600;")
        add_item.clicked.connect(self.on_add_item)
        edit_item.clicked.connect(self.on_edit_item)
        del_item.clicked.connect(self.on_delete_item)
        for b in (add_item, edit_item, del_item):
            btns.addWidget(b)
        layout.addLayout(btns)

        # Save/Cancel
        actions = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        actions.accepted.connect(self.on_save)
        actions.rejected.connect(self.reject)
        layout.addWidget(actions)

        self.load()

    def load(self):
        cur = self.conn.cursor()
        cur.execute("SELECT title,status FROM meridian_orders WHERE id=?;", (self.order_id,))
        row = cur.fetchone()
        if not row:
            return
        title, status = row
        self.setWindowTitle(f"Редактирование — {title}")
        idx = self.status_combo.findText(status)
        if idx >= 0:
            self.status_combo.setCurrentIndex(idx)

        cur.execute("SELECT id,product,sph,cyl,ax,d,qty FROM meridian_items WHERE order_id=? ORDER BY id DESC;", (self.order_id,))
        rows = cur.fetchall()
        self.table.setRowCount(len(rows))
        for i, (iid, product, sph, cyl, ax, d, qty) in enumerate(rows):
            self.table.setItem(i, 0, QTableWidgetItem(product))
            self.table.setItem(i, 1, QTableWidgetItem("" if sph is None else str(sph)))
            self.table.setItem(i, 2, QTableWidgetItem("" if cyl is None else str(cyl)))
            self.table.setItem(i, 3, QTableWidgetItem("" if ax is None else str(ax)))
            self.table.setItem(i, 4, QTableWidgetItem("" if d is None else str(d)))
            self.table.setItem(i, 5, QTableWidgetItem(str(qty)))
            self.table.setVerticalHeaderItem(i, QTableWidgetItem(str(iid)))

        if rows:
            self.table.selectRow(0)

    def _selected_iid(self) -> Optional[int]:
        idx = self.table.currentRow()
        if idx < 0:
            return None
        item = self.table.verticalHeaderItem(idx)
        if not item:
            return None
        try:
            return int(item.text())
        except Exception:
            return None

    def on_add_item(self):
        dlg = MeridianItemDialog(self)
        if dlg.exec() == QDialog.Accepted:
            data = dlg.get_data()
            if not data:
                return
            cur = self.conn.cursor()
            cur.execute("""
                INSERT INTO meridian_items (order_id,product,sph,cyl,ax,d,qty)
                VALUES (?,?,?,?,?,?,?)
            """, (self.order_id, data["product"], data["sph"], data["cyl"], data["ax"], data["d"], data["qty"]))
            self.conn.commit()
            self.load()

    def on_edit_item(self):
        iid = self._selected_iid()
        if iid is None:
            return
        cur = self.conn.cursor()
        cur.execute("SELECT id,product,sph,cyl,ax,d,qty FROM meridian_items WHERE id=?;", (iid,))
        row = cur.fetchone()
        if not row:
            return
        _, product, sph, cyl, ax, d, qty = row
        dlg = MeridianItemDialog(self, data={
            "product": product,
            "sph": sph,
            "cyl": cyl,
            "ax": ax,
            "d": d,
            "qty": qty
        })
        if dlg.exec() == QDialog.Accepted:
            data = dlg.get_data()
            if not data:
                return
            cur.execute("""
                UPDATE meridian_items SET product=?,sph=?,cyl=?,ax=?,d=?,qty=? WHERE id=?
            """, (data["product"], data["sph"], data["cyl"], data["ax"], data["d"], data["qty"], iid))
            self.conn.commit()
            self.load()

    def on_delete_item(self):
        iid = self._selected_iid()
        if iid is None:
            return
        if QMessageBox.question(self, "Удалить", "Удалить выбранную позицию?") == QMessageBox.Yes:
            cur = self.conn.cursor()
            cur.execute("DELETE FROM meridian_items WHERE id=?;", (iid,))
            self.conn.commit()
            self.load()

    def on_save(self):
        new_status = self.status_combo.currentText()
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        cur = self.conn.cursor()
        cur.execute("UPDATE meridian_orders SET status=?, date=? WHERE id=?;", (new_status, now, self.order_id))
        self.conn.commit()
        self.accept()


class MeridianItemDialog(QDialog):
    def __init__(self, parent, data: Optional[dict] = None):
        super().__init__(parent)
        self.setWindowTitle("Позиция заказа Меридиан")
        self.setModal(True)
        layout = QFormLayout(self)

        self.product = QLineEdit()
        self.sph = QLineEdit()
        self.cyl = QLineEdit()
        self.ax = QLineEdit()
        self.d = QLineEdit()
        self.qty = QSpinBox()
        self.qty.setRange(1, 20)

        layout.addRow("Product", self.product)
        layout.addRow("Sph", self.sph)
        layout.addRow("Cyl", self.cyl)
        layout.addRow("Ax", self.ax)
        layout.addRow("D", self.d)
        layout.addRow("Количество", self.qty)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

        if data:
            self.product.setText(data.get("product", ""))
            self.sph.setText("" if data.get("sph") is None else str(data.get("sph")))
            self.cyl.setText("" if data.get("cyl") is None else str(data.get("cyl")))
            self.ax.setText("" if data.get("ax") is None else str(data.get("ax")))
            self.d.setText("" if data.get("d") is None else str(data.get("d")))
            self.qty.setValue(int(data.get("qty", 1)))

    def get_data(self) -> Optional[dict]:
        product = self.product.text().strip() or "(Без названия)"

        def parse_optional_float(s: str) -> Optional[float]:
            s = s.strip().replace(",", ".")
            if not s:
                return None
            try:
                return float(s)
            except Exception:
                return None

        def parse_optional_int(s: str) -> Optional[int]:
            s = s.strip()
            if not s:
                return None
            try:
                return int(s)
            except Exception:
                return None

        sph = parse_optional_float(self.sph.text())
        if sph is not None:
            sph = normalize_step(sph, 0.25, -30.0, 30.0)

        cyl = parse_optional_float(self.cyl.text())
        if cyl is not None:
            cyl = normalize_step(cyl, 0.25, -10.0, 10.0)

        ax = parse_optional_int(self.ax.text())
        if ax is not None:
            ax = validate_int(ax, 0, 180)

        d = parse_optional_int(self.d.text())
        if d is not None:
            d = validate_int(d, 40, 90)
            # snap to 5
            d = int(round(d / 5) * 5)

        qty = self.qty.value()

        return {
            "product": product,
            "sph": None if sph is None else f"{sph:.2f}",
            "cyl": None if cyl is None else f"{cyl:.2f}",
            "ax": ax,
            "d": d,
            "qty": qty
        }


class ClientsView(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.conn = app.conn

        root = QVBoxLayout(self)

        back = QPushButton("← Назад")
        back.setMinimumHeight(36)
        back.setStyleSheet("font-weight: 600;")
        back.clicked.connect(self.app.show_mkl)  # Return to MKL by default
        root.addWidget(back)

        search_row = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Поиск по ФИО или телефону")
        find_btn = QPushButton("Найти")
        find_btn.clicked.connect(self.refresh)
        search_row.addWidget(self.search)
        search_row.addWidget(find_btn)
        root.addLayout(search_row)

        actions = QHBoxLayout()
        add = QPushButton("Добавить")
        edit = QPushButton("Редактировать")
        delete = QPushButton("Удалить")
        for b in (add, edit, delete):
            b.setMinimumHeight(36)
            b.setStyleSheet("font-weight: 600;")
        add.clicked.connect(self.on_add)
        edit.clicked.connect(self.on_edit)
        delete.clicked.connect(self.on_delete)
        for b in (add, edit, delete):
            actions.addWidget(b)
        root.addLayout(actions)

        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["ФИО", "Телефон"])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.itemDoubleClicked.connect(lambda _: self.on_edit())
        root.addWidget(self.table)

        self.refresh()

    def refresh(self):
        q = self.search.text().strip().lower()
        cur = self.conn.cursor()
        if q:
            like = f"%{q}%"
            cur.execute("""
                SELECT id,fio,phone FROM clients
                WHERE lower(fio) LIKE ? OR phone LIKE ?
                ORDER BY id DESC;
            """, (like, like))
        else:
            cur.execute("SELECT id,fio,phone FROM clients ORDER BY id DESC;")
        rows = cur.fetchall()
        self.table.setRowCount(len(rows))
        for i, (cid, fio, phone) in enumerate(rows):
            self.table.setItem(i, 0, QTableWidgetItem(fio))
            self.table.setItem(i, 1, QTableWidgetItem(format_phone_display(phone)))
            self.table.setVerticalHeaderItem(i, QTableWidgetItem(str(cid)))
        if rows:
            self.table.selectRow(0)

    def _selected_id(self) -> Optional[int]:
        idx = self.table.currentRow()
        if idx < 0:
            return None
        item = self.table.verticalHeaderItem(idx)
        if not item:
            return None
        try:
            return int(item.text())
        except Exception:
            return None

    def on_add(self):
        dlg = ClientDialog(self)
        if dlg.exec() == QDialog.Accepted:
            data = dlg.get_data()
            if not data:
                return
            cur = self.conn.cursor()
            cur.execute("INSERT INTO clients (fio,phone) VALUES (?,?);", (data["fio"], data["phone"]))
            self.conn.commit()
            self.refresh()

    def on_edit(self):
        cid = self._selected_id()
        if cid is None:
            return
        cur = self.conn.cursor()
        cur.execute("SELECT id,fio,phone FROM clients WHERE id=?;", (cid,))
        row = cur.fetchone()
        if not row:
            return
        _, fio, phone = row
        dlg = ClientDialog(self, data={"fio": fio, "phone": phone})
        if dlg.exec() == QDialog.Accepted:
            data = dlg.get_data()
            if not data:
                return
            cur.execute("UPDATE clients SET fio=?,phone=? WHERE id=?;", (data["fio"], data["phone"], cid))
            self.conn.commit()
            self.refresh()

    def on_delete(self):
        cid = self._selected_id()
        if cid is None:
            return
        if QMessageBox.question(self, "Удалить", "Удалить клиента?") == QMessageBox.Yes:
            cur = self.conn.cursor()
            cur.execute("DELETE FROM clients WHERE id=?;", (cid,))
            self.conn.commit()
            self.refresh()


class ClientDialog(QDialog):
    def __init__(self, parent, data: Optional[dict] = None):
        super().__init__(parent)
        self.setWindowTitle("Карточка клиента")
        self.setModal(True)
        layout = QFormLayout(self)

        self.fio = QLineEdit()
        self.phone = QLineEdit()
        layout.addRow("ФИО", self.fio)
        layout.addRow("Телефон", self.phone)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

        if data:
            self.fio.setText(data.get("fio", ""))
            self.phone.setText(data.get("phone", ""))

    def get_data(self) -> Optional[dict]:
        fio = self.fio.text().strip()
        phone_digits = only_digits(self.phone.text())
        if not fio or not phone_digits:
            QMessageBox.warning(self, "Ошибка", "ФИО и Телефон обязательны.")
            return None
        return {"fio": fio, "phone": phone_digits}


class ProductsView(QWidget):
    def __init__(self, app, catalog: str):
        super().__init__()
        self.app = app
        self.conn = app.conn
        self.catalog = catalog  # "mkl" or "meridian"
        root = QVBoxLayout(self)

        back = QPushButton("← Назад")
        back.setMinimumHeight(36)
        back.setStyleSheet("font-weight: 600;")
        back.clicked.connect(self.app.show_mkl if catalog == "mkl" else self.app.show_meridian)
        root.addWidget(back)

        title = QLabel("Товары (МКЛ)" if catalog == "mkl" else "Товары (Меридиан)")
        root.addWidget(title)

        actions = QHBoxLayout()
        add = QPushButton("Добавить")
        edit = QPushButton("Редактировать")
        delete = QPushButton("Удалить")
        for b in (add, edit, delete):
            b.setMinimumHeight(36)
            b.setStyleSheet("font-weight: 600;")
        add.clicked.connect(self.on_add)
        edit.clicked.connect(self.on_edit)
        delete.clicked.connect(self.on_delete)
        for b in (add, edit, delete):
            actions.addWidget(b)
        root.addLayout(actions)

        self.table = QTableWidget()
        self.table.setColumnCount(1)
        self.table.setHorizontalHeaderLabels(["Название товара"])
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.itemDoubleClicked.connect(lambda _: self.on_edit())
        root.addWidget(self.table)

        self.refresh()

    def refresh(self):
        cur = self.conn.cursor()
        if self.catalog == "mkl":
            cur.execute("SELECT id,name FROM products_mkl ORDER BY id DESC;")
        else:
            cur.execute("SELECT id,name FROM products_meridian ORDER BY id DESC;")
        rows = cur.fetchall()
        self.table.setRowCount(len(rows))
        for i, (pid, name) in enumerate(rows):
            self.table.setItem(i, 0, QTableWidgetItem(name))
            self.table.setVerticalHeaderItem(i, QTableWidgetItem(str(pid)))
        if rows:
            self.table.selectRow(0)

    def _selected_id(self) -> Optional[int]:
        idx = self.table.currentRow()
        if idx < 0:
            return None
        item = self.table.verticalHeaderItem(idx)
        if not item:
            return None
        try:
            return int(item.text())
        except Exception:
            return None

    def on_add(self):
        dlg = ProductDialog(self)
        if dlg.exec() == QDialog.Accepted:
            name = dlg.get_name()
            if not name:
                return
            cur = self.conn.cursor()
            if self.catalog == "mkl":
                cur.execute("INSERT INTO products_mkl (name) VALUES (?);", (name,))
            else:
                cur.execute("INSERT INTO products_meridian (name) VALUES (?);", (name,))
            self.conn.commit()
            self.refresh()

    def on_edit(self):
        pid = self._selected_id()
        if pid is None:
            return
        cur = self.conn.cursor()
        if self.catalog == "mkl":
            cur.execute("SELECT id,name FROM products_mkl WHERE id=?;", (pid,))
        else:
            cur.execute("SELECT id,name FROM products_meridian WHERE id=?;", (pid,))
        row = cur.fetchone()
        if not row:
            return
        _, name = row
        dlg = ProductDialog(self, name=name)
        if dlg.exec() == QDialog.Accepted:
            new_name = dlg.get_name()
            if not new_name:
                return
            if self.catalog == "mkl":
                cur.execute("UPDATE products_mkl SET name=? WHERE id=?;", (new_name, pid))
            else:
                cur.execute("UPDATE products_meridian SET name=? WHERE id=?;", (new_name, pid))
            self.conn.commit()
            self.refresh()

    def on_delete(self):
        pid = self._selected_id()
        if pid is None:
            return
        if QMessageBox.question(self, "Удалить", "Удалить товар?") == QMessageBox.Yes:
            cur = self.conn.cursor()
            if self.catalog == "mkl":
                cur.execute("DELETE FROM products_mkl WHERE id=?;", (pid,))
            else:
                cur.execute("DELETE FROM products_meridian WHERE id=?;", (pid,))
            self.conn.commit()
            self.refresh()


class ProductDialog(QDialog):
    def __init__(self, parent, name: str = ""):
        super().__init__(parent)
        self.setWindowTitle("Карточка товара")
        self.setModal(True)
        layout = QFormLayout(self)
        self.name = QLineEdit()
        self.name.setText(name)
        layout.addRow("Название товара", self.name)
        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addRow(buttons)

    def get_name(self) -> Optional[str]:
        n = self.name.text().strip()
        if not n:
            QMessageBox.warning(self, "Ошибка", "Введите название товара.")
            return None
        return n


class SettingsView(QWidget):
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.settings = app.settings
        root = QVBoxLayout(self)

        back = QPushButton("← Назад")
        back.setMinimumHeight(36)
        back.setStyleSheet("font-weight: 600;")
        back.clicked.connect(self.app.show_main)
        root.addWidget(back)

        # UI scale
        row_ui = QHBoxLayout()
        row_ui.addWidget(QLabel("Масштаб интерфейса"))
        self.ui_scale = QDoubleSpinBoxFix()
        self.ui_scale.setRange(0.8, 2.0)
        self.ui_scale.setSingleStep(0.05)
        self.ui_scale.setValue(float(self.settings.get("ui_scale", 1.25)))
        row_ui.addWidget(self.ui_scale)
        root.addLayout(row_ui)

        # Font size
        row_font = QHBoxLayout()
        row_font.addWidget(QLabel("Размер шрифта (глобально)"))
        self.ui_font = QSpinBox()
        self.ui_font.setRange(12, 28)
        self.ui_font.setValue(int(self.settings.get("ui_font_size", 17)))
        row_font.addWidget(self.ui_font)
        root.addLayout(row_font)

        # Export path
        row_export = QHBoxLayout()
        row_export.addWidget(QLabel("Папка экспорта TXT"))
        self.export_path = QLineEdit(self.settings.get("export_path", ""))
        browse = QPushButton("Обзор…")
        browse.clicked.connect(self.on_browse)
        row_export.addWidget(self.export_path)
        row_export.addWidget(browse)
        root.addLayout(row_export)

        # Tray and autostart
        self.tray_enabled = QCheckBox("Включить системный трей")
        self.tray_enabled.setChecked(bool(self.settings.get("tray_enabled", True)))
        self.minimize_to_tray = QCheckBox("Сворачивать в трей (закрыть/свернуть)")
        self.minimize_to_tray.setChecked(bool(self.settings.get("minimize_to_tray", True)))
        self.start_in_tray = QCheckBox("Запускать в трее (при старте)")
        self.start_in_tray.setChecked(bool(self.settings.get("start_in_tray", True)))
        self.autostart_enabled = QCheckBox("Автозапуск с Windows")
        self.autostart_enabled.setChecked(bool(self.settings.get("autostart_enabled", False)))
        for w in (self.tray_enabled, self.minimize_to_tray, self.start_in_tray, self.autostart_enabled):
            root.addWidget(w)

        # Meridian notifications
        root.addWidget(QLabel("Уведомления «Меридиан»"))
        self.notify_enabled = QCheckBox("Включить уведомления")
        self.notify_enabled.setChecked(bool(self.settings.get("notify_enabled", False)))
        days_row = QHBoxLayout()
        days_row.addWidget(QLabel("Дни недели"))
        self.week_checks = []
        current_days = set(self.settings.get("notify_days", []))
        for i, name in enumerate(["Пн","Вт","Ср","Чт","Пт","Сб","Вс"]):
            cb = QCheckBox(name)
            cb.setChecked(i in current_days)
            days_row.addWidget(cb)
            self.week_checks.append(cb)
        root.addLayout(days_row)
        time_row = QHBoxLayout()
        time_row.addWidget(QLabel("Время (чч:мм)"))
        self.notify_time = QLineEdit(self.settings.get("notify_time", "09:00"))
        time_row.addWidget(self.notify_time)
        root.addLayout(time_row)
        root.addWidget(self.notify_enabled)

        # MKL notifications
        root.addWidget(QLabel("Уведомления «МКЛ»"))
        self.mkl_notify_enabled = QCheckBox("Включить уведомления")
        self.mkl_notify_enabled.setChecked(bool(self.settings.get("mkl_notify_enabled", False)))
        after_row = QHBoxLayout()
        after_row.addWidget(QLabel("Напоминать через (дней)"))
        self.mkl_days = QSpinBox()
        self.mkl_days.setRange(1, 60)
        self.mkl_days.setValue(int(self.settings.get("mkl_notify_after_days", 3)))
        after_row.addWidget(self.mkl_days)
        root.addLayout(after_row)

        time_row_mkl = QHBoxLayout()
        time_row_mkl.addWidget(QLabel("Время (чч:мм)"))
        self.mkl_time = QLineEdit(self.settings.get("mkl_notify_time", "09:00"))
        time_row_mkl.addWidget(self.mkl_time)
        root.addLayout(time_row_mkl)
        root.addWidget(self.mkl_notify_enabled)

        # Sound settings (Windows)
        root.addWidget(QLabel("Звук уведомления (Windows)"))
        self.notify_sound_enabled = QCheckBox("Включить звук (Windows)")
        self.notify_sound_enabled.setChecked(bool(self.settings.get("notify_sound_enabled", True)))
        mode_row = QHBoxLayout()
        mode_row.addWidget(QLabel("Режим звука"))
        self.sound_mode = QComboBox()
        self.sound_mode.addItems(["alias", "file"])
        self.sound_mode.setCurrentText(self.settings.get("notify_sound_mode", "alias"))
        mode_row.addWidget(self.sound_mode)
        root.addLayout(mode_row)

        alias_row = QHBoxLayout()
        alias_row.addWidget(QLabel("Тип звука (Windows)"))
        self.sound_alias = QComboBox()
        self.sound_alias.addItems(["SystemAsterisk","SystemExclamation","SystemDefault","SystemHand","SystemQuestion"])
        self.sound_alias.setCurrentText(self.settings.get("notify_sound_alias", "SystemAsterisk"))
        alias_row.addWidget(self.sound_alias)
        root.addLayout(alias_row)

        file_row = QHBoxLayout()
        file_row.addWidget(QLabel("Файл WAV"))
        self.sound_file = QLineEdit(self.settings.get("notify_sound_file", ""))
        file_browse = QPushButton("Обзор…")
        file_browse.clicked.connect(self.on_browse_wav)
        file_row.addWidget(self.sound_file)
        file_row.addWidget(file_browse)
        root.addLayout(file_row)

        # Actions
        actions = QHBoxLayout()
        test_mkl = QPushButton("Проверить уведомление МКЛ")
        apply_btn = QPushButton("Применить")
        save_btn = QPushButton("Сохранить")
        for b in (test_mkl, apply_btn, save_btn):
            b.setMinimumHeight(36)
            b.setStyleSheet("font-weight: 600;")
        test_mkl.clicked.connect(self.app.test_mkl_notify)
        apply_btn.clicked.connect(self.on_apply)
        save_btn.clicked.connect(self.on_save)
        actions.addWidget(test_mkl)
        actions.addWidget(apply_btn)
        actions.addWidget(save_btn)
        root.addLayout(actions)

    def on_browse(self):
        path = QFileDialog.getExistingDirectory(self, "Выбор папки экспорта", self.export_path.text().strip() or user_desktop_path())
        if path:
            self.export_path.setText(path)

    def on_browse_wav(self):
        path, _ = QFileDialog.getOpenFileName(self, "Выбор WAV файла", "", "WAV Files (*.wav)")
        if path:
            self.sound_file.setText(path)
            self.sound_mode.setCurrentText("file")

    def on_apply(self):
        s = self.collect_settings()
        self.app.apply_ui_settings(s)
        self.app.apply_autostart(s)
        QMessageBox.information(self, "Применено", "Изменения применены.")

    def on_save(self):
        s = self.collect_settings()
        save_settings(s)
        self.app.settings = s
        self.app.apply_ui_settings(s)
        self.app.apply_autostart(s)
        QMessageBox.information(self, "Сохранено", "Настройки сохранены.")

    def collect_settings(self) -> dict:
        s = self.app.settings.copy()
        s["ui_scale"] = float(self.ui_scale.value())
        s["ui_font_size"] = int(self.ui_font.value())
        s["export_path"] = self.export_path.text().strip() or user_desktop_path()
        s["tray_enabled"] = bool(self.tray_enabled.isChecked())
        s["minimize_to_tray"] = bool(self.minimize_to_tray.isChecked())
        s["start_in_tray"] = bool(self.start_in_tray.isChecked())
        s["autostart_enabled"] = bool(self.autostart_enabled.isChecked())

        s["notify_enabled"] = bool(self.notify_enabled.isChecked())
        s["notify_days"] = [i for i, cb in enumerate(self.week_checks) if cb.isChecked()]
        s["notify_time"] = self.notify_time.text().strip() or "09:00"

        s["mkl_notify_enabled"] = bool(self.mkl_notify_enabled.isChecked())
        s["mkl_notify_after_days"] = int(self.mkl_days.value())
        s["mkl_notify_time"] = self.mkl_time.text().strip() or "09:00"

        s["notify_sound_enabled"] = bool(self.notify_sound_enabled.isChecked())
        s["notify_sound_mode"] = self.sound_mode.currentText()
        s["notify_sound_alias"] = self.sound_alias.currentText()
        s["notify_sound_file"] = self.sound_file.text().strip()

        return s


class QDoubleSpinBoxFix(QSpinBox):
    # Simple replacement to avoid floating widget import; store *100 step
    def __init__(self):
        super().__init__()
        self._min = 80
        self._max = 200
        self._step = 5
        self._value = 125
        self.setRange(self._min, self._max)
        self.setSingleStep(self._step)
        self.setValue(self._value)

    def value(self) -> float:  # type: ignore
        return self._value / 100.0

    def setValue(self, v: float):  # type: ignore
        self._value = int(round(v * 100))
        super().setValue(self._value)

    def setRange(self, mn: float, mx: float):  # type: ignore
        self._min = int(round(mn * 100))
        self._max = int(round(mx * 100))
        super().setRange(self._min, self._max)

    def setSingleStep(self, s: float):  # type: ignore
        self._step = int(round(s * 100))
        super().setSingleStep(self._step)


# Application
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.conn = ensure_db()
        self.settings = load_settings()
        self.tray: Optional[QSystemTrayIcon] = None

        # Central stack
        self.main_menu = MainMenu(self)
        self.mkl_view = MKLOrdersView(self)
        self.meridian_view = MeridianOrdersView(self)
        self.clients_view = ClientsView(self)
        self.products_mkl_view = ProductsView(self, "mkl")
        self.products_meridian_view = ProductsView(self, "meridian")
        self.settings_view = SettingsView(self)

        self.setCentralWidget(self.main_menu)

        self.apply_ui_settings(self.settings)
        self.resize(1200, 800)
        self.show()
        self._maximize_initial()

        # tray start
        if self.settings.get("start_in_tray", True) and self.settings.get("tray_enabled", True):
            self.hide()
            self.start_tray()

        # planner (every minute)
        self.timer = QTimer(self)
        self.timer.setInterval(60 * 1000)
        self.timer.timeout.connect(self.check_notifications)
        self.timer.start()

    def _maximize_initial(self):
        try:
            self.showMaximized()
        except Exception:
            screen = QApplication.primaryScreen().geometry()
            self.resize(screen.width(), screen.height())

        # Restore geometry if stored
        g = self.settings.get("main_geometry", "")
        if g:
            try:
                # Qt doesn't directly parse "WxH+X+Y"; leave as future
                pass
            except Exception:
                pass

    def apply_ui_settings(self, s: dict):
        # Global font
        app = QApplication.instance()
        font = app.font()
        font.setPointSize(int(s.get("ui_font_size", 17)))
        app.setFont(font)

        # Scale via palette and style sheets for readability
        self.setStyleSheet("""
            QPushButton { padding: 8px 12px; }
            QTableWidget::item { padding: 6px; }
        """)

    def show_main(self):
        self.setCentralWidget(self.main_menu)

    def show_mkl(self):
        self.mkl_view.refresh()
        self.setCentralWidget(self.mkl_view)

    def show_meridian(self):
        self.meridian_view.refresh()
        self.setCentralWidget(self.meridian_view)

    def show_clients(self):
        self.clients_view.refresh()
        self.setCentralWidget(self.clients_view)

    def show_products(self, kind: str):
        if kind == "mkl":
            self.products_mkl_view.refresh()
            self.setCentralWidget(self.products_mkl_view)
        else:
            self.products_meridian_view.refresh()
            self.setCentralWidget(self.products_meridian_view)

    def show_settings(self):
        self.settings_view = SettingsView(self)  # refresh with current
        self.setCentralWidget(self.settings_view)

    # Tray
    def start_tray(self):
        if not self.settings.get("tray_enabled", True):
            return
        if self.tray:
            self.tray.hide()
            self.tray.deleteLater()
            self.tray = None

        icon = self._best_icon()
        self.tray = QSystemTrayIcon(icon, self)
        menu = QMenu()
        open_action = QAction("Открыть", self)
        open_action.triggered.connect(self.restore_from_tray)
        menu.addAction(open_action)

        if IS_WINDOWS:
            auto = QAction(f"Автозапуск: {'Вкл' if self.settings.get('autostart_enabled', False) else 'Выкл'}", self)
            auto.triggered.connect(self.toggle_autostart)
            menu.addAction(auto)

        exit_action = QAction("Выход", self)
        exit_action.triggered.connect(self.exit_from_tray)
        menu.addAction(exit_action)

        self.tray.setContextMenu(menu)
        self.tray.setToolTip(APP_TITLE)
        self.tray.show()

    def _best_icon(self) -> QIcon:
        path = self.settings.get("tray_logo_path", "")
        if path and os.path.exists(path):
            return QIcon(path)
        # generate placeholder icon
        pix = QIcon.fromTheme("applications-graphics")
        if not pix.isNull():
            return pix
        # fallback: empty icon
        return QIcon()

    def restore_from_tray(self):
        self.show()
        self.raise_()
        self.activateWindow()
        if self.tray:
            self.tray.hide()
            self.tray.deleteLater()
            self.tray = None

    def exit_from_tray(self):
        # Save geometry string
        geo = self.geometry()
        geom_str = f"{geo.width()}x{geo.height()}+{geo.x()}+{geo.y()}"
        s = self.settings.copy()
        s["main_geometry"] = geom_str
        try:
            save_settings(s)
            self.settings = s
        except Exception:
            pass
        QApplication.instance().quit()

    def toggle_autostart(self):
        s = self.settings.copy()
        s["autostart_enabled"] = not s.get("autostart_enabled", False)
        try:
            save_settings(s)
            self.settings = s
            self.apply_autostart(s)
            self.start_tray()  # rebuild label
        except Exception:
            pass

    def apply_autostart(self, s: dict):
        if IS_WINDOWS:
            try:
                import winreg
                run_key = r"Software\Microsoft\Windows\CurrentVersion\Run"
                with winreg.OpenKey(winreg.HKEY_CURRENT_USER, run_key, 0, winreg.KEY_SET_VALUE) as key:
                    if s.get("autostart_enabled", False):
                        exe_path = os.path.abspath(sys.argv[0])
                        winreg.SetValueEx(key, "UssurOchkiRF", 0, winreg.REG_SZ, exe_path)
                    else:
                        try:
                            winreg.DeleteValue(key, "UssurOchkiRF")
                        except Exception:
                            pass
            except Exception:
                pass

    def check_notifications(self):
        now = datetime.now()
        minutes = now.strftime("%H:%M")

        # Meridian notifications
        if self.settings.get("notify_enabled", False):
            days = set(self.settings.get("notify_days", []))
            weekday = (now.weekday())  # 0 Monday
            if weekday in days and minutes == self.settings.get("notify_time", "09:00"):
                self._notify_meridian()

        # MKL notifications
        if self.settings.get("mkl_notify_enabled", False):
            if minutes == self.settings.get("mkl_notify_time", "09:00"):
                self._notify_mkl()

    def _play_sound(self):
        if not IS_WINDOWS or not self.settings.get("notify_sound_enabled", True):
            QApplication.beep()
            return
        if winsound is None:
            QApplication.beep()
            return
        mode = self.settings.get("notify_sound_mode", "alias")
        try:
            if mode == "alias":
                alias = self.settings.get("notify_sound_alias", "SystemAsterisk")
                winsound.PlaySound(alias, winsound.SND_ALIAS | winsound.SND_ASYNC)
            else:
                file = self.settings.get("notify_sound_file", "")
                if file and os.path.exists(file):
                    winsound.PlaySound(file, winsound.SND_FILENAME | winsound.SND_ASYNC)
                else:
                    winsound.MessageBeep()
        except Exception:
            # ignore sound errors
            pass

    def _notify_meridian(self):
        cur = self.conn.cursor()
        cur.execute("SELECT id,title,status,date FROM meridian_orders WHERE status='Не заказан' ORDER BY id DESC;")
        rows = cur.fetchall()
        if not rows:
            return

        # Snooze check
        cur.execute("SELECT value FROM notify_state WHERE key='meridian_snooze_until';")
        r = cur.fetchone()
        if r:
            try:
                until = datetime.fromisoformat(r[0])
                if datetime.now() < until:
                    return
            except Exception:
                pass

        self._play_sound()
        dlg = NotifyDialog(self, "Уведомления «Меридиан»",
                           [(title, f"{status} • {date}") for _, title, status, date in rows],
                           {
                               "Отложить 15 мин": lambda: self._snooze("meridian_snooze_until", 15),
                               "Отложить 30 мин": lambda: self._snooze("meridian_snooze_until", 30),
                               "Отметить \"Заказан\"": self._mark_meridian_ordered
                           })
        dlg.exec()

    def _notify_mkl(self):
        cur = self.conn.cursor()
        # aged pending
        after_days = int(self.settings.get("mkl_notify_after_days", 3))
        cutoff = (datetime.now() - timedelta(days=after_days)).strftime("%Y-%m-%d %H:%M")
        cur.execute("""
            SELECT id,fio,product,status,date FROM mkl_orders
            WHERE status='Не заказан' AND date <= ?
            ORDER BY id DESC;
        """, (cutoff,))
        rows = cur.fetchall()
        if not rows:
            return

        cur.execute("SELECT value FROM notify_state WHERE key='mkl_snooze_until';")
        r = cur.fetchone()
        if r:
            try:
                until = datetime.fromisoformat(r[0])
                if datetime.now() < until:
                    return
            except Exception:
                pass

        self._play_sound()
        dlg = NotifyDialog(self, "Уведомления «МКЛ»",
                           [(fio, f"{status} • {date}") for _, fio, product, status, date in rows],
                           {
                               "Отложить 1 день": lambda: self._snooze("mkl_snooze_until", 60 * 24),
                               "Отложить 3 дня": lambda: self._snooze("mkl_snooze_until", 60 * 24 * 3),
                               "Отметить \"Заказан\"": self._mark_mkl_ordered
                           })
        dlg.exec()

    def _snooze(self, key: str, minutes: int):
        until = (datetime.now() + timedelta(minutes=minutes)).isoformat(timespec="minutes")
        cur = self.conn.cursor()
        cur.execute("INSERT INTO notify_state (key,value) VALUES (?,?) ON CONFLICT(key) DO UPDATE SET value=excluded.value;", (key, until))
        self.conn.commit()

    def _mark_meridian_ordered(self):
        cur = self.conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        cur.execute("UPDATE meridian_orders SET status='Заказан', date=? WHERE status='Не заказан';", (now,))
        self.conn.commit()

    def _mark_mkl_ordered(self):
        cur = self.conn.cursor()
        now = datetime.now().strftime("%Y-%m-%d %H:%M")
        cur.execute("UPDATE mkl_orders SET status='Заказан', date=? WHERE status='Не заказан';", (now,))
        self.conn.commit()

    def test_mkl_notify(self):
        # Force add example aged order if none
        cur = self.conn.cursor()
        cur.execute("SELECT COUNT(1) FROM mkl_orders WHERE status='Не заказан';")
        if cur.fetchone()[0] == 0:
            past = (datetime.now() - timedelta(days=max(1, int(self.settings.get("mkl_notify_after_days", 3))))).strftime("%Y-%m-%d %H:%M")
            cur.execute("""
                INSERT INTO mkl_orders (fio,phone,product,sph,cyl,ax,bc,qty,status,date,comment)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """, ("Иванов Иван", "89991234567", "Test Product", "−1.25", None, None, None, 1, "Не заказан", past, ""))
            self.conn.commit()
        self._notify_mkl()

    def closeEvent(self, event: QCloseEvent):
        if self.settings.get("minimize_to_tray", True) and self.settings.get("tray_enabled", True):
            self.hide()
            self.start_tray()
            event.ignore()
        else:
            super().closeEvent(event)

    def changeEvent(self, event: QEvent):
        if event.type() == QEvent.WindowStateChange:
            if self.isMinimized() and self.settings.get("minimize_to_tray", True) and self.settings.get("tray_enabled", True):
                self.hide()
                self.start_tray()


def main():
    app = QApplication(sys.argv)

    # Modern palette
    QApplication.setStyle("Fusion")
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor("#0f172a"))  # slate-900
    palette.setColor(QPalette.WindowText, QColor("#e2e8f0"))
    palette.setColor(QPalette.Base, QColor("#111827"))
    palette.setColor(QPalette.AlternateBase, QColor("#1f2937"))
    palette.setColor(QPalette.ToolTipBase, QColor("#111827"))
    palette.setColor(QPalette.ToolTipText, QColor("#e2e8f0"))
    palette.setColor(QPalette.Text, QColor("#e2e8f0"))
    palette.setColor(QPalette.Button, QColor("#1f2937"))
    palette.setColor(QPalette.ButtonText, QColor("#e2e8f0"))
    palette.setColor(QPalette.Highlight, QColor("#3b82f6"))
    palette.setColor(QPalette.HighlightedText, QColor("#0b0f1a"))
    app.setPalette(palette)

    w = MainWindow()
    w.setWindowIcon(QIcon())  # placeholder

    sys.exit(app.exec())


if __name__ == "__main__":
    main()