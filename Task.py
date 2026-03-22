import json
import os
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox

FILE_NAME = "tasks.json"
DATE_FORMAT = "%d-%m-%Y"
CATEGORIES = ["Работа", "Личное", "Учёба"]
PRIORITIES = ["Высокий", "Средний", "Низкий"]

THEMES = {
    "dark": {
        "bg": "#1e1e1e",
        "panel": "#252525",
        "card": "#2a2a2a",
        "card_hover": "#333333",
        "card_selected": "#3a3a3a",
        "text": "#ffffff",
        "muted": "#bbbbbb",
        "input": "#2f2f2f",
        "button": "#3a3a3a",
        "button_active": "#4a4a4a",
        "stats": "#242424",
    },
    "light": {
        "bg": "#f3f4f6",
        "panel": "#ffffff",
        "card": "#ffffff",
        "card_hover": "#f0f3f7",
        "card_selected": "#e6eefc",
        "text": "#1f2937",
        "muted": "#6b7280",
        "input": "#ffffff",
        "button": "#e5e7eb",
        "button_active": "#d1d5db",
        "stats": "#e5e7eb",
    },
}

PRIORITY_COLORS = {
    "Высокий": "#e53935",
    "Средний": "#fbc02d",
    "Низкий": "#43a047",
}


tasks = []
selected_task_index = None
current_filter = "all"
theme_name = "dark"


# ===== Данные =====
def normalize_task(raw_task):
    category = raw_task.get("category", "Личное")
    priority = raw_task.get("priority", "Средний")
    return {
        "text": str(raw_task.get("text", "")).strip(),
        "done": bool(raw_task.get("done", False)),
        "deadline": str(raw_task.get("deadline", "без срока")).strip() or "без срока",
        "category": category if category in CATEGORIES else "Личное",
        "priority": priority if priority in PRIORITIES else "Средний",
    }


def parse_deadline(deadline_text):
    if not deadline_text or deadline_text.lower() == "без срока":
        return None
    try:
        return datetime.strptime(deadline_text, DATE_FORMAT).date()
    except ValueError:
        return None


def is_overdue(task):
    due_date = parse_deadline(task["deadline"])
    return due_date is not None and (not task["done"]) and due_date < datetime.now().date()


def load_tasks(filename=FILE_NAME):
    global tasks
    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            if not isinstance(loaded, list):
                loaded = []
            tasks = [normalize_task(item) for item in loaded if isinstance(item, dict)]
        except Exception:
            tasks = []
    else:
        tasks = []

    refresh_ui()
    show_startup_notifications()


def save_tasks(filename=FILE_NAME):
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(tasks, f, ensure_ascii=False, indent=4)
    except Exception as error:
        messagebox.showerror("Ошибка", f"Не удалось сохранить задачи:\n{error}")


# ===== Фильтр/поиск =====
def get_visible_items():
    query = search_var.get().strip().lower()

    items = []
    for i, task in enumerate(tasks):
        if query and query not in task["text"].lower():
            continue
        if current_filter == "done" and not task["done"]:
            continue
        if current_filter == "todo" and task["done"]:
            continue
        items.append((i, task))

    items.sort(key=lambda item: (parse_deadline(item[1]["deadline"]) is None, parse_deadline(item[1]["deadline"]) or datetime.max.date()))
    return items


# ===== UI helpers =====
def set_filter(mode):
    global current_filter
    current_filter = mode
    refresh_ui()


def select_task(index):
    global selected_task_index
    if index < 0 or index >= len(tasks):
        return
    selected_task_index = index
    fill_form_from_task(tasks[index])
    refresh_ui()


def clear_selection_and_form():
    global selected_task_index
    selected_task_index = None
    task_entry.delete(0, tk.END)
    deadline_entry.delete(0, tk.END)
    deadline_entry.insert(0, "дд-мм-гггг или без срока")
    category_var.set("Личное")
    priority_var.set("Средний")
    add_btn.config(text="Добавить")


def fill_form_from_task(task):
    task_entry.delete(0, tk.END)
    task_entry.insert(0, task["text"])

    deadline_entry.delete(0, tk.END)
    deadline_entry.insert(0, task["deadline"])

    category_var.set(task["category"])
    priority_var.set(task["priority"])
    add_btn.config(text="Сохранить")


