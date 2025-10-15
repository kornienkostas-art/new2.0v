import React, { useEffect, useState } from "react";
import { Button, makeStyles, shorthands, Text } from "@fluentui/react-components";
import { appWindow } from "@tauri-apps/api/window";
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
    width: "620px",
    margin: "0 auto",
    marginTop: "24px"
  },
});

type Screen = "menu" | "mkl" | "meridian" | "clients" | "products_mkl" | "products_meridian" | "settings";

export default function App() {
  const s = useStyles();
  const [screen, setScreen] = useState<Screen>("menu");

  useEffect(() => {
    // При первом запуске — максимизация окна (Windows)
    invoke("maximize_on_start").catch(() => {});
  }, []);

  const BackButton = () => (
    <div style={{ display: "flex", justifyContent: "flex-start", width: "620px", margin: "0 auto", marginTop: "18px" }}>
      <Button appearance="primary" size="large" className={s.bigButton} onClick={() => setScreen("menu")}>
        ← Назад
      </Button>
    </div>
  );

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

  const Placeholder = (title: string, subtitle: string) => (
    <div className={s.root}>
      <div className={s.header}>
        <Text className={s.title}>{title}</Text>
      </div>
      <BackButton />
      <div className={s.card}>
        <Text>{subtitle}</Text>
        <div style={{ marginTop: 12, color: "#374151" }}>
          Экран будет содержать таблицу, контекстное меню, формы и цветовые метки статусов — согласно ТЗ.
        </div>
      </div>
    </div>
  );

  if (screen === "menu") return <Menu />;
  if (screen === "mkl") return Placeholder("Заказ МКЛ • Таблица данных", "Поля: ФИО, Телефон, Товар, Sph, Cyl, Ax, BC, Количество, Статус, Дата, Комментарий");
  if (screen === "meridian") return Placeholder("Заказ Меридиан • Список заказов", "Каждый заказ может содержать несколько позиций товара");
  if (screen === "clients") return Placeholder("Клиенты", "Поиск, добавление, редактирование, удаление");
  if (screen === "products_mkl") return Placeholder("Товары (МКЛ)", "Добавить/редактировать/удалить");
  if (screen === "products_meridian") return Placeholder("Товары (Меридиан)", "Добавить/редактировать/удалить");
  if (screen === "settings") return Placeholder("Настройки", "Масштаб, шрифт, трей, автозапуск, уведомления и звук");

  return null;
}