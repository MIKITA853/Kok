import tkinter as tk
from tkinter import messagebox
import json
import os
from datetime import datetime

# ---------- CONFIG ----------
FILE_NAME = "tasks.json"
DATE_FORMAT = "%d-%m-%Y"

BG = "#0f172a"
CARD = "#1e293b"
TASK_CARD = "#273449"
INPUT = "#0b1220"
ACCENT = "#6366f1"
HOVER = "#4f46e5"
TEXT = "#e2e8f0"
MUTED = "#94a3b8"
DANGER = "#ef4444"

CATEGORIES = ["Работа", "Личное", "Учёба"]
PRIORITIES = ["Высокий", "Средний", "Низкий"]

tasks = []
selected_task_id = None

# ---------- DATA ----------
def load_tasks():
    global tasks
    if os.path.exists(FILE_NAME):
        try:
            with open(FILE_NAME, "r", encoding="utf-8") as f:
                data = json.load(f)
            tasks = data if isinstance(data, list) else []
        except:
            tasks = []

def save_tasks():
    with open(FILE_NAME, "w", encoding="utf-8") as f:
        json.dump(tasks, f, ensure_ascii=False, indent=2)

def next_id():
    return str(int(datetime.now().timestamp() * 1000000))

def parse_deadline(value):
    try:
        return datetime.strptime(value, DATE_FORMAT).date()
    except:
        return None

def is_overdue(task):
    if task["done"]:
        return False
    d = parse_deadline(task["deadline"])
    return d and d < datetime.now().date()

# ---------- LOGIC ----------
def add_or_update():
    global selected_task_id

    text = task_var.get().strip()
    deadline = deadline_var.get().strip()

    if not text:
        messagebox.showwarning("Ошибка", "Введите задачу")
        return

    if not parse_deadline(deadline):
        messagebox.showwarning("Ошибка", "Дата: дд-мм-гггг")
        return

    task = {
        "id": selected_task_id or next_id(),
        "text": text,
        "deadline": deadline,
        "done": False,
        "category": category_var.get(),
        "priority": priority_var.get(),
    }

    if selected_task_id:
        for i, t in enumerate(tasks):
            if t["id"] == selected_task_id:
                task["done"] = t["done"]
                tasks[i] = task
    else:
        tasks.append(task)

    save_tasks()
    clear_inputs()
    refresh()

def toggle_done(task_id):
    for t in tasks:
        if t["id"] == task_id:
            t["done"] = not t["done"]
    save_tasks()
    refresh()

def delete_task(task_id):
    global tasks
    tasks = [t for t in tasks if t["id"] != task_id]
    save_tasks()
    refresh()

def clear_inputs():
    global selected_task_id
    selected_task_id = None
    task_var.set("")
    deadline_var.set("")
    category_var.set("Личное")
    priority_var.set("Средний")
    add_btn.config(text="Добавить")

def select_task(task):
    global selected_task_id
    selected_task_id = task["id"]

    task_var.set(task["text"])
    deadline_var.set(task["deadline"])
    category_var.set(task["category"])
    priority_var.set(task["priority"])

    add_btn.config(text="Сохранить")

# ---------- UI ----------
def refresh():
    for w in list_frame.winfo_children():
        w.destroy()

    for task in tasks:
        create_card(task)

def create_card(task):
    color = HOVER if task["id"] == selected_task_id else TASK_CARD
    title_color = DANGER if is_overdue(task) else TEXT

    frame = tk.Frame(list_frame, bg=color, padx=10, pady=10)
    frame.pack(fill="x", pady=4)

    title = tk.Label(frame, text=task["text"], bg=color, fg=title_color, font=("Segoe UI", 12, "bold"))
    title.pack(anchor="w")

    meta = tk.Label(
        frame,
        text=f'{task["category"]} | {task["deadline"]} | {task["priority"]}',
        bg=color,
        fg=MUTED
    )
    meta.pack(anchor="w")

    btns = tk.Frame(frame, bg=color)
    btns.pack(anchor="e")

    tk.Button(btns, text="✔", command=lambda: toggle_done(task["id"]), bg=ACCENT, fg="white").pack(side="left")
    tk.Button(btns, text="✖", command=lambda: delete_task(task["id"]), bg=DANGER, fg="white").pack(side="left")

    frame.bind("<Button-1>", lambda e: select_task(task))
    title.bind("<Button-1>", lambda e: select_task(task))
    meta.bind("<Button-1>", lambda e: select_task(task))

# ---------- APP ----------
root = tk.Tk()
root.title("Task Manager")
root.geometry("700x700")
root.configure(bg=BG)

task_var = tk.StringVar()
deadline_var = tk.StringVar()
category_var = tk.StringVar(value="Личное")
priority_var = tk.StringVar(value="Средний")

container = tk.Frame(root, bg=CARD, padx=15, pady=15)
container.pack(fill="both", expand=True, padx=20, pady=20)

tk.Entry(container, textvariable=task_var, bg=INPUT, fg=TEXT).pack(fill="x", pady=5)
tk.Entry(container, textvariable=deadline_var, bg=INPUT, fg=TEXT).pack(fill="x", pady=5)

tk.OptionMenu(container, category_var, *CATEGORIES).pack(fill="x", pady=5)
tk.OptionMenu(container, priority_var, *PRIORITIES).pack(fill="x", pady=5)

add_btn = tk.Button(container, text="Добавить", command=add_or_update, bg=ACCENT, fg="white")
add_btn.pack(fill="x", pady=10)

list_frame = tk.Frame(container, bg=CARD)
list_frame.pack(fill="both", expand=True)

load_tasks()
refresh()

root.mainloop()