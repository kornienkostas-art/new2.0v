import React, { useEffect, useState } from "react";
import { Button, makeStyles, shorthands, Text } from "@fluentui/react-components";
import { invoke } from "@tauri-apps/api";
import { SystemRegular } from "@fluentui/react-icons";

const useStyles = makeStyles({
  root: {
    height: "100vh",
    display: "flex",
    flexDirection: "column",
    backgroundColor: "#f7f7f7"
  },
  header: {
    display: "flex",
    alignItems: "center",
    justifyContent: "center",
    paddingTop: "24px"
  },
  title: {
    fontWeight: 700,
    fontSize: "22px"
  },
  menu: {
    display: "flex",
    flexDirection: "column",
    alignItems: "center",
    gap: "14px",
    marginTop: "32px"
  },
  bigButton: {
    width: "360px",
    height: "56px",
    fontWeight: 700,
    fontSize: "18px"
  },
  footer: {
    marginTop: "auto",
    paddingBottom: "24px",
    display: "flex",
    justifyContent: "center",
    color: "#6b7280"
  },
  card: {
    backgroundColor: "white",
    ...shorthands.borderRadius("10px"),
    ...shorthands.padding("24px"),
    boxShadow: "0 6px 20px rgba(0,0,0,0.08)",
    width: "900px",
    margin: "0 auto",
    marginTop: "24px"
  },
});

type Screen = "menu" | "mkl" | "meridian" | "clients" | "products_mkl" | "products_meridian" | "settings";

export default function App() {
  const s = useStyles();
  const [screen, setScreen] = useState<Screen>("menu");

  useEffect(() => {
    invoke("maximize_on_start").catch(() => {});
  }, []);

  const Menu = () => (
    <div className={s.root}>
      <div className={s.header}>
        <Text className={s.title}>УссурОчки.рф — Заказ линз</Text>
      </div>
      <div className={s.menu}>
        <Button appearance="primary" size="large" className={s.bigButton} onClick={() => setScreen("mkl")}>
          Заказы МКЛ
        </Button>
        <Button appearance="primary" size="large" className={s.bigButton} onClick={() => setScreen("meridian")}>
          Заказы Меридиан
        </Button>
        <Button appearance="secondary" size="large" className={s.bigButton} onClick={() => setScreen("settings")}>
          Настройки…
        </Button>
      </div>
      <div className={s.card}>
        <Text>Пояснение</Text>
        <div style={{ marginTop: 12, color: "#374151" }}>
          Крупные кнопки основных действий, последующая реализация таблиц, экспорта, уведомлений и трея — в следующих коммитах. Интерфейс масштабируемый, шрифт регулируется из «Настройки».
        </div>
      </div>
      <div className={s.footer}>
        <SystemRegular />
        <span style={{ marginLeft: 8 }}>Tauri (Rust) + React + Fluent UI</span>
      </div>
    </div>
  );

  if (screen === "menu") return <Menu />;

  if (screen === "mkl") {
    return <MklScreen onBack={() => setScreen("menu")} />;
  }

  if (screen === "meridian") return <Placeholder title="Заказ Меридиан • Список заказов" subtitle="Каждый заказ может содержать несколько позиций товара" />;
  if (screen === "clients") return <Placeholder title="Клиенты" subtitle="Поиск, добавление, редактирование, удаление" />;
  if (screen === "products_mkl") return <Placeholder title="Товары (МКЛ)" subtitle="Добавить/редактировать/удалить" />;
  if (screen === "products_meridian") return <Placeholder title="Товары (Меридиан)" subtitle="Добавить/редактировать/удалить" />;
  if (screen === "settings") return <Placeholder title="Настройки" subtitle="Масштаб, шрифт, трей, автозапуск, уведомления и звук" />;

  return null;
}

function Placeholder({ title, subtitle }: { title: string; subtitle: string }) {
  const s = useStyles();
  return (
    <div className={s.root}>
      <div className={s.header}>
        <Text className={s.title}>{title}</Text>
      </div>
      <div className={s.card}>
        <Text>{subtitle}</Text>
      </div>
    </div>
  );
}

type MklOrder = {
  id: number;
  fio: string;
  phone: string;
  product: string;
  sph?: string | null;
  cyl?: string | null;
  ax?: number | null;
  bc?: number | null;
  qty: number;
  status: "Не заказан" | "Заказан" | "Прозвонен" | "Вручен" | string;
  date: string;
  comment: string;
};