def add_or_update_task():
    text = task_entry.get().strip()
    deadline = deadline_entry.get().strip()
    category = category_var.get().strip()
    priority = priority_var.get().strip()

    if not text:
        messagebox.showwarning("Ошибка", "Введите задачу")
        return

    if deadline == "":
        deadline = "без срока"
    elif deadline.lower() != "без срока" and parse_deadline(deadline) is None:
        messagebox.showwarning("Ошибка", "Формат дедлайна: дд-мм-гггг или без срока")
        return

    if category not in CATEGORIES:
        category = "Личное"
    if priority not in PRIORITIES:
        priority = "Средний"

    task_payload = {
        "text": text,
        "done": False,
        "deadline": deadline,
        "category": category,
        "priority": priority,
    }

    global selected_task_index
    if selected_task_index is None:
        tasks.append(task_payload)
    else:
        task_payload["done"] = tasks[selected_task_index]["done"]
        tasks[selected_task_index] = task_payload

    save_tasks()
    clear_selection_and_form()
    refresh_ui()


def toggle_done(index):
    tasks[index]["done"] = not tasks[index]["done"]
    save_tasks()
    refresh_ui()


def delete_task(index):
    global selected_task_index
    tasks.pop(index)
    selected_task_index = None
    clear_selection_and_form()
    save_tasks()
    refresh_ui()


def show_startup_notifications():
    overdue = sum(1 for t in tasks if is_overdue(t))
    if overdue > 0:
        messagebox.showwarning("Просроченные", f"Просроченных задач: {overdue}")

    today = datetime.now().date()
    reminders = [t for t in tasks if not t["done"] and parse_deadline(t["deadline"]) == today]
    if reminders:
        messagebox.showinfo("Напоминание", f"На сегодня задач: {len(reminders)}")


def export_tasks():
    file_path = filedialog.asksaveasfilename(
        title="Экспорт задач",
        defaultextension=".json",
        filetypes=[("JSON files", "*.json")],
    )
    if not file_path:
        return
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(tasks, f, ensure_ascii=False, indent=4)
        messagebox.showinfo("Успех", "Задачи экспортированы")
    except Exception as error:
        messagebox.showerror("Ошибка", f"Ошибка экспорта:\n{error}")


def import_tasks():
    global tasks
    file_path = filedialog.askopenfilename(
        title="Импорт задач",
        filetypes=[("JSON files", "*.json")],
    )
    if not file_path:
        return
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        if not isinstance(loaded, list):
            raise ValueError("Ожидается JSON-массив задач")
        tasks = [normalize_task(item) for item in loaded if isinstance(item, dict)]
        save_tasks()
        clear_selection_and_form()
        refresh_ui()
    except Exception as error:
        messagebox.showerror("Ошибка", f"Ошибка импорта:\n{error}")


def update_stats():
    total = len(tasks)
    done = sum(1 for t in tasks if t["done"])
    overdue = sum(1 for t in tasks if is_overdue(t))
    percent = int((done / total) * 100) if total else 0
    stats_var.set(f"Всего: {total} | Выполнено: {done} | {percent}% | Просрочено: {overdue}")


def clear_cards():
    for widget in cards_inner.winfo_children():
        widget.destroy()


def create_task_card(parent, index, task):
    colors = THEMES[theme_name]
    card_bg = colors["card_selected"] if index == selected_task_index else colors["card"]
    if is_overdue(task):
        title_color = "#ff4d4d"
    else:
        title_color = colors["text"]

    card = tk.Frame(parent, bg=card_bg, bd=0, highlightthickness=1, highlightbackground=colors["button"])
    card.grid_columnconfigure(1, weight=1)

    check_text = "✅" if task["done"] else "⬜"
    check_btn = tk.Button(
        card,
        text=check_text,
        width=3,
        bg=card_bg,
        fg=colors["text"],
        activebackground=colors["button_active"],
        relief="flat",
        command=lambda idx=index: toggle_done(idx),
        cursor="hand2",
    )
    check_btn.grid(row=0, column=0, rowspan=2, padx=(8, 6), pady=8, sticky="n")

    title = tk.Label(
        card,
        text=task["text"],
        bg=card_bg,
        fg=title_color,
        font=("Segoe UI", 11, "bold"),
        anchor="w",
    )
    title.grid(row=0, column=1, sticky="ew", pady=(8, 2))

    meta = tk.Label(
        card,
        text=f"{task['category']} | {task['deadline']} | {task['priority']}",
        bg=card_bg,
        fg=PRIORITY_COLORS.get(task["priority"], colors["muted"]),
        font=("Segoe UI", 9),
        anchor="w",
    )
    meta.grid(row=1, column=1, sticky="w", pady=(0, 8))

    done_btn = tk.Button(
        card,
        text="✔",
        width=3,
        bg=colors["button"],
        fg=colors["text"],
        activebackground=colors["button_active"],
        relief="flat",
        command=lambda idx=index: toggle_done(idx),
        cursor="hand2",
    )
    done_btn.grid(row=0, column=2, padx=4, pady=(8, 2))

    del_btn = tk.Button(
        card,
        text="✖",
        width=3,
        bg=colors["button"],
        fg="#ff6b6b",
        activebackground=colors["button_active"],
        relief="flat",
        command=lambda idx=index: delete_task(idx),
        cursor="hand2",
    )
    del_btn.grid(row=1, column=2, padx=4, pady=(0, 8))

    def on_enter(_):
        if index != selected_task_index:
            card.configure(bg=colors["card_hover"])
            title.configure(bg=colors["card_hover"])
            meta.configure(bg=colors["card_hover"])
            check_btn.configure(bg=colors["card_hover"])

    def on_leave(_):
        if index != selected_task_index:
            card.configure(bg=colors["card"])
            title.configure(bg=colors["card"])
            meta.configure(bg=colors["card"])
            check_btn.configure(bg=colors["card"])

    def on_click(_):
        select_task(index)

    for widget in (card, title, meta):
        widget.bind("<Button-1>", on_click)
        widget.bind("<Enter>", on_enter)
        widget.bind("<Leave>", on_leave)

    return card


