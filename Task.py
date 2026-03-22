import json
import os
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, ttk

FILE_NAME = "tasks.json"
DATE_FORMAT = "%d-%m-%Y"
CATEGORIES = ["Работа", "Личное", "Учёба"]
PRIORITIES = ["Высокий", "Средний", "Низкий"]

THEMES = {
    "light": {
        "bg": "#f5f5f5",
        "fg": "#1e1e1e",
        "input_bg": "#ffffff",
        "button_bg": "#e7e7e7",
        "select_bg": "#d9d9d9",
    },
    "dark": {
        "bg": "#1f1f1f",
        "fg": "#f0f0f0",
        "input_bg": "#2d2d2d",
        "button_bg": "#3a3a3a",
        "select_bg": "#505050",
    },
}

tasks = []
displayed_indices = []
editing_task_index = None
theme_name = "light"


def normalize_task(raw_task):
    """Нормализует задачу из JSON к ожидаемой структуре."""
    return {
        "text": str(raw_task.get("text", "")).strip(),
        "done": bool(raw_task.get("done", False)),
        "deadline": str(raw_task.get("deadline", "без срока")).strip() or "без срока",
        "category": raw_task.get("category", CATEGORIES[1])
        if raw_task.get("category", CATEGORIES[1]) in CATEGORIES
        else CATEGORIES[1],
        "priority": raw_task.get("priority", "Средний")
        if raw_task.get("priority", "Средний") in PRIORITIES
        else "Средний",
    }


def parse_deadline(deadline_text):
    if not deadline_text or deadline_text.lower() == "без срока":
        return None
    try:
        return datetime.strptime(deadline_text, DATE_FORMAT).date()
    except ValueError:
        return None


def is_overdue(task):
    date_value = parse_deadline(task["deadline"])
    if date_value is None:
        return False
    return (not task["done"]) and date_value < datetime.now().date()


# ===== Работа с файлом =====
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
        messagebox.showerror("Ошибка сохранения", f"Не удалось сохранить задачи:\n{error}")


# ===== Фильтрация и сортировка =====
def get_filtered_sorted_items():
    query = search_var.get().strip().lower()
    status_filter = status_filter_var.get()
    category_filter = category_filter_var.get()
    sort_mode = sort_var.get()

    items = []
    for index, task in enumerate(tasks):
        if query and query not in task["text"].lower():
            continue
        if status_filter == "Выполненные" and not task["done"]:
            continue
        if status_filter == "Невыполненные" and task["done"]:
            continue
        if category_filter != "Все категории" and task["category"] != category_filter:
            continue
        items.append((index, task))

    if sort_mode == "По дедлайну":
        def deadline_sort_key(item):
            task = item[1]
            date_value = parse_deadline(task["deadline"])
            if date_value is None:
                return (1, datetime.max.date())
            return (0, date_value)

        items.sort(key=deadline_sort_key)
    elif sort_mode == "По статусу":
        items.sort(key=lambda item: item[1]["done"])

    return items


# ===== UI логика =====
def update_listbox():
    global displayed_indices
    listbox.delete(0, tk.END)

    filtered_items = get_filtered_sorted_items()
    displayed_indices = [index for index, _ in filtered_items]

    for _, task in filtered_items:
        status = "✅" if task["done"] else "❌"
        text = (
            f"{status} [{task['category']}] {task['text']} "
            f"(до: {task['deadline']}, приоритет: {task['priority']})"
        )
        listbox.insert(tk.END, text)

    apply_listbox_colors(filtered_items)


def apply_listbox_colors(filtered_items):
    for i, (_, task) in enumerate(filtered_items):
        fg_color = priority_color(task["priority"])
        if is_overdue(task):
            fg_color = "#ff4d4d"
        listbox.itemconfig(i, foreground=fg_color)


def priority_color(priority):
    if priority == "Высокий":
        return "#e53935"
    if priority == "Средний":
        return "#fbc02d"
    return "#43a047"


def update_stats():
    total = len(tasks)
    done = sum(1 for t in tasks if t["done"])
    overdue = sum(1 for t in tasks if is_overdue(t))
    percent = int((done / total) * 100) if total else 0
    stats_var.set(
        f"Всего: {total} | Выполнено: {done} | Выполнение: {percent}% | Просрочено: {overdue}"
    )


def refresh_ui(*_):
    update_listbox()
    update_stats()


def show_startup_notifications():
    overdue_count = sum(1 for t in tasks if is_overdue(t))
    if overdue_count:
        messagebox.showwarning("Просроченные задачи", f"Просрочено задач: {overdue_count}")

    today = datetime.now().date()
    today_tasks = [
        t
        for t in tasks
        if (not t["done"]) and parse_deadline(t["deadline"]) == today
    ]
    if today_tasks:
        messagebox.showinfo("Напоминание", f"На сегодня задач: {len(today_tasks)}")


