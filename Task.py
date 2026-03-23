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

COLORS = {
    "bg": "#0f172a",
    "card": "#1e293b",
    "input": "#0b1220",
    "accent": "#6366f1",
    "hover": "#4f46e5",
    "text": "#e2e8f0",
    "muted": "#94a3b8",
    "danger": "#ef4444",
}

tasks = []

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

# ===== UI =====
def clear_tasks():
    for w in task_container.winfo_children():
        w.destroy()

def create_card(i, task):
    frame = tk.Frame(task_container, bg="#273449", padx=14, pady=12)
    frame.pack(fill="x", pady=6)

    def on_enter(e):
        frame.configure(bg=COLORS["hover"])

    def on_leave(e):
        frame.configure(bg="#273449")

    frame.bind("<Enter>", on_enter)
    frame.bind("<Leave>", on_leave)

    color = COLORS["danger"] if is_overdue(task) else COLORS["text"]

    tk.Label(
        frame,
        text=task["text"],
        bg=frame["bg"],
        fg=color,
        font=("Segoe UI", 13, "bold"),
        anchor="w"
    ).pack(fill="x")

    tk.Label(
        frame,
        text=f"{task['category']} | {task['deadline']} | {task['priority']}",
        bg=frame["bg"],
        fg=COLORS["muted"]
    ).pack(fill="x", pady=(2, 6))

    btns = tk.Frame(frame, bg=frame["bg"])
    btns.pack(anchor="e")

    tk.Button(btns, text="✔", bg=COLORS["accent"], fg="white",
              bd=0, command=lambda: toggle_task(i)).pack(side="right", padx=4)

    tk.Button(btns, text="✖", bg=COLORS["accent"], fg="white",
              bd=0, command=lambda: delete_task(i)).pack(side="right", padx=4)

def refresh_ui():
    clear_tasks()

    for i, t in enumerate(tasks):
        create_card(i, t)

    total = len(tasks)
    done = sum(t["done"] for t in tasks)
    percent = int(done / total * 100) if total else 0

    stats_var.set(f"Всего: {total} | Выполнено: {done} | {percent}%")

# ===== ОКНО =====
root = tk.Tk()
root.title("Task Manager")
root.geometry("1100x800")
root.configure(bg=COLORS["bg"])

# ===== ЦЕНТРАЛЬНАЯ КАРТОЧКА =====
container = tk.Frame(
    root,
    bg=COLORS["card"],
    padx=25,
    pady=25,
    highlightthickness=1,
    highlightbackground="#334155"
)

container.place(relx=0.5, rely=0.5, anchor="center", width=800, height=700)

# ===== TITLE =====
tk.Label(
    container,
    text="Task Manager",
    bg=COLORS["card"],
    fg=COLORS["text"],
    font=("Segoe UI", 20, "bold")
).pack(pady=(0, 15))

# ===== INPUTS =====
entry = tk.Entry(container, bg=COLORS["input"], fg=COLORS["text"],
                 insertbackground="white", bd=0, font=("Segoe UI", 12))
entry.pack(fill="x", pady=5)

deadline_entry = tk.Entry(container, bg=COLORS["input"], fg=COLORS["text"],
                          bd=0, font=("Segoe UI", 12))
deadline_entry.pack(fill="x", pady=5)
deadline_entry.insert(0, "дд-мм-гггг")

category_var = tk.StringVar(value="Личное")
priority_var = tk.StringVar(value="Средний")

row = tk.Frame(container, bg=COLORS["card"])
row.pack(fill="x", pady=5)

tk.OptionMenu(row, category_var, *CATEGORIES).pack(side="left", padx=5)
tk.OptionMenu(row, priority_var, *PRIORITIES).pack(side="left", padx=5)

tk.Button(
    container,
    text="Добавить",
    bg=COLORS["accent"],
    fg="white",
    bd=0,
    font=("Segoe UI", 12),
    command=add_task
).pack(fill="x", pady=10)

# ===== TASKS =====
task_container = tk.Frame(container, bg=COLORS["card"])
task_container.pack(fill="both", expand=True, pady=10)

# ===== STATS =====
stats_var = tk.StringVar()
tk.Label(
    container,
    textvariable=stats_var,
    bg=COLORS["card"],
    fg=COLORS["muted"],
    font=("Segoe UI", 11)
).pack(pady=5)

# ===== СТАРТ =====
load_tasks()
root.mainloop()