def refresh_cards():
    clear_cards()
    visible = get_visible_items()

    for row, (index, task) in enumerate(visible):
        card = create_task_card(cards_inner, index, task)
        card.grid(row=row, column=0, sticky="ew", padx=8, pady=6)

    cards_inner.grid_columnconfigure(0, weight=1)
    cards_canvas.configure(scrollregion=cards_canvas.bbox("all"))


def refresh_ui(*_):
    refresh_cards()
    update_stats()
    update_theme_widgets()


def toggle_theme():
    global theme_name
    theme_name = "light" if theme_name == "dark" else "dark"
    refresh_ui()


def create_placeholder(entry, text):
    entry.insert(0, text)
    entry._placeholder = text

    def on_focus_in(_):
        if entry.get() == entry._placeholder:
            entry.delete(0, tk.END)

    def on_focus_out(_):
        if not entry.get().strip():
            entry.delete(0, tk.END)
            entry.insert(0, entry._placeholder)

    entry.bind("<FocusIn>", on_focus_in)
    entry.bind("<FocusOut>", on_focus_out)


def update_theme_widgets():
    colors = THEMES[theme_name]

    root.configure(bg=colors["bg"])
    sidebar.configure(bg=colors["panel"])
    content.configure(bg=colors["bg"])
    top_panel.configure(bg=colors["bg"])
    cards_wrap.configure(bg=colors["bg"])
    cards_inner.configure(bg=colors["bg"])
    bottom_panel.configure(bg=colors["stats"])
    title_label.configure(bg=colors["panel"], fg=colors["text"])

    for btn in sidebar_buttons:
        btn.configure(bg=colors["button"], fg=colors["text"], activebackground=colors["button_active"])

    for lbl in form_labels:
        lbl.configure(bg=colors["bg"], fg=colors["text"])

    for entry in [task_entry, deadline_entry, search_entry]:
        entry.configure(bg=colors["input"], fg=colors["text"], insertbackground=colors["text"], relief="flat")

    for btn in top_buttons:
        btn.configure(bg=colors["button"], fg=colors["text"], activebackground=colors["button_active"], relief="flat")

    stats_label.configure(bg=colors["stats"], fg=colors["text"])
    cards_canvas.configure(bg=colors["bg"], highlightthickness=0)


# ===== UI =====
root = tk.Tk()
root.title("Task Manager")
root.geometry("1100x700")
root.minsize(900, 600)
root.grid_rowconfigure(0, weight=1)
root.grid_columnconfigure(1, weight=1)

# Sidebar
sidebar = tk.Frame(root, width=200)
sidebar.grid(row=0, column=0, sticky="ns")
sidebar.grid_propagate(False)
sidebar.grid_rowconfigure(6, weight=1)

title_label = tk.Label(sidebar, text="Task Manager", font=("Segoe UI", 16, "bold"))
title_label.grid(row=0, column=0, padx=16, pady=(16, 20), sticky="w")

btn_all = tk.Button(sidebar, text="Все задачи", command=lambda: set_filter("all"), cursor="hand2", padx=10, pady=10)
btn_done = tk.Button(sidebar, text="Выполненные", command=lambda: set_filter("done"), cursor="hand2", padx=10, pady=10)
btn_todo = tk.Button(sidebar, text="Невыполненные", command=lambda: set_filter("todo"), cursor="hand2", padx=10, pady=10)
btn_theme = tk.Button(sidebar, text="🌙 Тема", command=toggle_theme, cursor="hand2", padx=10, pady=10)
btn_import = tk.Button(sidebar, text="Импорт", command=import_tasks, cursor="hand2", padx=10, pady=10)
btn_export = tk.Button(sidebar, text="Экспорт", command=export_tasks, cursor="hand2", padx=10, pady=10)

