import json
import os
import tkinter as tk
from datetime import datetime
from tkinter import messagebox

# ===== НАСТРОЙКИ =====
FILE_NAME = "tasks.json"
DATE_FORMAT = "%d-%m-%Y"

CATEGORIES = ["Работа", "Личное", "Учёба"]
PRIORITIES = ["Высокий", "Средний", "Низкий"]

# ===== КОРИЧНЕВАЯ ТЕМА =====
COLORS = {
    "bg": "#2b1e17",
    "sidebar": "#3a2a21",
    "card": "#4b362b",
    "hover": "#5a4033",
    "accent": "#a9745b",
    "text": "#f5e6d3",
    "muted": "#c2a78f",
    "danger": "#ff6b6b",
}

tasks = []
current_filter = "all"

# ===== DATA =====
def normalize_task(raw):
    return {
        "text": raw.get("text", ""),
        "done": raw.get("done", False),
        "deadline": raw.get("deadline", "без срока"),
        "category": raw.get("category", "Личное"),
        "priority": raw.get("priority", "Средний"),
    }

def parse_deadline(text):
    try:
        return datetime.strptime(text, DATE_FORMAT).date()
    except:
        return None

def is_overdue(task):
    d = parse_deadline(task["deadline"])
    return d and not task["done"] and d < datetime.now().date()

def load_tasks():
    global tasks
    if os.path.exists(FILE_NAME):
        try:
            with open(FILE_NAME, "r", encoding="utf-8") as f:
                tasks = [normalize_task(t) for t in json.load(f)]
        except:
            tasks = []
    refresh_ui()

def save_tasks():
    with open(FILE_NAME, "w", encoding="utf-8") as f:
        json.dump(tasks, f, ensure_ascii=False, indent=4)

# ===== ЛОГИКА =====
def get_visible():
    result = []
    for i, t in enumerate(tasks):
        if current_filter == "done" and not t["done"]:
            continue
        if current_filter == "todo" and t["done"]:
            continue
        result.append((i, t))
    return result

def add_task():
    text = entry.get().strip()
    deadline = deadline_entry.get().strip() or "без срока"

    if not text:
        messagebox.showwarning("Ошибка", "Введите задачу")
        return

    tasks.append({
        "text": text,
        "done": False,
        "deadline": deadline,
        "category": category_var.get(),
        "priority": priority_var.get()
    })

    entry.delete(0, tk.END)
    deadline_entry.delete(0, tk.END)

    save_tasks()
    refresh_ui()

def toggle_task(i):
    tasks[i]["done"] = not tasks[i]["done"]
    save_tasks()
    refresh_ui()

def delete_task(i):
    tasks.pop(i)
    save_tasks()
    refresh_ui()

def set_filter(mode):
    global current_filter
    current_filter = mode
    refresh_ui()

# ===== UI =====
def clear_tasks():
    for w in task_container.winfo_children():
        w.destroy()

def create_card(i, task):
    frame = tk.Frame(task_container, bg=COLORS["card"], padx=10, pady=10)
    frame.pack(fill="x", pady=5)

    # hover эффект
    def on_enter(e):
        frame.configure(bg=COLORS["hover"])
    def on_leave(e):
        frame.configure(bg=COLORS["card"])

    frame.bind("<Enter>", on_enter)
    frame.bind("<Leave>", on_leave)

    color = COLORS["danger"] if is_overdue(task) else COLORS["text"]

    tk.Label(
        frame,
        text=task["text"],
        bg=COLORS["card"],
        fg=color,
        font=("Segoe UI", 12, "bold"),
        anchor="w"
    ).pack(fill="x")

    tk.Label(
        frame,
        text=f"{task['category']} | {task['deadline']} | {task['priority']}",
        bg=COLORS["card"],
        fg=COLORS["muted"]
    ).pack(fill="x")

    btns = tk.Frame(frame, bg=COLORS["card"])
    btns.pack(anchor="e")

    tk.Button(
        btns, text="✔",
        bg=COLORS["accent"],
        command=lambda: toggle_task(i)
    ).pack(side="right", padx=3)

    tk.Button(
        btns, text="✖",
        bg=COLORS["accent"],
        command=lambda: delete_task(i)
    ).pack(side="right", padx=3)

def refresh_ui():
    clear_tasks()

    for i, t in get_visible():
        create_card(i, t)

    total = len(tasks)
    done = sum(t["done"] for t in tasks)
    percent = int(done / total * 100) if total else 0

    stats_var.set(f"Всего: {total} | Выполнено: {done} | {percent}%")

# ===== ОКНО =====
root = tk.Tk()
root.title("Task Manager")
root.geometry("900x600")
root.configure(bg=COLORS["bg"])

root.grid_columnconfigure(1, weight=1)
root.grid_rowconfigure(0, weight=1)

# ===== SIDEBAR =====
sidebar = tk.Frame(root, bg=COLORS["sidebar"], width=200)
sidebar.grid(row=0, column=0, sticky="ns")

tk.Label(
    sidebar,
    text="Task Manager",
    bg=COLORS["sidebar"],
    fg=COLORS["text"],
    font=("Segoe UI", 16, "bold")
).pack(pady=20)

tk.Button(sidebar, text="Все", bg=COLORS["accent"],
          command=lambda: set_filter("all")).pack(fill="x", padx=10, pady=5)

tk.Button(sidebar, text="Выполненные", bg=COLORS["accent"],
          command=lambda: set_filter("done")).pack(fill="x", padx=10, pady=5)

tk.Button(sidebar, text="Невыполненные", bg=COLORS["accent"],
          command=lambda: set_filter("todo")).pack(fill="x", padx=10, pady=5)

# ===== MAIN =====
main = tk.Frame(root, bg=COLORS["bg"])
main.grid(row=0, column=1, sticky="nsew")

# TOP
top = tk.Frame(main, bg=COLORS["bg"])
top.pack(fill="x", pady=10)

entry = tk.Entry(top)
entry.pack(side="left", fill="x", expand=True, padx=5)

deadline_entry = tk.Entry(top, width=15)
deadline_entry.pack(side="left", padx=5)
deadline_entry.insert(0, "дд-мм-гггг")

category_var = tk.StringVar(value="Личное")
priority_var = tk.StringVar(value="Средний")

tk.OptionMenu(top, category_var, *CATEGORIES).pack(side="left", padx=5)
tk.OptionMenu(top, priority_var, *PRIORITIES).pack(side="left", padx=5)

tk.Button(
    top,
    text="Добавить",
    bg=COLORS["accent"],
    command=add_task
).pack(side="left", padx=5)

# TASKS
task_container = tk.Frame(main, bg=COLORS["bg"])
task_container.pack(fill="both", expand=True, padx=10)

# STATS
stats_var = tk.StringVar()
tk.Label(
    main,
    textvariable=stats_var,
    bg=COLORS["bg"],
    fg=COLORS["text"]
).pack(pady=10)

# ===== СТАРТ =====
load_tasks()
root.mainloop()