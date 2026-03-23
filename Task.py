import json
import os
import tkinter as tk
from datetime import datetime
from tkinter import messagebox
from tkcalendar import DateEntry

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
def load_tasks():
    global tasks
    if os.path.exists(FILE_NAME):
        try:
            with open(FILE_NAME, "r", encoding="utf-8") as f:
                tasks = json.load(f)
        except:
            tasks = []
    refresh_ui()

def save_tasks():
    with open(FILE_NAME, "w", encoding="utf-8") as f:
        json.dump(tasks, f, ensure_ascii=False, indent=4)

def is_overdue(task):
    try:
        d = datetime.strptime(task["deadline"], DATE_FORMAT).date()
        return not task["done"] and d < datetime.now().date()
    except:
        return False

# ===== LOGIC =====
def add_task():
    text = entry.get().strip()
    if not text:
        messagebox.showwarning("Ошибка", "Введите задачу")
        return

    task = {
        "text": text,
        "done": False,
        "deadline": date_entry.get(),
        "category": category_var.get(),
        "priority": priority_var.get()
    }

    tasks.append(task)
    save_tasks()

    entry.delete(0, tk.END)
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
    for w in inner_frame.winfo_children():
        w.destroy()

def create_card(i, task):
    frame = tk.Frame(inner_frame, bg="#273449", padx=14, pady=12)
    frame.pack(fill="x", pady=6, padx=10)

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

# ===== WINDOW =====
root = tk.Tk()
root.title("Task Manager")
root.geometry("1100x800")
root.configure(bg=COLORS["bg"])

# ===== CENTER CONTAINER =====
container = tk.Frame(root, bg=COLORS["card"], padx=25, pady=25)
container.place(relx=0.5, rely=0.5, anchor="center", width=850, height=720)

# TITLE
tk.Label(container, text="Task Manager",
         bg=COLORS["card"], fg=COLORS["text"],
         font=("Segoe UI", 20, "bold")).pack(pady=10)

# INPUT
entry = tk.Entry(container, bg=COLORS["input"], fg=COLORS["text"],
                 insertbackground="white", bd=0, font=("Segoe UI", 12))
entry.pack(fill="x", pady=5)

# DATE PICKER
date_entry = DateEntry(container, date_pattern="dd-mm-yyyy")
date_entry.pack(fill="x", pady=5)

# SELECTORS
category_var = tk.StringVar(value="Личное")
priority_var = tk.StringVar(value="Средний")

row = tk.Frame(container, bg=COLORS["card"])
row.pack(pady=5)

tk.OptionMenu(row, category_var, *CATEGORIES).pack(side="left", padx=5)
tk.OptionMenu(row, priority_var, *PRIORITIES).pack(side="left", padx=5)

# BUTTON
tk.Button(container, text="Добавить",
          bg=COLORS["accent"], fg="white",
          bd=0, font=("Segoe UI", 12),
          command=add_task).pack(fill="x", pady=10)

# ===== SCROLLABLE TASKS =====
canvas = tk.Canvas(container, bg=COLORS["card"], highlightthickness=0)
scrollbar = tk.Scrollbar(container, orient="vertical", command=canvas.yview)

inner_frame = tk.Frame(canvas, bg=COLORS["card"])

inner_frame.bind(
    "<Configure>",
    lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
)

canvas.create_window((0, 0), window=inner_frame, anchor="nw")
canvas.configure(yscrollcommand=scrollbar.set)

canvas.pack(side="left", fill="both", expand=True)
scrollbar.pack(side="right", fill="y")

# STATS
stats_var = tk.StringVar()
tk.Label(container, textvariable=stats_var,
         bg=COLORS["card"], fg=COLORS["muted"]).pack(pady=5)

# START
load_tasks()
root.mainloop()