sidebar_buttons = [btn_all, btn_done, btn_todo, btn_theme, btn_import, btn_export]
for i, btn in enumerate(sidebar_buttons, start=1):
    btn.grid(row=i, column=0, padx=12, pady=6, sticky="ew")

# Main content
content = tk.Frame(root)
content.grid(row=0, column=1, sticky="nsew")
content.grid_rowconfigure(1, weight=1)
content.grid_columnconfigure(0, weight=1)

# Top input panel
top_panel = tk.Frame(content)
top_panel.grid(row=0, column=0, sticky="ew", padx=14, pady=12)
top_panel.grid_columnconfigure(0, weight=5)
top_panel.grid_columnconfigure(1, weight=2)
top_panel.grid_columnconfigure(2, weight=2)
top_panel.grid_columnconfigure(3, weight=2)
top_panel.grid_columnconfigure(4, weight=1)
top_panel.grid_columnconfigure(5, weight=2)

label_task = tk.Label(top_panel, text="Задача")
label_deadline = tk.Label(top_panel, text="Дедлайн")
label_category = tk.Label(top_panel, text="Категория")
label_priority = tk.Label(top_panel, text="Приоритет")
label_search = tk.Label(top_panel, text="Поиск")
form_labels = [label_task, label_deadline, label_category, label_priority, label_search]

label_task.grid(row=0, column=0, sticky="w", padx=5)
label_deadline.grid(row=0, column=1, sticky="w", padx=5)
label_category.grid(row=0, column=2, sticky="w", padx=5)
label_priority.grid(row=0, column=3, sticky="w", padx=5)
label_search.grid(row=0, column=5, sticky="w", padx=5)

task_entry = tk.Entry(top_panel, font=("Segoe UI", 10))
deadline_entry = tk.Entry(top_panel, font=("Segoe UI", 10))
category_var = tk.StringVar(value="Личное")
priority_var = tk.StringVar(value="Средний")

category_menu = tk.OptionMenu(top_panel, category_var, *CATEGORIES)
priority_menu = tk.OptionMenu(top_panel, priority_var, *PRIORITIES)

add_btn = tk.Button(top_panel, text="Добавить", command=add_or_update_task, cursor="hand2", padx=12, pady=8)

search_var = tk.StringVar()
search_entry = tk.Entry(top_panel, textvariable=search_var, font=("Segoe UI", 10))

task_entry.grid(row=1, column=0, sticky="ew", padx=5)
deadline_entry.grid(row=1, column=1, sticky="ew", padx=5)
category_menu.grid(row=1, column=2, sticky="ew", padx=5)
priority_menu.grid(row=1, column=3, sticky="ew", padx=5)
add_btn.grid(row=1, column=4, sticky="ew", padx=5)
search_entry.grid(row=1, column=5, sticky="ew", padx=5)
top_buttons = [add_btn]

# Cards area (scrollable)
cards_wrap = tk.Frame(content)
cards_wrap.grid(row=1, column=0, sticky="nsew", padx=8, pady=(0, 8))
cards_wrap.grid_rowconfigure(0, weight=1)
cards_wrap.grid_columnconfigure(0, weight=1)

cards_canvas = tk.Canvas(cards_wrap)
scrollbar = tk.Scrollbar(cards_wrap, orient="vertical", command=cards_canvas.yview)
cards_inner = tk.Frame(cards_canvas)

cards_inner.bind(
    "<Configure>",
    lambda _e: cards_canvas.configure(scrollregion=cards_canvas.bbox("all")),
)

window_id = cards_canvas.create_window((0, 0), window=cards_inner, anchor="nw")

cards_canvas.configure(yscrollcommand=scrollbar.set)
cards_canvas.grid(row=0, column=0, sticky="nsew")
scrollbar.grid(row=0, column=1, sticky="ns")


def sync_inner_width(event):
    cards_canvas.itemconfig(window_id, width=event.width)


cards_canvas.bind("<Configure>", sync_inner_width)

# Bottom stats
bottom_panel = tk.Frame(content)
bottom_panel.grid(row=2, column=0, sticky="ew", padx=14, pady=(0, 12))
stats_var = tk.StringVar(value="Всего: 0 | Выполнено: 0 | 0% | Просрочено: 0")
stats_label = tk.Label(bottom_panel, textvariable=stats_var, font=("Segoe UI", 10, "bold"), anchor="w", padx=10, pady=8)
stats_label.grid(row=0, column=0, sticky="ew")
bottom_panel.grid_columnconfigure(0, weight=1)

# Placeholder text
create_placeholder(task_entry, "Введите задачу...")
create_placeholder(deadline_entry, "дд-мм-гггг или без срока")
create_placeholder(search_entry, "Поиск по тексту...")

# Реакция на поиск
search_var.trace_add("write", refresh_ui)

load_tasks()
update_theme_widgets()
root.mainloop()
