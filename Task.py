import json
import os
import sys
import tkinter as tk
from datetime import datetime
from tkinter import filedialog, messagebox, ttk

# ===== Фикс пути для .exe =====
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(__file__)

FILE_NAME = os.path.join(BASE_DIR, "tasks.json")

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
    return {
        "text": str(raw_task.get("text", "")).strip(),
        "done": bool(raw_task.get("done", False)),
        "deadline": str(raw_task.get("deadline", "без срока")).strip() or "без срока",
        "category": raw_task.get("category", CATEGORIES[1]) if raw_task.get("category") in CATEGORIES else CATEGORIES[1],
        "priority": raw_task.get("priority", "Средний") if raw_task.get("priority") in PRIORITIES else "Средний",
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
    return date_value and (not task["done"]) and date_value < datetime.now().date()


# ===== ФАЙЛ =====
def load_tasks():
    global tasks
    if os.path.exists(FILE_NAME):
        try:
            with open(FILE_NAME, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, list):
                data = []
            tasks = [normalize_task(t) for t in data if isinstance(t, dict)]
        except:
            tasks = []
    else:
        tasks = []

    refresh_ui()
    show_startup_notifications()


def save_tasks():
    try:
        with open(FILE_NAME, "w", encoding="utf-8") as f:
            json.dump(tasks, f, ensure_ascii=False, indent=4)
    except Exception as e:
        messagebox.showerror("Ошибка", str(e))


# ===== ЛОГИКА =====
def get_filtered_sorted_items():
    query = search_var.get().lower()
    status = status_filter_var.get()
    category = category_filter_var.get()
    sort = sort_var.get()

    items = []
    for i, task in enumerate(tasks):
        if query and query not in task["text"].lower():
            continue
        if status == "Выполненные" and not task["done"]:
            continue
        if status == "Невыполненные" and task["done"]:
            continue
        if category != "Все категории" and task["category"] != category:
            continue
        items.append((i, task))

    if sort == "По дедлайну":
        items.sort(key=lambda x: parse_deadline(x[1]["deadline"]) or datetime.max.date())
    elif sort == "По статусу":
        items.sort(key=lambda x: x[1]["done"])

    return items


def update_listbox():
    global displayed_indices
    listbox.delete(0, tk.END)

    filtered = get_filtered_sorted_items()
    displayed_indices = [i for i, _ in filtered]

    for _, task in filtered:
        text = f"{'✅' if task['done'] else '❌'} [{task['category']}] {task['text']} (до: {task['deadline']}, {task['priority']})"
        listbox.insert(tk.END, text)

    for i, (_, task) in enumerate(filtered):
        color = "#ff4d4d" if is_overdue(task) else (
            "#e53935" if task["priority"] == "Высокий" else
            "#fbc02d" if task["priority"] == "Средний" else "#43a047"
        )
        listbox.itemconfig(i, foreground=color)


def update_stats():
    total = len(tasks)
    done = sum(t["done"] for t in tasks)
    overdue = sum(is_overdue(t) for t in tasks)
    percent = int(done / total * 100) if total else 0
    stats_var.set(f"Всего: {total} | Выполнено: {done} | {percent}% | Просрочено: {overdue}")


def refresh_ui(*args):
    update_listbox()
    update_stats()


def show_startup_notifications():
    overdue = sum(is_overdue(t) for t in tasks)
    if overdue:
        messagebox.showwarning("Просрочено", f"{overdue} задач просрочено")


def get_selected():
    sel = listbox.curselection()
    if not sel:
        return None
    return displayed_indices[sel[0]]


def add_task():
    text = entry.get().strip()
    deadline = deadline_entry.get().strip()

    if not text:
        return

    if not deadline:
        deadline = "без срока"
    elif deadline != "без срока" and not parse_deadline(deadline):
        messagebox.showerror("Ошибка", "Дата дд-мм-гггг")
        return

    tasks.append({
        "text": text,
        "done": False,
        "deadline": deadline,
        "category": category_var.get(),
        "priority": priority_var.get()
    })

    save_tasks()
    refresh_ui()


def delete_task():
    i = get_selected()
    if i is None:
        return
    tasks.pop(i)
    save_tasks()
    refresh_ui()


def toggle_done():
    i = get_selected()
    if i is None:
        return
    tasks[i]["done"] = not tasks[i]["done"]
    save_tasks()
    refresh_ui()


# ===== UI =====
root = tk.Tk()
root.title("Task Manager")
root.geometry("750x650")

entry = tk.Entry(root, width=40)
entry.pack()

deadline_entry = tk.Entry(root)
deadline_entry.pack()
deadline_entry.insert(0, "дд-мм-гггг")

category_var = tk.StringVar(value=CATEGORIES[1])
ttk.Combobox(root, textvariable=category_var, values=CATEGORIES).pack()

priority_var = tk.StringVar(value="Средний")
ttk.Combobox(root, textvariable=priority_var, values=PRIORITIES).pack()

search_var = tk.StringVar()
tk.Entry(root, textvariable=search_var).pack()

status_filter_var = tk.StringVar(value="Все")
ttk.Combobox(root, textvariable=status_filter_var, values=["Все", "Выполненные", "Невыполненные"]).pack()

category_filter_var = tk.StringVar(value="Все категории")
ttk.Combobox(root, textvariable=category_filter_var, values=["Все категории", *CATEGORIES]).pack()

sort_var = tk.StringVar(value="Без сортировки")
ttk.Combobox(root, textvariable=sort_var, values=["Без сортировки", "По дедлайну", "По статусу"]).pack()

tk.Button(root, text="Добавить", command=add_task).pack()
tk.Button(root, text="Удалить", command=delete_task).pack()
tk.Button(root, text="Готово", command=toggle_done).pack()

listbox = tk.Listbox(root, width=90, height=20)
listbox.pack()

stats_var = tk.StringVar()
tk.Label(root, textvariable=stats_var).pack()

search_var.trace_add("write", refresh_ui)
status_filter_var.trace_add("write", refresh_ui)
category_filter_var.trace_add("write", refresh_ui)
sort_var.trace_add("write", refresh_ui)

load_tasks()

root.mainloop()