function formatPhoneMask(raw: string): string {
  const digits = raw.replace(/\D/g, "");
  if (digits.length >= 11) {
    const first = digits[0];
    const ten = digits.slice(-10);
    const format8 = (n: string) => `8-${n.slice(0,3)}-${n.slice(3,6)}-${n.slice(6,8)}-${n.slice(8,10)}`;
    if (first === "7") return `+7-${digits.slice(1,4)}-${digits.slice(4,7)}-${digits.slice(7,9)}-${digits.slice(9,11)}`;
    if (first === "8") return format8(digits.slice(1,11));
    return format8(ten);
  } else if (digits.length === 10) {
    return `8-${digits.slice(0,3)}-${digits.slice(3,6)}-${digits.slice(6,8)}-${digits.slice(8,10)}`;
  }
  return raw.trim();
}

function statusStyle(status: string): React.CSSProperties {
  switch (status) {
    case "Не заказан":
      return { backgroundColor: "#fee2e2", color: "#7f1d1d" };
    case "Заказан":
      return { backgroundColor: "#fef3c7", color: "#7c2d12" };
    case "Прозвонен":
      return { backgroundColor: "#dbeafe", color: "#1e3a8a" };
    case "Вручен":
      return { backgroundColor: "#dcfce7", color: "#065f46" };
    default:
      return {};
  }
}

function MklScreen({ onBack }: { onBack: () => void }) {
  const s = useStyles();
  const [rows, setRows] = useState<MklOrder[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    invoke<MklOrder[]>("mkl_orders")
      .then((data) => setRows(data))
      .catch(() => setRows([]))
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className={s.root}>
      <div className={s.header}>
        <Text className={s.title}>Заказ МКЛ • Таблица данных</Text>
      </div>
      <div style={{ display: "flex", justifyContent: "flex-start", width: "900px", margin: "0 auto", marginTop: "18px", gap: 12 }}>
        <Button appearance="primary" size="large" onClick={onBack} style={{ fontWeight: 700 }}>← Главное меню</Button>
        <Button appearance="primary">Новый заказ</Button>
        <Button appearance="secondary">Редактировать</Button>
        <Button appearance="secondary">Удалить</Button>
        <Button appearance="secondary">Сменить статус</Button>
        <Button appearance="secondary">Клиенты</Button>
        <Button appearance="secondary">Товары</Button>
        <Button appearance="secondary">Экспорт TXT</Button>
      </div>

      <div className={s.card}>
        <div style={{ fontWeight: 600, marginBottom: 12 }}>Поля: ФИО, Телефон, Товар, Sph, Cyl, Ax, BC, Количество, Статус, Дата, Комментарий</div>
        {loading ? (
          <div>Загрузка…</div>
        ) : rows.length === 0 ? (
          <div>Нет записей</div>
        ) : (
          <table style={{ width: "100%", borderCollapse: "collapse" }}>
            <thead>
              <tr style={{ textAlign: "left", borderBottom: "1px solid #e5e7eb" }}>
                <th>ФИО</th>
                <th>Телефон</th>
                <th>Товар</th>
                <th>Sph</th>
                <th>Cyl</th>
                <th>Ax</th>
                <th>BC</th>
                <th>Количество</th>
                <th>Статус</th>
                <th>Дата</th>
                <th>Комментарий</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((r) => (
                <tr key={r.id} style={{ ...statusStyle(r.status) }}>
                  <td style={{ padding: "8px 6px" }}>{r.fio}</td>
                  <td style={{ padding: "8px 6px" }}>{formatPhoneMask(r.phone)}</td>
                  <td style={{ padding: "8px 6px" }}>{r.product}</td>
                  <td style={{ padding: "8px 6px" }}>{r.sph ?? ""}</td>
                  <td style={{ padding: "8px 6px" }}>{r.cyl ?? ""}</td>
                  <td style={{ padding: "8px 6px" }}>{r.ax ?? ""}</td>
                  <td style={{ padding: "8px 6px" }}>{r.bc ?? ""}</td>
                  <td style={{ padding: "8px 6px" }}>{r.qty}</td>
                  <td style={{ padding: "8px 6px" }}>{r.status}</td>
                  <td style={{ padding: "8px 6px" }}>{r.date}</td>
                  <td style={{ padding: "8px 6px" }}>{r.comment && r.comment.trim() !== "" ? "ЕСТЬ" : "НЕТ"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
      <div className={s.footer}>
        <SystemRegular />
        <span style={{ marginLeft: 8 }}>Tauri (Rust) + React + Fluent UI</span>
      </div>
    </div>
  );
}