def get_selected_task_index():
    selected = listbox.curselection()
    if not selected:
        return None
    visible_index = selected[0]
    if visible_index >= len(displayed_indices):
        return None
    return displayed_indices[visible_index]


def add_or_update_task():
    global editing_task_index

    text = entry.get().strip()
    deadline = deadline_entry.get().strip()
    category = category_var.get().strip() or CATEGORIES[1]
    priority = priority_var.get().strip() or "Средний"

    if text == "":
        messagebox.showwarning("Ошибка", "Введите задачу")
        return

    if deadline == "":
        deadline = "без срока"
    elif deadline.lower() != "без срока" and parse_deadline(deadline) is None:
        messagebox.showwarning("Ошибка", "Дата должна быть в формате дд-мм-гггг или 'без срока'")
        return

    task_payload = {
        "text": text,
        "done": False,
        "deadline": deadline,
        "category": category if category in CATEGORIES else CATEGORIES[1],
        "priority": priority if priority in PRIORITIES else "Средний",
    }

    if editing_task_index is None:
        tasks.append(task_payload)
    else:
        current_done = tasks[editing_task_index]["done"]
        task_payload["done"] = current_done
        tasks[editing_task_index] = task_payload

    save_tasks()
    clear_input_fields()
    refresh_ui()


def delete_task():
    global editing_task_index
    index = get_selected_task_index()
    if index is None:
        return

    tasks.pop(index)
    editing_task_index = None
    add_update_btn.config(text="Добавить / Обновить")
    save_tasks()
    clear_input_fields()
    refresh_ui()


def toggle_done():
    index = get_selected_task_index()
    if index is None:
        return

    tasks[index]["done"] = not tasks[index]["done"]
    save_tasks()
    refresh_ui()


def on_task_select(_event=None):
    global editing_task_index
    index = get_selected_task_index()
    if index is None:
        return

    task = tasks[index]
    editing_task_index = index

    entry.delete(0, tk.END)
    entry.insert(0, task["text"])

    deadline_entry.delete(0, tk.END)
    deadline_entry.insert(0, task["deadline"])

    category_var.set(task["category"])
    priority_var.set(task["priority"])
    add_update_btn.config(text="Сохранить изменения")


def clear_input_fields():
    global editing_task_index
    editing_task_index = None
    entry.delete(0, tk.END)
    deadline_entry.delete(0, tk.END)
    deadline_entry.insert(0, "дд-мм-гггг или без срока")
    category_var.set(CATEGORIES[1])
    priority_var.set("Средний")
    add_update_btn.config(text="Добавить / Обновить")


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
        messagebox.showinfo("Экспорт", "Задачи успешно экспортированы")
    except Exception as error:
        messagebox.showerror("Ошибка", f"Не удалось экспортировать:\n{error}")


def import_tasks():
    file_path = filedialog.askopenfilename(
        title="Импорт задач",
        filetypes=[("JSON files", "*.json")],
    )
    if not file_path:
        return

    global tasks
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        if not isinstance(loaded, list):
            raise ValueError("Файл должен содержать список задач")
        tasks = [normalize_task(item) for item in loaded if isinstance(item, dict)]
        save_tasks()
        clear_input_fields()
        refresh_ui()
        show_startup_notifications()
        messagebox.showinfo("Импорт", "Задачи успешно импортированы")
    except Exception as error:
        messagebox.showerror("Ошибка", f"Не удалось импортировать:\n{error}")


def toggle_theme():
    global theme_name
    theme_name = "dark" if theme_name == "light" else "light"
    apply_theme()


def apply_theme():
    colors = THEMES[theme_name]

    root.configure(bg=colors["bg"])
    main_frame.configure(bg=colors["bg"])
    controls_frame.configure(bg=colors["bg"])
    filters_frame.configure(bg=colors["bg"])
    actions_frame.configure(bg=colors["bg"])

    for label in labels_for_theme:
        label.configure(bg=colors["bg"], fg=colors["fg"])

    for entry_widget in entries_for_theme:
        entry_widget.configure(bg=colors["input_bg"], fg=colors["fg"], insertbackground=colors["fg"])

    listbox.configure(
        bg=colors["input_bg"],
        fg=colors["fg"],
        selectbackground=colors["select_bg"],
        selectforeground=colors["fg"],
    )

    for button in buttons_for_theme:
        button.configure(bg=colors["button_bg"], fg=colors["fg"], activebackground=colors["select_bg"])


# ===== Окно =====
root = tk.Tk()
root.title("Менеджер задач")
root.geometry("780x720")
root.minsize(760, 680)

main_frame = tk.Frame(root)
main_frame.pack(fill="both", expand=True, padx=12, pady=12)

# Создание задачи
controls_frame = tk.Frame(main_frame)
controls_frame.pack(fill="x", pady=4)

tk.Label(controls_frame, text="Задача:").grid(row=0, column=0, sticky="w")
entry = tk.Entry(controls_frame, width=42)
entry.grid(row=1, column=0, padx=3, pady=3, sticky="w")

tk.Label(controls_frame, text="Дедлайн (дд-мм-гггг/без срока):").grid(row=0, column=1, sticky="w")
deadline_entry = tk.Entry(controls_frame, width=22)
deadline_entry.grid(row=1, column=1, padx=3, pady=3, sticky="w")
deadline_entry.insert(0, "дд-мм-гггг")

tk.Label(controls_frame, text="Категория:").grid(row=0, column=2, sticky="w")
category_var = tk.StringVar(value=CATEGORIES[1])
category_box = ttk.Combobox(controls_frame, textvariable=category_var, values=CATEGORIES, width=14, state="readonly")
category_box.grid(row=1, column=2, padx=3, pady=3)

tk.Label(controls_frame, text="Приоритет:").grid(row=0, column=3, sticky="w")
priority_var = tk.StringVar(value="Средний")
priority_box = ttk.Combobox(controls_frame, textvariable=priority_var, values=PRIORITIES, width=12, state="readonly")
priority_box.grid(row=1, column=3, padx=3, pady=3)

# Поиск/фильтры/сортировка
filters_frame = tk.Frame(main_frame)
filters_frame.pack(fill="x", pady=8)

tk.Label(filters_frame, text="Поиск:").grid(row=0, column=0, sticky="w")
search_var = tk.StringVar()
search_entry = tk.Entry(filters_frame, textvariable=search_var, width=30)
search_entry.grid(row=1, column=0, padx=3, pady=3, sticky="w")

tk.Label(filters_frame, text="Статус:").grid(row=0, column=1, sticky="w")
status_filter_var = tk.StringVar(value="Все")
status_box = ttk.Combobox(
    filters_frame,
    textvariable=status_filter_var,
    values=["Все", "Выполненные", "Невыполненные"],
    width=16,
    state="readonly",
)
status_box.grid(row=1, column=1, padx=3, pady=3)

tk.Label(filters_frame, text="Категория:").grid(row=0, column=2, sticky="w")
category_filter_var = tk.StringVar(value="Все категории")
category_filter_box = ttk.Combobox(
    filters_frame,
    textvariable=category_filter_var,
    values=["Все категории", *CATEGORIES],
    width=16,
    state="readonly",
)
category_filter_box.grid(row=1, column=2, padx=3, pady=3)

tk.Label(filters_frame, text="Сортировка:").grid(row=0, column=3, sticky="w")
sort_var = tk.StringVar(value="Без сортировки")
sort_box = ttk.Combobox(
    filters_frame,
    textvariable=sort_var,
    values=["Без сортировки", "По дедлайну", "По статусу"],
    width=16,
    state="readonly",
)
sort_box.grid(row=1, column=3, padx=3, pady=3)

# Кнопки
actions_frame = tk.Frame(main_frame)
actions_frame.pack(fill="x", pady=5)

add_update_btn = tk.Button(actions_frame, text="Добавить / Обновить", command=add_or_update_task)
add_update_btn.pack(side="left", padx=3)

tk.Button(actions_frame, text="Удалить", command=delete_task).pack(side="left", padx=3)
tk.Button(actions_frame, text="Выполнено / Не выполнено", command=toggle_done).pack(side="left", padx=3)
tk.Button(actions_frame, text="Очистить поля", command=clear_input_fields).pack(side="left", padx=3)
tk.Button(actions_frame, text="Импорт", command=import_tasks).pack(side="left", padx=3)
tk.Button(actions_frame, text="Экспорт", command=export_tasks).pack(side="left", padx=3)
tk.Button(actions_frame, text="Тема 🌙", command=toggle_theme).pack(side="right", padx=3)

# Список задач
listbox = tk.Listbox(main_frame, width=110, height=20)
listbox.pack(fill="both", expand=True, pady=8)
listbox.bind("<<ListboxSelect>>", on_task_select)

# Статистика
stats_var = tk.StringVar(value="Всего: 0 | Выполнено: 0 | Выполнение: 0% | Просрочено: 0")
stats_label = tk.Label(main_frame, textvariable=stats_var, anchor="w", font=("Arial", 10, "bold"))
stats_label.pack(fill="x", pady=6)

# Реакция UI на изменения фильтров
search_var.trace_add("write", refresh_ui)
status_filter_var.trace_add("write", refresh_ui)
category_filter_var.trace_add("write", refresh_ui)
sort_var.trace_add("write", refresh_ui)

# Элементы для применения темы
labels_for_theme = [
    child for child in controls_frame.winfo_children() if isinstance(child, tk.Label)
] + [
    child for child in filters_frame.winfo_children() if isinstance(child, tk.Label)
] + [
    stats_label
]

entries_for_theme = [entry, deadline_entry, search_entry]
buttons_for_theme = [
    child for child in actions_frame.winfo_children() if isinstance(child, tk.Button)
]

# Загрузка задач
load_tasks()
apply_theme()

root.mainloop()
